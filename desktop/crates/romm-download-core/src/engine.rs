use crate::{
    DestinationRootHandle, DestinationRootRegistry, DownloadState, FinalizationError,
    FinalizationMode, Finalizer, JobStore, PersistedJob, PlatformOperations, ValidatedManifest,
    ValidatedMember, classify_local_failure,
};

/// Coordinates verified local completion with an atomic persisted job-state transition.
pub struct IntegrityDownloadEngine<'a, O: PlatformOperations> {
    operations: &'a mut O,
}

impl<'a, O: PlatformOperations> IntegrityDownloadEngine<'a, O> {
    pub fn new(operations: &'a mut O) -> Self {
        Self { operations }
    }

    pub fn finalize_member(
        &mut self,
        registry: &DestinationRootRegistry,
        handle: DestinationRootHandle,
        manifest: &ValidatedManifest,
        member: &ValidatedMember,
        store: &JobStore,
        mode: FinalizationMode,
    ) -> Result<DownloadState, FinalizationError> {
        let target =
            crate::PathResolver::prepare_member(registry, handle, &member.destination, &member.id)
                .map_err(|_| FinalizationError::PermissionDenied)?;
        match Finalizer::publish(
            self.operations,
            &target.part_path,
            &target.final_path,
            member.size,
            &member.sha256,
            mode,
        ) {
            Ok(_) => {
                let completed =
                    PersistedJob::new(manifest.id, member, DownloadState::Completed, member.size);
                store
                    .upsert(&completed)
                    .map_err(|_| FinalizationError::IoFailure)?;
                Ok(DownloadState::Completed)
            }
            Err(error) => {
                let bytes = std::fs::metadata(&target.part_path)
                    .map(|metadata| metadata.len())
                    .unwrap_or(0);
                let recovery = classify_local_failure(error);
                let retained =
                    PersistedJob::new(manifest.id, member, recovery.state, bytes.min(member.size));
                store
                    .upsert(&retained)
                    .map_err(|_| FinalizationError::IoFailure)?;
                Err(error)
            }
        }
    }
}
