use std::{
    collections::HashMap,
    fs,
    path::{Path, PathBuf},
};

use unicode_casefold::{Locale, UnicodeCaseFold, Variant};
use unicode_normalization::UnicodeNormalization;
use uuid::Uuid;

use crate::MemberId;

/// A bounded error returned by the local filesystem trust boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LocalPathError {
    InvalidNativeSelection,
    UnknownDestinationRoot,
    UnsafeDestination,
    PortableCollision,
    SymlinkEscape,
    IoFailure,
}

/// An opaque core-issued reference to a currently registered destination root.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub struct DestinationRootHandle(Uuid);

/// Owns canonical destination roots and is the only path-bearing registration seam.
#[derive(Default)]
pub struct DestinationRootRegistry {
    roots: HashMap<DestinationRootHandle, PathBuf>,
}

impl DestinationRootRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn register_native_selection(
        &mut self,
        selected_path: impl AsRef<Path>,
    ) -> Result<DestinationRootHandle, LocalPathError> {
        let canonical =
            fs::canonicalize(selected_path).map_err(|_| LocalPathError::InvalidNativeSelection)?;
        if !canonical.is_dir() {
            return Err(LocalPathError::InvalidNativeSelection);
        }
        let handle = DestinationRootHandle(Uuid::new_v4());
        self.roots.insert(handle, canonical);
        Ok(handle)
    }

    pub fn expire(&mut self, handle: DestinationRootHandle) {
        self.roots.remove(&handle);
    }

    pub(crate) fn root(&self, handle: DestinationRootHandle) -> Result<&Path, LocalPathError> {
        self.roots
            .get(&handle)
            .map(PathBuf::as_path)
            .ok_or(LocalPathError::UnknownDestinationRoot)
    }
}

/// A checked target, retained internally so paths never become serialized authority.
#[derive(Debug)]
pub struct PreparedTarget {
    pub(crate) final_path: PathBuf,
    pub(crate) part_path: PathBuf,
}

/// Resolves and re-proves portable local targets beneath a registered root.
pub struct PathResolver;

impl PathResolver {
    pub fn prepare_member(
        registry: &DestinationRootRegistry,
        handle: DestinationRootHandle,
        destination: &str,
        member_id: &MemberId,
    ) -> Result<PreparedTarget, LocalPathError> {
        validate_portable_destination(destination)?;
        let root = registry.root(handle)?;
        let mut current = root.to_path_buf();
        let segments: Vec<_> = destination.split('/').collect();

        for (index, segment) in segments.iter().enumerate() {
            let candidate = current.join(segment);
            let is_final = index + 1 == segments.len();
            reject_portable_tree_collision(&current, segment)?;

            if !is_final {
                if !candidate.exists() {
                    fs::create_dir(&candidate).map_err(|_| LocalPathError::IoFailure)?;
                }
                prove_directory_within_root(root, &candidate)?;
                current = candidate;
            }
        }

        let final_path = root.join(destination);
        prove_target_within_root(root, &final_path)?;
        let part_path = final_path.with_file_name(format!(".romm-part-{member_id}"));
        prove_target_within_root(root, &part_path)?;
        Ok(PreparedTarget {
            final_path,
            part_path,
        })
    }
}

fn validate_portable_destination(destination: &str) -> Result<(), LocalPathError> {
    if destination.is_empty()
        || destination.starts_with('/')
        || destination.starts_with('\\')
        || destination.contains('\\')
        || destination.contains(':')
        || destination.chars().any(char::is_control)
    {
        return Err(LocalPathError::UnsafeDestination);
    }

    for segment in destination.split('/') {
        if segment.is_empty()
            || segment == "."
            || segment == ".."
            || segment.ends_with('.')
            || segment.ends_with(' ')
            || is_windows_reserved_name(segment)
        {
            return Err(LocalPathError::UnsafeDestination);
        }
    }
    Ok(())
}

fn is_windows_reserved_name(segment: &str) -> bool {
    let stem = segment
        .split('.')
        .next()
        .unwrap_or_default()
        .to_ascii_uppercase();
    matches!(stem.as_str(), "CON" | "NUL" | "PRN" | "AUX")
        || (stem.len() == 4
            && (stem.starts_with("COM") || stem.starts_with("LPT"))
            && matches!(stem.as_bytes()[3], b'1'..=b'9'))
}

fn reject_portable_tree_collision(
    parent: &Path,
    expected_name: &str,
) -> Result<(), LocalPathError> {
    let entries = fs::read_dir(parent).map_err(|_| LocalPathError::IoFailure)?;
    for entry in entries {
        let entry = entry.map_err(|_| LocalPathError::IoFailure)?;
        let name = entry.file_name();
        let Some(name) = name.to_str() else {
            return Err(LocalPathError::PortableCollision);
        };
        if name == expected_name {
            continue;
        }
        if portable_names_collide(name, expected_name) {
            return Err(LocalPathError::PortableCollision);
        }
    }
    Ok(())
}

fn portable_names_collide(left: &str, right: &str) -> bool {
    left == right
        || left
            .case_fold_with(Variant::Full, Locale::NonTurkic)
            .eq(right.case_fold_with(Variant::Full, Locale::NonTurkic))
        || left.nfc().eq(right.nfc())
        || left.nfd().eq(right.nfd())
}

fn prove_directory_within_root(root: &Path, path: &Path) -> Result<(), LocalPathError> {
    let metadata = fs::symlink_metadata(path).map_err(|_| LocalPathError::IoFailure)?;
    if metadata.file_type().is_symlink() {
        return Err(LocalPathError::SymlinkEscape);
    }
    let canonical = fs::canonicalize(path).map_err(|_| LocalPathError::IoFailure)?;
    if !canonical.starts_with(root) || !canonical.is_dir() {
        return Err(LocalPathError::SymlinkEscape);
    }
    Ok(())
}

fn prove_target_within_root(root: &Path, path: &Path) -> Result<(), LocalPathError> {
    let parent = path.parent().ok_or(LocalPathError::SymlinkEscape)?;
    prove_directory_within_root(root, parent)?;
    match fs::symlink_metadata(path) {
        Ok(metadata) => {
            if metadata.file_type().is_symlink() {
                return Err(LocalPathError::SymlinkEscape);
            }
            let canonical = fs::canonicalize(path).map_err(|_| LocalPathError::IoFailure)?;
            if !canonical.starts_with(root) {
                return Err(LocalPathError::SymlinkEscape);
            }
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(_) => return Err(LocalPathError::IoFailure),
    }
    Ok(())
}
