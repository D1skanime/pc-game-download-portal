use std::collections::BTreeMap;

use crate::{
    ConfiguredOrigin, DestinationRootHandle, DestinationRootRegistry, HttpRequest, HttpResponse,
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
        let origin = self.origin.clone().ok_or(DownloadError::InvalidResponse)?;
        let mut headers = BTreeMap::new();
        if offset != 0 {
            headers.insert("Range".to_owned(), format!("bytes={offset}-"));
            headers.insert("If-Match".to_owned(), member.snapshot.clone());
        }
        let response = self.request(&origin, &member.download, headers)?;
        if response.status == 416 {
            return if offset == member.size {
                Ok(TransferOutcome::VerificationCandidate)
            } else {
                Err(DownloadError::InvalidResponse)
            };
        }
        let expected = member
            .size
            .checked_sub(offset)
            .ok_or(DownloadError::CorruptLocalState)?;
        if offset == 0 {
            if response.status != 200 || exact_length(&response, expected).is_err() {
                return Err(DownloadError::InvalidResponse);
            }
        } else if response.status != 206
            || !valid_content_range(&response, offset, member.size)
            || exact_length(&response, expected).is_err()
        {
            return Err(DownloadError::InvalidResponse);
        }
        sink.append(&response.body)
            .map_err(|_| DownloadError::IoFailure)?;
        Ok(TransferOutcome::Downloaded { bytes: member.size })
    }

    fn request(
        &mut self,
        origin: &ConfiguredOrigin,
        route: &str,
        mut headers: BTreeMap<String, String>,
    ) -> Result<HttpResponse, DownloadError> {
        let url = origin
            .join_relative(route)
            .map_err(|_| DownloadError::InvalidResponse)?;
        headers.insert("Authorization".to_owned(), format!("Bearer {}", self.token));
        let request = HttpRequest { url, headers };
        self.last_request = Some(request.clone());
        let response = self
            .transport
            .execute(request)
            .map_err(|_| DownloadError::NetworkError)?;
        if response
            .final_url
            .as_deref()
            .is_some_and(|url| !origin.contains_url(url))
        {
            return Err(DownloadError::InvalidResponse);
        }
        match response.status {
            401 | 403 => Err(DownloadError::AuthRequired),
            410 => Err(DownloadError::ManifestStale),
            409 | 412 => Err(DownloadError::SourceChanged),
            _ => Ok(response),
        }
    }
}

fn map_root_error(error: LocalPathError) -> DownloadError {
    match error {
        LocalPathError::UnknownDestinationRoot => DownloadError::InvalidDestinationRoot,
        _ => DownloadError::InvalidDestinationRoot,
    }
}

fn exact_length(response: &HttpResponse, expected: u64) -> Result<(), ()> {
    let length = response
        .headers
        .get("Content-Length")
        .ok_or(())?
        .parse::<u64>()
        .map_err(|_| ())?;
    if length == expected && u64::try_from(response.body.len()).map_err(|_| ())? == expected {
        Ok(())
    } else {
        Err(())
    }
}

fn valid_content_range(response: &HttpResponse, start: u64, total: u64) -> bool {
    let Some(value) = response.headers.get("Content-Range") else {
        return false;
    };
    let Some(value) = value.strip_prefix("bytes ") else {
        return false;
    };
    let Some((range, total_value)) = value.split_once('/') else {
        return false;
    };
    let Some((actual_start, actual_end)) = range.split_once('-') else {
        return false;
    };
    let (Ok(actual_start), Ok(actual_end), Ok(actual_total)) = (
        actual_start.parse::<u64>(),
        actual_end.parse::<u64>(),
        total_value.parse::<u64>(),
    ) else {
        return false;
    };
    actual_start == start
        && actual_total == total
        && actual_end
            .checked_sub(actual_start)
            .and_then(|length| length.checked_add(1))
            .is_some_and(|length| length == total.saturating_sub(start))
}
