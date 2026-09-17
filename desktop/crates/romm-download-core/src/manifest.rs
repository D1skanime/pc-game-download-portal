use std::collections::HashSet;

use serde::Deserialize;
use unicode_casefold::{Locale, UnicodeCaseFold, Variant};
use unicode_normalization::UnicodeNormalization;
use uuid::Uuid;

use crate::{ManifestId, ManifestValidationError, MemberId, ValidatedManifest, ValidatedMember};

const SCHEMA_VERSION: u64 = 1;

/// Validates untrusted Phase-14 manifest JSON before it can become job input.
pub struct ManifestValidator;

impl ManifestValidator {
    pub fn validate(input: &str) -> Result<ValidatedManifest, ManifestValidationError> {
        let manifest: RawManifest =
            serde_json::from_str(input).map_err(|_| ManifestValidationError::InvalidManifest)?;

        if manifest.schema_version != SCHEMA_VERSION {
            return Err(ManifestValidationError::UnsupportedSchemaVersion);
        }
        if manifest.created_at.is_empty() || manifest.expires_at.is_empty() {
            return Err(ManifestValidationError::InvalidManifest);
        }
        if manifest
            .components
            .iter()
            .any(|component| component.component_id == 0 || component.kind.is_empty())
        {
            return Err(ManifestValidationError::InvalidManifest);
        }

        let manifest_id = Uuid::parse_str(&manifest.id)
            .map(ManifestId::new)
            .map_err(|_| ManifestValidationError::InvalidManifestId)?;
        let mut member_ids = HashSet::new();
        let mut destinations = HashSet::new();
        let mut case_folded_destinations = HashSet::new();
        let mut nfc_destinations = HashSet::new();
        let mut nfd_destinations = HashSet::new();
        let mut members = Vec::with_capacity(manifest.members.len());

        for member in manifest.members {
            let member_id = Uuid::parse_str(&member.file_id)
                .map(MemberId::new)
                .map_err(|_| ManifestValidationError::InvalidMemberId)?;
            if !member_ids.insert(member_id) {
                return Err(ManifestValidationError::DuplicateMemberId);
            }
            if !is_safe_relative_destination(&member.destination) {
                return Err(ManifestValidationError::InvalidDestination);
            }
            let case_folded = member
                .destination
                .case_fold_with(Variant::Full, Locale::NonTurkic)
                .collect::<String>();
            let nfc = member.destination.nfc().collect::<String>();
            let nfd = member.destination.nfd().collect::<String>();
            if !destinations.insert(member.destination.clone())
                || !case_folded_destinations.insert(case_folded)
                || !nfc_destinations.insert(nfc)
                || !nfd_destinations.insert(nfd)
            {
                return Err(ManifestValidationError::DestinationCollision);
            }
            let size = member
                .size
                .as_u64()
                .ok_or(ManifestValidationError::InvalidSize)?;
            if !is_lowercase_sha256(&member.sha256) {
                return Err(ManifestValidationError::InvalidSha256);
            }
            if !is_strong_snapshot(&member.snapshot) {
                return Err(ManifestValidationError::InvalidSnapshot);
            }
            if member.download != format!("/api/download-manifests/{manifest_id}/files/{member_id}")
            {
                return Err(ManifestValidationError::InvalidDownloadUrl);
            }

            members.push(ValidatedMember {
                id: member_id,
                destination: member.destination,
                size,
                sha256: member.sha256,
                snapshot: member.snapshot,
                download: member.download,
            });
        }

        Ok(ValidatedManifest {
            id: manifest_id,
            members,
        })
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawManifest {
    schema_version: u64,
    id: String,
    created_at: String,
    expires_at: String,
    components: Vec<RawComponent>,
    members: Vec<RawMember>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawComponent {
    component_id: u64,
    kind: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawMember {
    file_id: String,
    destination: String,
    size: serde_json::Value,
    sha256: String,
    snapshot: String,
    download: String,
}

fn is_safe_relative_destination(destination: &str) -> bool {
    !destination.is_empty()
        && !destination.starts_with('/')
        && !destination.contains('\\')
        && !destination.chars().any(char::is_control)
        && destination
            .split('/')
            .all(|segment| !segment.is_empty() && segment != "." && segment != "..")
}

fn is_lowercase_sha256(hash: &str) -> bool {
    hash.len() == 64
        && hash
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn is_strong_snapshot(snapshot: &str) -> bool {
    let Some(value) = snapshot
        .strip_prefix('"')
        .and_then(|value| value.strip_suffix('"'))
    else {
        return false;
    };

    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte == b'!' || (b'#'..=b'~').contains(&byte))
}
