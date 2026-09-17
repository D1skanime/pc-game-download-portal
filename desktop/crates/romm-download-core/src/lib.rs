//! Path-free download manifest contracts.

mod engine;
mod error;
mod finalize;
mod hash;
mod http;
mod job_store;
mod manifest;
mod model;
mod path;
mod recovery;
mod scheduler;
mod transfer;

pub use engine::IntegrityDownloadEngine;
pub use error::ManifestValidationError;
pub use finalize::{
    FinalizationError, FinalizationMode, Finalizer, NativePlatformOperations, PlatformFamily,
    PlatformOperations, RecoveryAction, RecoveryDecision, classify_local_failure,
    preflight_required_bytes,
};
pub use http::{
    ConfiguredOrigin, HttpBoundaryError, HttpRequest, HttpResponse, HttpTransport,
    HttpTransportError,
};
pub use job_store::{JobStore, JobStoreError, PersistedJob};
pub use manifest::ManifestValidator;
pub use model::{DownloadState, ManifestId, MemberId, ValidatedManifest, ValidatedMember};
pub use path::{DestinationRootHandle, DestinationRootRegistry, LocalPathError, PathResolver};
pub use recovery::{RecoveryClassification, RecoveryError, RecoveryManager};
pub use scheduler::{SchedulerError, TransferPermit, TransferScheduler};
pub use transfer::{
    DownloadEngine, DownloadError, FileSink, FileSinkError, QueuedManifest, TransferOutcome,
    VecSink,
};
