use std::{fs, path::Path};

use romm_download_core::{
    DestinationRootRegistry, DownloadState, FinalizationError, FinalizationMode,
    IntegrityDownloadEngine, JobStore, ManifestValidator, PlatformOperations, RecoveryAction,
    classify_local_failure, preflight_required_bytes,
};

const MANIFEST_ID: &str = "11111111-1111-4111-8111-111111111111";
const MEMBER_ID: &str = "22222222-2222-4222-8222-222222222222";
const ABC_SHA256: &str = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

struct DiskFullOperations;

impl PlatformOperations for DiskFullOperations {
    fn fsync_part(&mut self, _: &Path) -> Result<(), FinalizationError> {
        Err(FinalizationError::DiskFull)
    }

    fn publish_no_replace(&mut self, _: &Path, _: &Path) -> Result<(), FinalizationError> {
        unreachable!("fsync failure must stop publication")
    }

    fn replace_verified(&mut self, _: &Path, _: &Path) -> Result<(), FinalizationError> {
        unreachable!("fsync failure must stop publication")
    }
}

fn manifest() -> romm_download_core::ValidatedManifest {
    ManifestValidator::validate(&format!(
        r#"{{"schema_version":1,"id":"{MANIFEST_ID}","created_at":"2026-09-17T00:00:00Z","expires_at":"2026-09-18T00:00:00Z","components":[],"members":[{{"file_id":"{MEMBER_ID}","destination":"Game/file.bin","size":3,"sha256":"{ABC_SHA256}","snapshot":"\"snapshot\"","download":"/api/download-manifests/{MANIFEST_ID}/files/{MEMBER_ID}"}}]}}"#
    ))
    .expect("manifest")
}

#[test]
fn preflight_uses_only_matching_partial_bytes_and_the_conservative_margin() {
    let required = preflight_required_bytes(
        &[
            (5_u64 * 1024 * 1024 * 1024, Some(1024)),
            (80 * 1024 * 1024 * 1024, Some(81 * 1024 * 1024 * 1024)),
            (120 * 1024 * 1024 * 1024, None),
        ],
        500,
    )
    .expect("valid preflight");

    let remaining = 205_u64 * 1024 * 1024 * 1024 - 1024;
    assert_eq!(required, remaining + (205_u64 * 1024 * 1024 * 1024 / 20));
}

#[test]
fn recovery_failures_preserve_the_part_and_offer_the_bounded_recovery_action() {
    for (error, state) in [
        (FinalizationError::DiskFull, DownloadState::DiskFull),
        (
            FinalizationError::PermissionDenied,
            DownloadState::PermissionDenied,
        ),
        (FinalizationError::NetworkError, DownloadState::NetworkError),
        (FinalizationError::Paused, DownloadState::Paused),
        (
            FinalizationError::ChecksumFailed,
            DownloadState::ChecksumFailed,
        ),
    ] {
        let recovery = classify_local_failure(error);
        assert_eq!(recovery.state, state);
        assert_eq!(recovery.action, RecoveryAction::ResumeOrDiscardPart);
        assert!(recovery.retains_part);
        assert!(!recovery.may_replace_final);
    }
}

#[test]
fn injected_disk_full_persists_recoverable_job_state_without_touching_a_final() {
    let root =
        std::env::temp_dir().join(format!("romm-download-core-engine-{}", std::process::id()));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(root.join("Game")).expect("root");
    let mut registry = DestinationRootRegistry::new();
    let handle = registry.register_native_selection(&root).expect("handle");
    let manifest = manifest();
    let member = &manifest.members[0];
    let part = root.join(format!("Game/.romm-part-{}", member.id));
    let final_path = root.join("Game/file.bin");
    fs::write(&part, b"abc").expect("part");
    fs::write(&final_path, b"foreign").expect("foreign final");
    let store = JobStore::open(&registry, handle).expect("store");
    let mut operations = DiskFullOperations;
    let mut engine = IntegrityDownloadEngine::new(&mut operations);

    assert_eq!(
        engine
            .finalize_member(
                &registry,
                handle,
                &manifest,
                member,
                &store,
                FinalizationMode::NoReplace,
            )
            .expect_err("disk full"),
        FinalizationError::DiskFull
    );
    assert_eq!(
        store.load(member.id).expect("recovery job").state,
        DownloadState::DiskFull
    );
    assert_eq!(fs::read(&part).expect("part retained"), b"abc");
    assert_eq!(fs::read(&final_path).expect("final preserved"), b"foreign");
    fs::remove_dir_all(root).expect("cleanup");
}
