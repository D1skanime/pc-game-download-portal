//! Real local-loopback UAT. It is ignored because it requires a writable volume with 30 GiB free.
use std::{collections::BTreeMap, fs::{self, File, OpenOptions}, io::{Read, Seek, SeekFrom, Write}, net::{TcpListener, TcpStream}, path::PathBuf, thread};
use romm_download_core::{ConfiguredOrigin, DestinationRootRegistry, DownloadEngine, FileSink, FileSinkError, HttpRequest, HttpResponse, HttpStreamResponse, HttpTransport, HttpTransportError, JobStore, ManifestValidator, PersistedJob, TransferOutcome, ValidatedMember, IntegrityDownloadEngine, NativePlatformOperations, PlatformFamily, FinalizationMode};
use sha2::{Digest, Sha256};

const TOTAL: u64 = 30 * 1024 * 1024 * 1024;
const INTERRUPT_AFTER: u64 = 8 * 1024 * 1024;
const MANIFEST_ID: &str = "11111111-1111-4111-8111-111111111111";
const MEMBER_ID: &str = "22222222-2222-4222-8222-222222222222";

struct FileSinkState { file: File, bytes: u64, stop_after: Option<u64> }
impl FileSink for FileSinkState {
    fn append(&mut self, data: &[u8]) -> Result<(), FileSinkError> {
        if self.stop_after.is_some_and(|limit| self.bytes + data.len() as u64 > limit) { return Err(FileSinkError); }
        self.file.write_all(data).map_err(|_| FileSinkError)?;
        self.bytes += data.len() as u64;
        Ok(())
    }
}

struct LoopbackTransport { address: std::net::SocketAddr }
impl LoopbackTransport {
    fn request(&self, request: HttpRequest, mut on_chunk: Option<&mut dyn FnMut(&[u8]) -> Result<(), HttpTransportError>>) -> Result<(HttpStreamResponse, Vec<u8>), HttpTransportError> {
        let mut stream = TcpStream::connect(self.address).map_err(|_| HttpTransportError)?;
        let path = request.url.split_once("/").map(|(_, value)| format!("/{value}")).unwrap_or_else(|| "/".to_owned());
        write!(stream, "GET {path} HTTP/1.1\r\nHost: localhost\r\n").map_err(|_| HttpTransportError)?;
        for (key, value) in request.headers { write!(stream, "{key}: {value}\r\n").map_err(|_| HttpTransportError)?; }
        write!(stream, "\r\n").map_err(|_| HttpTransportError)?;
        let mut headers = Vec::new();
        let mut byte = [0_u8; 1];
        while !headers.ends_with(b"\r\n\r\n") { stream.read_exact(&mut byte).map_err(|_| HttpTransportError)?; headers.push(byte[0]); }
        let text = String::from_utf8_lossy(&headers);
        let status = text.split_whitespace().nth(1).and_then(|v| v.parse().ok()).ok_or(HttpTransportError)?;
        let mut response_headers = BTreeMap::new();
        for line in text.lines().skip(1) { if let Some((k, v)) = line.split_once(": ") { response_headers.insert(k.to_owned(), v.to_owned()); } }
        let length: u64 = response_headers.get("Content-Length").and_then(|v| v.parse().ok()).ok_or(HttpTransportError)?;
        let response = HttpStreamResponse { status, headers: response_headers, final_url: None };
        let mut body = Vec::new();
        let mut remaining = length;
        let mut chunk = vec![0_u8; 1024 * 1024];
        while remaining > 0 { let count = remaining.min(chunk.len() as u64) as usize; stream.read_exact(&mut chunk[..count]).map_err(|_| HttpTransportError)?; if let Some(handler) = on_chunk.as_mut() { handler(&chunk[..count])?; } else { body.extend_from_slice(&chunk[..count]); } remaining -= count as u64; }
        Ok((response, body))
    }
}
impl HttpTransport for LoopbackTransport {
    fn execute(&mut self, request: HttpRequest) -> Result<HttpResponse, HttpTransportError> { let (response, body) = self.request(request, None)?; Ok(HttpResponse { status: response.status, headers: response.headers, body, final_url: response.final_url }) }
    fn execute_stream(&mut self, request: HttpRequest, on_chunk: &mut dyn FnMut(&[u8]) -> Result<(), HttpTransportError>) -> Result<HttpStreamResponse, HttpTransportError> { self.request(request, Some(on_chunk)).map(|(response, _)| response) }
}

