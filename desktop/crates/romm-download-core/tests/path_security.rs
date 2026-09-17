use std::{fs, path::PathBuf};

use romm_download_core::{
    DestinationRootRegistry, LocalPathError, ManifestValidator, MemberId, PathResolver,
};

const MANIFEST_ID: &str = "11111111-1111-4111-8111-111111111111";
const MEMBER_ID: &str = "22222222-2222-4222-8222-222222222222";

fn root(name: &str) -> PathBuf {
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "romm-download-core-{name}-{}-{nonce}",
        std::process::id()
    ));
    fs::create_dir_all(&root).unwrap();
    root
}

fn member(destination: &str) -> romm_download_core::ValidatedMember {
    let input = format!(
        r#"{{"schema_version":1,"id":"{MANIFEST_ID}","created_at":"2026-09-17T00:00:00Z","expires_at":"2026-09-18T00:00:00Z","components":[],"members":[{{"file_id":"{MEMBER_ID}","destination":"{destination}","size":3,"sha256":"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","snapshot":"\"romm-snapshot\"","download":"/api/download-manifests/{MANIFEST_ID}/files/{MEMBER_ID}"}}]}}"#
    );
    ManifestValidator::validate(&input)
        .unwrap()
        .members
        .remove(0)
}

#[test]
fn rejects_portable_unsafe_destination_forms_before_creating_files() {
    let root = root("unsafe");
    let mut registry = DestinationRootRegistry::new();
    let handle = registry.register_native_selection(&root).unwrap();

    for destination in [
        "../foo",
        "..\\foo",
        "/foo",
        "\\foo",
        "C:\\foo",
        "C:foo",
        "\\\\server\\share",
        "//server/share",
        "Game/../foo",
        "Game:bad/file",
        "Game/\u{0000}file",
        "CON/file",
        "NUL",
        "PRN.txt",
        "AUX",
        "COM1/file",
        "LPT1/file",
        "Game/file. ",
    ] {
        assert_eq!(
            PathResolver::prepare_member(
                &registry,
                handle,
                destination,
                &member("Game/file.bin").id
            )
            .unwrap_err(),
            LocalPathError::UnsafeDestination,
            "{destination}"
        );
    }
    assert!(fs::read_dir(&root).unwrap().next().is_none());
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn rejects_forged_expired_and_portably_colliding_destination_handles() {
    let root = root("handles");
    fs::create_dir_all(root.join("Game")).unwrap();
    fs::write(root.join("Game/File.bin"), b"foreign").unwrap();

    let mut registry = DestinationRootRegistry::new();
    let handle = registry.register_native_selection(&root).unwrap();
    let member_id = member("Game/file.bin").id;
    assert_eq!(
        PathResolver::prepare_member(&registry, handle, "Game/file.bin", &member_id).unwrap_err(),
        LocalPathError::PortableCollision
    );

    registry.expire(handle);
    assert_eq!(
        PathResolver::prepare_member(&registry, handle, "Game/file.bin", &member_id).unwrap_err(),
        LocalPathError::UnknownDestinationRoot
    );
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn rejects_unicode_normalization_collisions_in_existing_tree() {
    let root = root("unicode");
    fs::create_dir_all(root.join("Game")).unwrap();
    fs::write(root.join("Game/café.bin"), b"foreign").unwrap();
    let mut registry = DestinationRootRegistry::new();
    let handle = registry.register_native_selection(&root).unwrap();
    let member_id = member("Game/café.bin").id;

    assert_eq!(
        PathResolver::prepare_member(&registry, handle, "Game/café.bin", &member_id).unwrap_err(),
        LocalPathError::PortableCollision
    );
    fs::remove_dir_all(root).unwrap();
}

#[cfg(unix)]
#[test]
fn rejects_symlink_components_that_escape_the_canonical_root() {
    use std::os::unix::fs::symlink;

    let destination_root = root("symlink");
    let outside = root("outside");
    symlink(&outside, destination_root.join("Game")).unwrap();
    let mut registry = DestinationRootRegistry::new();
    let handle = registry
        .register_native_selection(&destination_root)
        .unwrap();
    let member_id: MemberId = member("Game/file.bin").id;

    assert_eq!(
        PathResolver::prepare_member(&registry, handle, "Game/file.bin", &member_id).unwrap_err(),
        LocalPathError::SymlinkEscape
    );
    fs::remove_dir_all(destination_root).unwrap();
    fs::remove_dir_all(outside).unwrap();
}
