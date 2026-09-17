use core::fmt;

/// A bounded public error category for untrusted manifest input.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ManifestValidationError {
    InvalidManifest,
    UnsupportedSchemaVersion,
    InvalidManifestId,
    InvalidMemberId,
    DuplicateMemberId,
    InvalidDestination,
    DestinationCollision,
    InvalidSize,
    InvalidSha256,
    InvalidSnapshot,
    InvalidDownloadUrl,
}

impl fmt::Display for ManifestValidationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::InvalidManifest => "invalid_manifest",
            Self::UnsupportedSchemaVersion => "unsupported_schema_version",
            Self::InvalidManifestId => "invalid_manifest_id",
            Self::InvalidMemberId => "invalid_member_id",
            Self::DuplicateMemberId => "duplicate_member_id",
            Self::InvalidDestination => "invalid_destination",
            Self::DestinationCollision => "destination_collision",
            Self::InvalidSize => "invalid_size",
            Self::InvalidSha256 => "invalid_sha256",
            Self::InvalidSnapshot => "invalid_snapshot",
            Self::InvalidDownloadUrl => "invalid_download_url",
        })
    }
}

impl std::error::Error for ManifestValidationError {}
