use romm_download_core::{
    classify_local_failure, preflight_required_bytes, DownloadState, FinalizationError,
    RecoveryAction,
};

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

    let remaining = 5_u64 * 1024 * 1024 * 1024 - 1024 + 120 * 1024 * 1024 * 1024;
    assert_eq!(required, remaining + (205_u64 * 1024 * 1024 * 1024 / 20));
}

#[test]
fn recovery_failures_preserve_the_part_and_offer_the_bounded_recovery_action() {
    for (error, state) in [
        (FinalizationError::DiskFull, DownloadState::DiskFull),
        (FinalizationError::PermissionDenied, DownloadState::PermissionDenied),
        (FinalizationError::NetworkError, DownloadState::NetworkError),
        (FinalizationError::Paused, DownloadState::Paused),
        (FinalizationError::ChecksumFailed, DownloadState::ChecksumFailed),
    ] {
        let recovery = classify_local_failure(error);
        assert_eq!(recovery.state, state);
        assert_eq!(recovery.action, RecoveryAction::ResumeOrDiscardPart);
        assert!(recovery.retains_part);
        assert!(!recovery.may_replace_final);
    }
}
