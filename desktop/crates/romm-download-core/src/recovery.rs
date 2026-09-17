use std::{fs, io::Read};

use sha2::{Digest, Sha256};

use crate::{
    DestinationRootHandle, DestinationRootRegistry, JobStore, JobStoreError, LocalPathError,
    PathResolver, ValidatedManifest, ValidatedMember,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RecoveryClassification {
    Completed,
    LocalConflict,
    Resumable { bytes: u64 },
    UntrustedLocalState,
    CorruptLocalState,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RecoveryError {
    LocalPath(LocalPathError),
    JobStore(JobStoreError),
    IoFailure,
}

/// Classifies existing local candidates without accepting filename coincidence as identity.
pub struct RecoveryManager;

impl RecoveryManager {
    pub fn classify(
        registry: &DestinationRootRegistry,
        handle: DestinationRootHandle,
        manifest: &ValidatedManifest,
        member: &ValidatedMember,
        store: &JobStore,
    ) -> Result<RecoveryClassification, RecoveryError> {
        let target =
            PathResolver::prepare_member(registry, handle, &member.destination, &member.id)
                .map_err(RecoveryError::LocalPath)?;

        if target.final_path.exists() {
            return if file_sha256_matches(&target.final_path, member)? {
                Ok(RecoveryClassification::Completed)
            } else {
                Ok(RecoveryClassification::LocalConflict)
            };
        }
        if !target.part_path.exists() {
            return Ok(RecoveryClassification::UntrustedLocalState);
        }

        let size = fs::metadata(&target.part_path)
            .map_err(|_| RecoveryError::IoFailure)?
            .len();
        if size > member.size {
            return Ok(RecoveryClassification::CorruptLocalState);
        }
        let saved = store
            .load_optional(member.id)
            .map_err(RecoveryError::JobStore)?;
        if size < member.size
            && saved.is_some_and(|job| job.matches_member(manifest.id, member) && job.bytes == size)
        {
            return Ok(RecoveryClassification::Resumable { bytes: size });
        }
        Ok(RecoveryClassification::UntrustedLocalState)
    }
}

fn file_sha256_matches(
    path: &std::path::Path,
    member: &ValidatedMember,
) -> Result<bool, RecoveryError> {
    let metadata = fs::metadata(path).map_err(|_| RecoveryError::IoFailure)?;
    if metadata.len() != member.size {
        return Ok(false);
    }
    let mut file = fs::File::open(path).map_err(|_| RecoveryError::IoFailure)?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|_| RecoveryError::IoFailure)?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()) == member.sha256)
}
