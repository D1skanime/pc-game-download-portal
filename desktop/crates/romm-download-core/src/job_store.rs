use std::{collections::HashMap, fs, path::PathBuf};

use serde::{Deserialize, Serialize};

use crate::{
    DestinationRootHandle, DestinationRootRegistry, DownloadState, LocalPathError, ManifestId,
    MemberId, ValidatedMember,
};

const STORE_NAME: &str = ".romm-jobs.json";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum JobStoreError {
    LocalPath(LocalPathError),
    InvalidState,
    IoFailure,
}

/// The exact, path-free identity needed to resume one local part file.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct PersistedJob {
    pub manifest_id: ManifestId,
    pub member_id: MemberId,
    pub expected_size: u64,
    pub sha256: String,
    pub snapshot: String,
    pub destination: String,
    pub state: DownloadState,
    pub bytes: u64,
}

impl PersistedJob {
    pub fn new(
        manifest_id: ManifestId,
        member: &ValidatedMember,
        state: DownloadState,
        bytes: u64,
    ) -> Self {
        Self {
            manifest_id,
            member_id: member.id,
            expected_size: member.size,
            sha256: member.sha256.clone(),
            snapshot: member.snapshot.clone(),
            destination: member.destination.clone(),
            state,
            bytes,
        }
    }

    pub(crate) fn matches_member(&self, manifest_id: ManifestId, member: &ValidatedMember) -> bool {
        self.manifest_id == manifest_id
            && self.member_id == member.id
            && self.expected_size == member.size
            && self.sha256 == member.sha256
            && self.snapshot == member.snapshot
            && self.destination == member.destination
            && self.bytes <= member.size
    }
}

/// Client-private atomic per-member recovery record storage.
pub struct JobStore {
    file: PathBuf,
}

impl JobStore {
    pub fn open(
        registry: &DestinationRootRegistry,
        handle: DestinationRootHandle,
    ) -> Result<Self, JobStoreError> {
        let root = registry.root(handle).map_err(JobStoreError::LocalPath)?;
        let file = root.join(STORE_NAME);
        Ok(Self { file })
    }

    pub fn load(&self, member_id: MemberId) -> Result<PersistedJob, JobStoreError> {
        self.read_all()?
            .remove(&member_id.to_string())
            .ok_or(JobStoreError::InvalidState)
    }

    pub fn load_optional(
        &self,
        member_id: MemberId,
    ) -> Result<Option<PersistedJob>, JobStoreError> {
        Ok(self.read_all()?.remove(&member_id.to_string()))
    }

    pub fn upsert(&self, job: &PersistedJob) -> Result<(), JobStoreError> {
        if job.bytes > job.expected_size {
            return Err(JobStoreError::InvalidState);
        }
        let mut jobs = self.read_all()?;
        jobs.insert(job.member_id.to_string(), job.clone());
        let encoded = serde_json::to_vec(&jobs).map_err(|_| JobStoreError::InvalidState)?;
        let temporary = self.file.with_extension("json.tmp");
        fs::write(&temporary, encoded).map_err(|_| JobStoreError::IoFailure)?;
        fs::rename(&temporary, &self.file).map_err(|_| JobStoreError::IoFailure)
    }

    fn read_all(&self) -> Result<HashMap<String, PersistedJob>, JobStoreError> {
        if !self.file.exists() {
            return Ok(HashMap::new());
        }
        let raw = fs::read(&self.file).map_err(|_| JobStoreError::IoFailure)?;
        serde_json::from_slice(&raw).map_err(|_| JobStoreError::InvalidState)
    }
}
