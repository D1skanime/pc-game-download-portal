use std::{fs, path::PathBuf};

use romm_download_core::{
    FinalizationError, FinalizationMode, Finalizer, NativePlatformOperations, PlatformFamily,
};

const ABC_SHA256: &str = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

fn root(name: &str) -> PathBuf {
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "romm-download-core-finalization-{name}-{}-{nonce}",
        std::process::id()
    ));
    fs::create_dir_all(&root).expect("temporary root");
    root
}

#[test]
fn only_a_verified_fsynced_part_can_publish_to_an_absent_final() {
    let root = root("normal");
    let final_path = root.join("game.bin");
    let part_path = root.join(".romm-part-member");
    fs::write(&part_path, b"abc").expect("part");

    let mut operations = NativePlatformOperations::new(PlatformFamily::Linux);
    let outcome = Finalizer::publish(
        &mut operations,
        &part_path,
        &final_path,
        3,
        ABC_SHA256,
        FinalizationMode::NoReplace,
    )
    .expect("verified publish");

    assert_eq!(outcome, FinalizationMode::NoReplace);
    assert_eq!(fs::read(&final_path).expect("final"), b"abc");
    assert!(!part_path.exists());
    fs::remove_dir_all(root).expect("cleanup");
}

#[test]
fn foreign_final_survives_normal_completion_but_explicit_replace_uses_platform_adapter() {
    for platform in [PlatformFamily::Linux, PlatformFamily::Windows] {
        let root = root(match platform {
            PlatformFamily::Linux => "linux",
            PlatformFamily::Windows => "windows",
        });
        let final_path = root.join("game.bin");
        let part_path = root.join(".romm-part-member");
        fs::write(&final_path, b"foreign").expect("foreign final");
        fs::write(&part_path, b"abc").expect("part");

        let mut operations = NativePlatformOperations::new(platform);
        assert_eq!(
            Finalizer::publish(
                &mut operations,
                &part_path,
                &final_path,
                3,
                ABC_SHA256,
                FinalizationMode::NoReplace,
            )
            .expect_err("normal completion must not replace a final"),
            FinalizationError::LocalConflict
        );
        assert_eq!(
            fs::read(&final_path).expect("foreign preserved"),
            b"foreign"
        );
        assert_eq!(fs::read(&part_path).expect("part retained"), b"abc");

        assert_eq!(
            Finalizer::publish(
                &mut operations,
                &part_path,
                &final_path,
                3,
                ABC_SHA256,
                FinalizationMode::ExplicitReplace,
            )
            .expect("explicit replacement"),
            FinalizationMode::ExplicitReplace
        );
        assert_eq!(fs::read(&final_path).expect("replaced final"), b"abc");
        assert!(!part_path.exists());
        fs::remove_dir_all(root).expect("cleanup");
    }
}

#[test]
fn checksum_failure_never_promotes_or_removes_the_recoverable_part() {
    let root = root("checksum");
    let final_path = root.join("game.bin");
    let part_path = root.join(".romm-part-member");
    fs::write(&part_path, b"damaged").expect("part");

    let mut operations = NativePlatformOperations::new(PlatformFamily::Linux);
    assert_eq!(
        Finalizer::publish(
            &mut operations,
            &part_path,
            &final_path,
            7,
            ABC_SHA256,
            FinalizationMode::NoReplace,
        )
        .expect_err("checksum mismatch"),
        FinalizationError::ChecksumFailed
    );
    assert!(!final_path.exists());
    assert_eq!(fs::read(&part_path).expect("part retained"), b"damaged");
    fs::remove_dir_all(root).expect("cleanup");
}
