use std::{collections::BTreeMap, fs, path::PathBuf};

use romm_download_core::{
    ConfiguredOrigin, DestinationRootRegistry, DownloadEngine, DownloadError, HttpRequest,
    HttpResponse, HttpTransport, TransferOutcome, VecSink,
};

const MANIFEST_ID: &str = "11111111-1111-4111-8111-111111111111";
const MEMBER_ID: &str = "22222222-2222-4222-8222-222222222222";
const SHA256: &str = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

#[derive(Default)]
struct MockTransport {
    responses: Vec<Result<HttpResponse, ()>>,
    requests: Vec<HttpRequest>,
}

impl MockTransport {
    fn with(response: HttpResponse) -> Self {
        Self { responses: vec![Ok(response)], requests: Vec::new() }
    }
}

impl HttpTransport for MockTransport {
    fn execute(&mut self, request: HttpRequest) -> Result<HttpResponse, ()> {
        self.requests.push(request);
        self.responses.remove(0)
    }
}

fn response(status: u16, body: &[u8]) -> HttpResponse {
    HttpResponse { status, headers: BTreeMap::new(), body: body.to_vec(), final_url: None }
}

fn manifest(size: u64) -> String {
    format!(
        r#"{{"schema_version":1,"id":"{MANIFEST_ID}","created_at":"2026-09-17T00:00:00Z","expires_at":"2026-09-18T00:00:00Z","components":[],"members":[{{"file_id":"{MEMBER_ID}","destination":"Game/file.bin","size":{size},"sha256":"{SHA256}","snapshot":"\"snapshot\"","download":"/api/download-manifests/{MANIFEST_ID}/files/{MEMBER_ID}"}}]}}"#
    )
}

fn root() -> PathBuf {
    let root = std::env::temp_dir().join(format!("romm-transfer-{}", std::process::id()));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(&root).unwrap();
    root
}

#[test]
fn fetches_only_an_origin_bound_manifest_before_accepting_a_root_handle() {
    let origin = ConfiguredOrigin::parse("https://romm.example:8443").unwrap();
    let mut transport = MockTransport::with(response(200, manifest(3).as_bytes()));
    let mut roots = DestinationRootRegistry::new();
    let handle = roots.register_native_selection(root()).unwrap();
    let mut engine = DownloadEngine::new(&mut transport, &roots, "device-token");

    let queued = engine.queue_manifest(origin, MANIFEST_ID.parse().unwrap(), handle).unwrap();

    assert_eq!(queued.manifest.members[0].size, 3);
    assert_eq!(transport.requests[0].url, format!("https://romm.example:8443/api/download-manifests/{MANIFEST_ID}"));
    assert_eq!(transport.requests[0].headers.get("Authorization"), Some(&"Bearer device-token".to_owned()));
    assert!(!transport.requests[0].headers.contains_key("Cookie"));
}

#[test]
fn invalid_remote_states_do_not_create_a_job_or_accept_cross_origin_data() {
    let origin = ConfiguredOrigin::parse("https://romm.example").unwrap();
    let mut roots = DestinationRootRegistry::new();
    let handle = roots.register_native_selection(root()).unwrap();
    for (status, expected) in [(401, DownloadError::AuthRequired), (403, DownloadError::AuthRequired), (410, DownloadError::ManifestStale), (409, DownloadError::SourceChanged)] {
        let mut transport = MockTransport::with(response(status, b"{}"));
        let mut engine = DownloadEngine::new(&mut transport, &roots, "secret");
        assert_eq!(engine.queue_manifest(origin.clone(), MANIFEST_ID.parse().unwrap(), handle).unwrap_err(), expected);
    }
    let mut redirect = response(200, manifest(3).as_bytes());
    redirect.final_url = Some("https://evil.example/api/download-manifests/x".to_owned());
    let mut transport = MockTransport::with(redirect);
    let mut engine = DownloadEngine::new(&mut transport, &roots, "secret");
    assert_eq!(engine.queue_manifest(origin, MANIFEST_ID.parse().unwrap(), handle).unwrap_err(), DownloadError::InvalidResponse);
}

