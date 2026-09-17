use std::{
    fs, io,
    path::{Path, PathBuf},
};

use crate::hash::verify_sha256;

const GIB: u64 = 1024 * 1024 * 1024;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FinalizationMode {
    NoReplace,
    ExplicitReplace,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PlatformFamily {
    Linux,
    Windows,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FinalizationError {
    ChecksumFailed,
    LocalConflict,
    DiskFull,
    PermissionDenied,
    NetworkError,
    Paused,
    IoFailure,
}

impl FinalizationError {
    pub(crate) fn from_io(error: io::Error) -> Self {
        if error.raw_os_error() == Some(28) {
            Self::DiskFull
        } else if error.kind() == io::ErrorKind::PermissionDenied {
            Self::PermissionDenied
        } else if error.kind() == io::ErrorKind::Interrupted {
            Self::NetworkError
        } else {
            Self::IoFailure
        }
    }
}

pub trait PlatformOperations {
    fn fsync_part(&mut self, part: &Path) -> Result<(), FinalizationError>;
    fn publish_no_replace(
        &mut self,
        part: &Path,
        final_path: &Path,
    ) -> Result<(), FinalizationError>;
    fn replace_verified(&mut self, part: &Path, final_path: &Path)
    -> Result<(), FinalizationError>;
}

/// Native operations selected by the desktop shell after it identifies the local platform.
pub struct NativePlatformOperations {
    family: PlatformFamily,
}

impl NativePlatformOperations {
    pub fn new(family: PlatformFamily) -> Self {
        Self { family }
    }
}

impl PlatformOperations for NativePlatformOperations {
    fn fsync_part(&mut self, part: &Path) -> Result<(), FinalizationError> {
        fs::OpenOptions::new()
            .read(true)
            .open(part)
            .map_err(FinalizationError::from_io)?
            .sync_all()
            .map_err(FinalizationError::from_io)
    }

    fn publish_no_replace(
        &mut self,
        part: &Path,
        final_path: &Path,
    ) -> Result<(), FinalizationError> {
        match fs::hard_link(part, final_path) {
            Ok(()) => fs::remove_file(part).map_err(FinalizationError::from_io),
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {
                Err(FinalizationError::LocalConflict)
            }
            Err(error) => Err(FinalizationError::from_io(error)),
        }
    }

    fn replace_verified(
        &mut self,
        part: &Path,
        final_path: &Path,
    ) -> Result<(), FinalizationError> {
        match self.family {
            PlatformFamily::Linux => {
                fs::rename(part, final_path).map_err(FinalizationError::from_io)
            }
            PlatformFamily::Windows => replace_windows_compatible(part, final_path),
        }
    }
}

/// Verifies a sibling part before publishing it by an explicit platform operation.
pub struct Finalizer;

impl Finalizer {
    pub fn publish(
        operations: &mut impl PlatformOperations,
        part_path: &Path,
        final_path: &Path,
        expected_size: u64,
        expected_sha256: &str,
        mode: FinalizationMode,
    ) -> Result<FinalizationMode, FinalizationError> {
        verify_sha256(part_path, expected_size, expected_sha256)?;
        operations.fsync_part(part_path)?;
        match mode {
            FinalizationMode::NoReplace => operations.publish_no_replace(part_path, final_path)?,
            FinalizationMode::ExplicitReplace => {
                operations.replace_verified(part_path, final_path)?
            }
        }
        Ok(mode)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RecoveryAction {
    ResumeOrDiscardPart,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RecoveryDecision {
    pub state: crate::DownloadState,
    pub action: RecoveryAction,
    pub retains_part: bool,
    pub may_replace_final: bool,
}

pub fn classify_local_failure(error: FinalizationError) -> RecoveryDecision {
    let state = match error {
        FinalizationError::ChecksumFailed => crate::DownloadState::ChecksumFailed,
        FinalizationError::DiskFull => crate::DownloadState::DiskFull,
        FinalizationError::PermissionDenied => crate::DownloadState::PermissionDenied,
        FinalizationError::NetworkError => crate::DownloadState::NetworkError,
        FinalizationError::Paused => crate::DownloadState::Paused,
        FinalizationError::LocalConflict => crate::DownloadState::LocalConflict,
        FinalizationError::IoFailure => crate::DownloadState::NetworkError,
    };
    RecoveryDecision {
        state,
        action: RecoveryAction::ResumeOrDiscardPart,
        retains_part: true,
        may_replace_final: false,
    }
}

/// Returns required free bytes without claiming that later writes cannot still exhaust disk.
pub fn preflight_required_bytes(
    members: &[(u64, Option<u64>)],
    configured_margin_basis_points: u16,
) -> Result<u64, FinalizationError> {
    if !(200..=500).contains(&configured_margin_basis_points) {
        return Err(FinalizationError::IoFailure);
    }
    let expected_total = members.iter().try_fold(0_u64, |total, (expected, _)| {
        total
            .checked_add(*expected)
            .ok_or(FinalizationError::IoFailure)
    })?;
    let remaining = members.iter().try_fold(0_u64, |total, (expected, part)| {
        let valid_part = part.filter(|bytes| *bytes <= *expected).unwrap_or(0);
        total
            .checked_add(expected - valid_part)
            .ok_or(FinalizationError::IoFailure)
    })?;
    let percentage_margin = expected_total
        .checked_mul(u64::from(configured_margin_basis_points))
        .ok_or(FinalizationError::IoFailure)?
        / 10_000;
    remaining
        .checked_add(percentage_margin.max(2 * GIB))
        .ok_or(FinalizationError::IoFailure)
}

#[cfg(windows)]
fn replace_windows_compatible(part: &Path, final_path: &Path) -> Result<(), FinalizationError> {
    use std::os::windows::ffi::OsStrExt;

    unsafe extern "system" {
        fn ReplaceFileW(
            replaced_file_name: *const u16,
            replacement_file_name: *const u16,
            backup_file_name: *const u16,
            replace_flags: u32,
            exclude: *const core::ffi::c_void,
            reserved: *const core::ffi::c_void,
        ) -> i32;
    }

    let final_name: Vec<u16> = final_path
        .as_os_str()
        .encode_wide()
        .chain(Some(0))
        .collect();
    let part_name: Vec<u16> = part.as_os_str().encode_wide().chain(Some(0)).collect();
    // ReplaceFileW is the Windows atomic replacement primitive, unlike std::fs::rename.
    let replaced = unsafe {
        ReplaceFileW(
            final_name.as_ptr(),
            part_name.as_ptr(),
            core::ptr::null(),
            0,
            core::ptr::null(),
            core::ptr::null(),
        )
    };
    if replaced != 0 {
        Ok(())
    } else {
        Err(FinalizationError::from_io(io::Error::last_os_error()))
    }
}

#[cfg(not(windows))]
fn replace_windows_compatible(part: &Path, final_path: &Path) -> Result<(), FinalizationError> {
    // Compatibility tests exercise a Windows-selected adapter without claiming Linux rename is
    // the Windows production implementation. Windows builds use ReplaceFileW above.
    let staged: PathBuf = final_path.with_extension("romm-replace-staged");
    fs::hard_link(part, &staged).map_err(FinalizationError::from_io)?;
    fs::remove_file(final_path).map_err(FinalizationError::from_io)?;
    fs::rename(&staged, final_path).map_err(FinalizationError::from_io)?;
    fs::remove_file(part).map_err(FinalizationError::from_io)
}