fn serve(listener: TcpListener, source: PathBuf) { for stream in listener.incoming().take(3) { let Ok(mut stream) = stream else { continue }; let mut request = [0_u8; 4096]; let length = stream.read(&mut request).unwrap_or(0); let text = String::from_utf8_lossy(&request[..length]); let offset = text.lines().find_map(|line| line.strip_prefix("Range: bytes=")?.strip_suffix('-')?.parse::<u64>().ok()).unwrap_or(0); let status = if offset > 0 { 206 } else { 200 }; let size = TOTAL - offset; let headers = if offset > 0 { format!("HTTP/1.1 206 Partial Content\r\nContent-Length: {size}\r\nContent-Range: bytes {offset}-{}/{TOTAL}\r\n\r\n", TOTAL - 1) } else { format!("HTTP/1.1 200 OK\r\nContent-Length: {TOTAL}\r\n\r\n") }; stream.write_all(headers.as_bytes()).unwrap(); let mut file = File::open(&source).unwrap(); file.seek(SeekFrom::Start(offset)).unwrap(); let mut chunk = vec![0_u8; 1024 * 1024]; let mut remaining = size; while remaining > 0 { let count = remaining.min(chunk.len() as u64) as usize; file.read_exact(&mut chunk[..count]).unwrap(); stream.write_all(&chunk[..count]).unwrap(); remaining -= count as u64; } if status == 206 { break; } } }

#[test]
#[ignore = "requires an isolated writable volume with at least 30 GiB free"]
fn sparse_30gib_resume_finalize_uat() {
    let root = std::env::temp_dir().join(format!("romm-30gib-{}", std::process::id()));
    fs::create_dir_all(&root).unwrap();
    let source = root.join("sparse-source.bin");
    let destination = root.join("destination"); fs::create_dir_all(&destination).unwrap();
    let source_file = OpenOptions::new().create(true).write(true).open(&source).unwrap(); source_file.set_len(TOTAL).unwrap();
    let mut hash = Sha256::new(); let zeros = vec![0_u8; 1024 * 1024]; for _ in 0..(TOTAL / zeros.len() as u64) { hash.update(&zeros); } let sha = format!("{:x}", hash.finalize());
    let listener = TcpListener::bind("127.0.0.1:0").unwrap(); let address = listener.local_addr().unwrap(); let server = thread::spawn(move || serve(listener, source));
    let origin = ConfiguredOrigin::parse(&format!("http://127.0.0.1:{}", address.port())).unwrap(); let mut roots = DestinationRootRegistry::new(); let handle = roots.register_native_selection(&destination).unwrap();
    let manifest_json = format!(r#"{{"schema_version":1,"id":"{MANIFEST_ID}","created_at":"2026-09-17T00:00:00Z","expires_at":"2026-09-18T00:00:00Z","components":[],"members":[{{"file_id":"{MEMBER_ID}","destination":"Game/original.bin","size":{TOTAL},"sha256":"{sha}","snapshot":"\"uat\"","download":"/api/download-manifests/{MANIFEST_ID}/files/{MEMBER_ID}"}}]}}"#);
    let manifest = ManifestValidator::validate(&manifest_json).unwrap(); let member: ValidatedMember = manifest.members[0].clone(); let mut transport = LoopbackTransport { address }; let mut engine = DownloadEngine::new(&mut transport, &roots, "uat-token"); let queued = engine.queue_manifest(origin, manifest.id, handle).unwrap();
    let part = destination.join("Game/original.bin.romm-part-22222222-2222-4222-8222-222222222222"); fs::create_dir_all(part.parent().unwrap()).unwrap(); let mut sink = FileSinkState { file: File::create(&part).unwrap(), bytes: 0, stop_after: Some(INTERRUPT_AFTER) }; let store = JobStore::open(&roots, handle).unwrap(); let mut progress = |bytes| { store.upsert(&PersistedJob::new(queued.manifest.id, &member, romm_download_core::DownloadState::Downloading, bytes)).unwrap(); }; assert!(engine.transfer_member_stream(&member, 0, &mut sink, &mut progress).is_err()); let interrupted = sink.bytes; assert!(interrupted > 0); drop(sink);
    let mut sink = FileSinkState { file: OpenOptions::new().append(true).open(&part).unwrap(), bytes: interrupted, stop_after: None }; let mut progress = |bytes| { store.upsert(&PersistedJob::new(queued.manifest.id, &member, romm_download_core::DownloadState::Downloading, bytes)).unwrap(); }; assert_eq!(engine.transfer_member_stream(&member, interrupted, &mut sink, &mut progress).unwrap(), TransferOutcome::Downloaded { bytes: TOTAL }); assert_eq!(sink.bytes, TOTAL); drop(sink);
    let mut operations = NativePlatformOperations::new(PlatformFamily::Linux); let mut finalizer = IntegrityDownloadEngine::new(&mut operations); assert_eq!(finalizer.finalize_member(&roots, handle, &queued.manifest, &member, &store, FinalizationMode::NoReplace).unwrap(), romm_download_core::DownloadState::Completed); assert_eq!(fs::metadata(destination.join("Game/original.bin")).unwrap().len(), TOTAL); server.join().unwrap(); drop(roots); fs::remove_dir_all(&root).unwrap(); assert!(!root.exists());
}