#[test]
fn malformed_manifests_and_expired_handles_create_no_local_state() {
    let origin = ConfiguredOrigin::parse("https://romm.example").unwrap();
    let local_root = root();
    let mut roots = DestinationRootRegistry::new();
    let handle = roots.register_native_selection(&local_root).unwrap();
    let mut transport = MockTransport::with(response(200, b"not json"));
    let mut engine = DownloadEngine::new(&mut transport, &roots, "secret");
    assert_eq!(engine.queue_manifest(origin.clone(), MANIFEST_ID.parse().unwrap(), handle).unwrap_err(), DownloadError::InvalidResponse);
    assert!(fs::read_dir(&local_root).unwrap().next().is_none());

    roots.expire(handle);
    let mut transport = MockTransport::with(response(200, manifest(3).as_bytes()));
    let mut engine = DownloadEngine::new(&mut transport, &roots, "secret");
    assert_eq!(engine.queue_manifest(origin, MANIFEST_ID.parse().unwrap(), handle).unwrap_err(), DownloadError::InvalidDestinationRoot);
    assert!(fs::read_dir(&local_root).unwrap().next().is_none());
}

#[test]
fn fresh_and_resume_protocols_require_exact_status_range_snapshot_and_lengths() {
    let origin = ConfiguredOrigin::parse("https://romm.example").unwrap();
    let mut roots = DestinationRootRegistry::new();
    let handle = roots.register_native_selection(root()).unwrap();
    let mut transport = MockTransport::with(response(200, manifest(3).as_bytes()));
    let mut engine = DownloadEngine::new(&mut transport, &roots, "token");
    let queued = engine.queue_manifest(origin, MANIFEST_ID.parse().unwrap(), handle).unwrap();
    let member = queued.manifest.members[0].clone();

    let mut fresh = response(200, b"abc");
    fresh.headers.insert("Content-Length".to_owned(), "3".to_owned());
    engine.replace_transport(MockTransport::with(fresh));
    let mut sink = VecSink::default();
    assert_eq!(engine.transfer_member(&member, 0, &mut sink).unwrap(), TransferOutcome::Downloaded { bytes: 3 });
    assert_eq!(sink.bytes(), b"abc");

    let mut resumed = response(206, b"c");
    resumed.headers.insert("Content-Length".to_owned(), "1".to_owned());
    resumed.headers.insert("Content-Range".to_owned(), "bytes 2-2/3".to_owned());
    engine.replace_transport(MockTransport::with(resumed));
    let mut sink = VecSink::default();
    assert_eq!(engine.transfer_member(&member, 2, &mut sink).unwrap(), TransferOutcome::Downloaded { bytes: 3 });
    assert_eq!(engine.last_request().unwrap().headers.get("Range"), Some(&"bytes=2-".to_owned()));
    assert_eq!(engine.last_request().unwrap().headers.get("If-Match"), Some(&"\"snapshot\"".to_owned()));

    engine.replace_transport(MockTransport::with(response(200, b"c")));
    assert_eq!(engine.transfer_member(&member, 2, &mut VecSink::default()).unwrap_err(), DownloadError::InvalidResponse);
}

#[test]
fn classifies_416_and_large_u64_metadata_without_allocating_parts() {
    let origin = ConfiguredOrigin::parse("https://romm.example").unwrap();
    for size in [5_u64 * 1024 * 1024 * 1024, 80 * 1024 * 1024 * 1024, 120 * 1024 * 1024 * 1024] {
        let mut roots = DestinationRootRegistry::new();
        let handle = roots.register_native_selection(root()).unwrap();
        let mut transport = MockTransport::with(response(200, manifest(size).as_bytes()));
        let mut engine = DownloadEngine::new(&mut transport, &roots, "token");
        let queued = engine.queue_manifest(origin.clone(), MANIFEST_ID.parse().unwrap(), handle).unwrap();
        engine.replace_transport(MockTransport::with(response(416, b"")));
        assert_eq!(engine.transfer_member(&queued.manifest.members[0], size, &mut VecSink::default()).unwrap(), TransferOutcome::VerificationCandidate);
        assert_eq!(engine.transfer_member(&queued.manifest.members[0], size + 1, &mut VecSink::default()).unwrap_err(), DownloadError::CorruptLocalState);
    }
}
