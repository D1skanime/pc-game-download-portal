use std::{fs, path::PathBuf};

use romm_download_core::{
    DestinationRootRegistry, DownloadState, JobStore, ManifestValidator, PersistedJob,
    RecoveryClassification, RecoveryManager,
};

const MANIFEST_ID: &str = "11111111-1111-4111-8111-111111111111";
const MEMBER_ID: &str = "22222222-2222-4222-8222-222222222222";
const ABC_SHA256: &str = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

fn root() -> PathBuf {
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "romm-download-core-recovery-{}-{nonce}",
        std::process::id()
    ));
    fs::create_dir_all(&root).unwrap();
    root
}

fn manifest(size: u64) -> romm_download_core::ValidatedManifest {
    ManifestValidator::validate(&format!(
        r#"{{"schema_version":1,"id":"{MANIFEST_ID}","created_at":"2026-09-17T00:00:00Z","expires_at":"2026-09-18T00:00:00Z","components":[],"members":[{{"file_id":"{MEMBER_ID}","destination":"Game/file.bin","size":{},"sha256":"{ABC_SHA256}","snapshot":"\"romm-snapshot\"","download":"/api/download-manifests/{MANIFEST_ID}/files/{MEMBER_ID}"}}]}}"#,
        size
    )).unwrap()
}

fn persisted(manifest: &romm_download_core::ValidatedManifest, bytes: u64) -> PersistedJob {
    let member = &manifest.members[0];
    PersistedJob::new(manifest.id, member, DownloadState::Downloading, bytes)
}

#[test]
fn atomically_persists_only_exact_recovery_identity() {
    let root = root();
    let mut registry = DestinationRootRegistry::new();
    let handle = registry.register_native_selection(&root).unwrap();
    let manifest = manifest(3);
    let store = JobStore::open(&registry, handle).unwrap();
    store.upsert(&persisted(&manifest, 2)).unwrap();

    let raw = fs::read_to_string(root.join(".romm-jobs.json")).unwrap();
    assert!(!raw.contains("token"));
    assert!(!raw.contains("/home/"));
    assert_eq!(store.load(manifest.members[0].id).unwrap().bytes, 2);
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn classifies_final_and_part_files_without_unsafe_overwrite_or_resume() {
    let root = root();
    let mut registry = DestinationRootRegistry::new();
    let handle = registry.register_native_selection(&root).unwrap();
    let manifest = manifest(3);
    let member = &manifest.members[0];
    let store = JobStore::open(&registry, handle).unwrap();
    fs::create_dir_all(root.join("Game")).unwrap();

    fs::write(root.join("Game/file.bin"), b"abc").unwrap();
    assert_eq!(
        RecoveryManager::classify(&registry, handle, &manifest, member, &store).unwrap(),
        RecoveryClassification::Completed
    );
    fs::write(root.join("Game/file.bin"), b"foreign").unwrap();
    assert_eq!(
        RecoveryManager::classify(&registry, handle, &manifest, member, &store).unwrap(),
        RecoveryClassification::LocalConflict
    );
    fs::remove_file(root.join("Game/file.bin")).unwrap();

    let part = root.join(format!("Game/.romm-part-{}", member.id));
    fs::write(&part, b"ab").unwrap();
    assert_eq!(
        RecoveryManager::classify(&registry, handle, &manifest, member, &store).unwrap(),
        RecoveryClassification::UntrustedLocalState
    );
    store.upsert(&persisted(&manifest, 2)).unwrap();
    assert_eq!(
        RecoveryManager::classify(&registry, handle, &manifest, member, &store).unwrap(),
        RecoveryClassification::Resumable { bytes: 2 }
    );
    fs::write(&part, b"abcd").unwrap();
    assert_eq!(
        RecoveryManager::classify(&registry, handle, &manifest, member, &store).unwrap(),
        RecoveryClassification::CorruptLocalState
    );
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn rejects_a_part_when_any_persisted_identity_field_differs() {
    let root = root();
    let mut registry = DestinationRootRegistry::new();
    let handle = registry.register_native_selection(&root).unwrap();
    let manifest = manifest(3);
    let member = &manifest.members[0];
    let store = JobStore::open(&registry, handle).unwrap();
    fs::create_dir_all(root.join("Game")).unwrap();
    fs::write(root.join(format!("Game/.romm-part-{}", member.id)), b"ab").unwrap();
    let mut record = persisted(&manifest, 2);
    record.snapshot = "\"another-snapshot\"".into();
    store.upsert(&record).unwrap();

    assert_eq!(
        RecoveryManager::classify(&registry, handle, &manifest, member, &store).unwrap(),
        RecoveryClassification::UntrustedLocalState
    );
    fs::remove_dir_all(root).unwrap();
}
