use std::collections::BTreeMap;

use crate::{
    ConfiguredOrigin, DestinationRootHandle, DestinationRootRegistry, HttpRequest, HttpResponse,
    HttpStreamResponse, HttpTransportError,
    HttpTransport, LocalPathError, ManifestId, ManifestValidator, ValidatedManifest,
    ValidatedMember,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DownloadError {
    AuthRequired,
    ManifestStale,
    SourceChanged,
    InvalidResponse,
    InvalidDestinationRoot,
    CorruptLocalState,
    NetworkError,
    IoFailure,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TransferOutcome {
    Downloaded { bytes: u64 },
    VerificationCandidate,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FileSinkError;

/// File append seam used by the protocol layer after the local-path boundary has prepared a part.
pub trait FileSink {
    fn append(&mut self, data: &[u8]) -> Result<(), FileSinkError>;
}

#[derive(Default)]
pub struct VecSink(Vec<u8>);

impl VecSink {
    pub fn bytes(&self) -> &[u8] {
        &self.0
    }
}

impl FileSink for VecSink {
    fn append(&mut self, data: &[u8]) -> Result<(), FileSinkError> {
        self.0.extend_from_slice(data);
        Ok(())
    }
}

/// A queued immutable manifest contains no raw path authority.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct QueuedManifest {
    pub manifest: ValidatedManifest,
    pub destination_root: DestinationRootHandle,
}

/// Origin-bound authenticated direct-transfer protocol engine.
pub struct DownloadEngine<'a, T: HttpTransport> {
    transport: &'a mut T,
    roots: &'a DestinationRootRegistry,
    token: &'a str,
    origin: Option<ConfiguredOrigin>,
    last_request: Option<HttpRequest>,
}

impl<'a, T: HttpTransport> DownloadEngine<'a, T> {
    pub fn new(transport: &'a mut T, roots: &'a DestinationRootRegistry, token: &'a str) -> Self {
        Self {
            transport,
            roots,
            token,
            origin: None,
            last_request: None,
        }
    }

    pub fn replace_transport(&mut self, transport: T) {
        *self.transport = transport;
    }

    pub fn last_request(&self) -> Option<&HttpRequest> {
        self.last_request.as_ref()
    }

    pub fn queue_manifest(
        &mut self,
        origin: ConfiguredOrigin,
        manifest_id: ManifestId,
        destination_root: DestinationRootHandle,
    ) -> Result<QueuedManifest, DownloadError> {
        let route = format!("/api/download-manifests/{manifest_id}");
        let response = self.request(&origin, &route, BTreeMap::new())?;
        let manifest = ManifestValidator::validate(
            std::str::from_utf8(&response.body).map_err(|_| DownloadError::InvalidResponse)?,
        )
        .map_err(|_| DownloadError::InvalidResponse)?;
        if manifest.id != manifest_id {
            return Err(DownloadError::InvalidResponse);
        }
        self.roots.root(destination_root).map_err(map_root_error)?;
        self.origin = Some(origin);
        Ok(QueuedManifest {
            manifest,
            destination_root,
        })
    }

    pub fn transfer_member(
        &mut self,
        member: &ValidatedMember,
        offset: u64,
        sink: &mut impl FileSink,
    ) -> Result<TransferOutcome, DownloadError> {
        if offset > member.size {
            return Err(DownloadError::CorruptLocalState);
        }
        self.transfer_member_stream(member, offset, sink, &mut |_| {})
    }

    /// Streams bounded response chunks into the sink and reports each durable byte count.
    pub fn transfer_member_stream(
        &mut self,
        member: &ValidatedMember,
        offset: u64,
        sink: &mut impl FileSink,
        on_progress: &mut impl FnMut(u64),
    ) -> Result<TransferOutcome, DownloadError> {
        if offset > member.size {
            return Err(DownloadError::CorruptLocalState);
        }
        let origin = self.origin.clone().ok_or(DownloadError::InvalidResponse)?;
        let mut headers = BTreeMap::new();
        if offset != 0 {
            headers.insert("Range".to_owned(), format!("bytes={offset}-"));
            headers.insert("If-Match".to_owned(), member.snapshot.clone());
        }
        let request = self.make_request(&origin, &member.download, headers)?;
        let expected = member.size.checked_sub(offset).ok_or(DownloadError::CorruptLocalState)?;
        let mut written = 0_u64;
        let mut callback = |chunk: &[u8]| {
            let count = u64::try_from(chunk.len()).map_err(|_| HttpTransportError)?;
            written = written.checked_add(count).ok_or(HttpTransportError)?;
            sink.append(chunk).map_err(|_| HttpTransportError)?;
            on_progress(offset + written);
            Ok(())
        };
        let response = self.transport.execute_stream(request, &mut callback).map_err(|_| DownloadError::NetworkError)?;
        if response.final_url.as_deref().is_some_and(|url| !origin.contains_url(url)) { return Err(DownloadError::InvalidResponse); }
        match response.status { 401 | 403 => return Err(DownloadError::AuthRequired), 410 => return Err(DownloadError::ManifestStale), 409 | 412 => return Err(DownloadError::SourceChanged), _ => {} }
        self.validate_response(member, offset, expected, &response, written)
    }

    fn validate_response(
        &self,
        member: &ValidatedMember,
        offset: u64,
        expected: u64,
        response: &HttpStreamResponse,
        written: u64,
    ) -> Result<TransferOutcome, DownloadError> {
        if response.status == 416 {
            return if offset == member.size && written == 0 { Ok(TransferOutcome::VerificationCandidate) } else { Err(DownloadError::InvalidResponse) };
        }
        if offset == 0 {
            if response.status != 200 || content_length(&response.headers) != Some(expected) || written != expected { return Err(DownloadError::InvalidResponse); }
        } else if response.status != 206 || !valid_content_range_headers(&response.headers, offset, member.size) || content_length(&response.headers) != Some(expected) || written != expected {
            return Err(DownloadError::InvalidResponse);
        }
        Ok(TransferOutcome::Downloaded { bytes: member.size })
    }

    fn make_request(
        &mut self,
        origin: &ConfiguredOrigin,
        route: &str,
        mut headers: BTreeMap<String, String>,
    ) -> Result<HttpRequest, DownloadError> {
        let url = origin.join_relative(route).map_err(|_| DownloadError::InvalidResponse)?;
        headers.insert("Authorization".to_owned(), format!("Bearer {}", self.token));
        let request = HttpRequest { url, headers };
        self.last_request = Some(request.clone());
        Ok(request)
    }

    fn request(
        &mut self,
        origin: &ConfiguredOrigin,
        route: &str,
        headers: BTreeMap<String, String>,
    ) -> Result<HttpResponse, DownloadError> {
        let request = self.make_request(origin, route, headers)?;
        let response = self.transport.execute(request).map_err(|_| DownloadError::NetworkError)?;
        if response.final_url.as_deref().is_some_and(|url| !origin.contains_url(url)) { return Err(DownloadError::InvalidResponse); }
        match response.status { 401 | 403 => Err(DownloadError::AuthRequired), 410 => Err(DownloadError::ManifestStale), 409 | 412 => Err(DownloadError::SourceChanged), _ => Ok(response) }
    }
}

fn content_length(headers: &BTreeMap<String, String>) -> Option<u64> { headers.get("Content-Length")?.parse().ok() }
fn valid_content_range_headers(headers: &BTreeMap<String, String>, start: u64, total: u64) -> bool {
    let Some(value) = headers.get("Content-Range").and_then(|v| v.strip_prefix("bytes ")) else { return false; };
    let Some((range, total_value)) = value.split_once('/') else { return false; };
    let Some((actual_start, actual_end)) = range.split_once('-') else { return false; };
    let (Ok(actual_start), Ok(actual_end), Ok(actual_total)) = (actual_start.parse::<u64>(), actual_end.parse::<u64>(), total_value.parse::<u64>()) else { return false; };
    actual_start == start && actual_total == total && actual_end.checked_sub(actual_start).and_then(|length| length.checked_add(1)).is_some_and(|length| length == total.saturating_sub(start))
}

fn map_root_error(error: LocalPathError) -> DownloadError {
    match error {
        LocalPathError::UnknownDestinationRoot => DownloadError::InvalidDestinationRoot,
        _ => DownloadError::InvalidDestinationRoot,
    }
}
