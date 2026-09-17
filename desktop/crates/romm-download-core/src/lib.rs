//! Path-free download manifest contracts.

mod error;
mod job_store;
mod manifest;
mod model;
mod path;
mod recovery;

pub use error::ManifestValidationError;
pub use job_store::{JobStore, JobStoreError, PersistedJob};
pub use manifest::ManifestValidator;
pub use model::{DownloadState, ManifestId, MemberId, ValidatedManifest, ValidatedMember};
pub use path::{DestinationRootHandle, DestinationRootRegistry, LocalPathError, PathResolver};
pub use recovery::{RecoveryClassification, RecoveryError, RecoveryManager};
