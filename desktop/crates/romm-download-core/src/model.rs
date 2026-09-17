use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// An opaque server-owned manifest identity.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Hash, PartialEq, Serialize)]
#[serde(transparent)]
pub struct ManifestId(Uuid);

impl ManifestId {
    pub(crate) const fn new(value: Uuid) -> Self {
        Self(value)
    }
}

impl std::fmt::Display for ManifestId {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        self.0.fmt(formatter)
    }
}

impl std::str::FromStr for ManifestId {
    type Err = uuid::Error;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        uuid::Uuid::parse_str(value).map(Self::new)
    }
}

/// An opaque server-owned manifest member identity.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Hash, PartialEq, Serialize)]
#[serde(transparent)]
pub struct MemberId(Uuid);

impl MemberId {
    pub(crate) const fn new(value: Uuid) -> Self {
        Self(value)
    }
}

impl std::fmt::Display for MemberId {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        self.0.fmt(formatter)
    }
}

/// All normal and recovery states permitted in persisted job data.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum DownloadState {
    Queued,
    Preparing,
    Ready,
    Downloading,
    Paused,
    Verifying,
    Completed,
    AuthRequired,
    SourceChanged,
    ManifestStale,
    LocalConflict,
    DiskFull,
    PermissionDenied,
    NetworkError,
    ChecksumFailed,
}

/// Immutable member data safe to pass to later core stages.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ValidatedMember {
    pub id: MemberId,
    pub destination: String,
    pub size: u64,
    pub sha256: String,
    pub snapshot: String,
    pub download: String,
}

/// Immutable manifest data safe to persist as a job input.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ValidatedManifest {
    pub id: ManifestId,
    pub members: Vec<ValidatedMember>,
}
