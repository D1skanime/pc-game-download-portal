use romm_download_core::{ManifestValidationError, ManifestValidator};

const MANIFEST_ID: &str = "11111111-1111-4111-8111-111111111111";
const MEMBER_ID: &str = "22222222-2222-4222-8222-222222222222";

fn manifest(member_json: &str) -> String {
    format!(
        r#"{{
            "schema_version": 1,
            "id": "{MANIFEST_ID}",
            "created_at": "2026-09-17T00:00:00Z",
            "expires_at": "2026-09-18T00:00:00Z",
            "components": [],
            "members": [{member_json}]
        }}"#
    )
}

fn member(destination: &str) -> String {
    format!(
        r#"{{
            "file_id": "{MEMBER_ID}",
            "destination": "{destination}",
            "size": 5368709120,
            "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "snapshot": "\\\"romm-snapshot\\\"",
            "download": "/api/download-manifests/{MANIFEST_ID}/files/{MEMBER_ID}"
        }}"#
    )
}

#[test]
fn validates_only_canonical_path_free_members() {
    let validated = ManifestValidator::validate(&manifest(&member("Game/file.bin"))).unwrap();

    assert_eq!(validated.id.to_string(), MANIFEST_ID);
    assert_eq!(validated.members.len(), 1);
    assert_eq!(validated.members[0].id.to_string(), MEMBER_ID);
    assert_eq!(validated.members[0].size, 5_368_709_120);
    assert_eq!(validated.members[0].snapshot, "\"romm-snapshot\"");
}

#[test]
fn rejects_untrusted_wire_values() {
    let cases = [
        (manifest(&member("Game/file.bin")).replace("\"schema_version\": 1", "\"schema_version\": 2"), ManifestValidationError::UnsupportedSchemaVersion),
        (manifest(&member("Game/file.bin")).replace(MEMBER_ID, "not-a-uuid"), ManifestValidationError::InvalidMemberId),
        (manifest(&member("Game/file.bin")).replace("5368709120", "-1"), ManifestValidationError::InvalidSize),
        (manifest(&member("Game/file.bin")).replace("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "ABC"), ManifestValidationError::InvalidSha256),
        (manifest(&member("Game/file.bin")).replace("\\\"romm-snapshot\\\"", "W/\\\"weak\\\""), ManifestValidationError::InvalidSnapshot),
        (manifest(&member("Game/file.bin")).replace("/api/download-manifests/", "https://evil.example/api/download-manifests/"), ManifestValidationError::InvalidDownloadUrl),
        (manifest(&member("Game/file.bin")).replace("\"members\": [", "\"unknown\": true, \"members\": ["), ManifestValidationError::InvalidManifest),
    ];

    for (input, expected) in cases {
        assert_eq!(ManifestValidator::validate(&input).unwrap_err(), expected);
    }
}

#[test]
fn rejects_duplicate_and_portably_colliding_destinations() {
    for destination_pair in [
        ("Game/file.bin", "Game/file.bin"),
        ("Game/File.bin", "game/file.bin"),
        ("Game/café.bin", "Game/café.bin"),
    ] {
        let first = member(destination_pair.0);
        let second = member(destination_pair.1).replace(MEMBER_ID, "33333333-3333-4333-8333-333333333333");
        let input = manifest(&format!("{first},{second}"));

        assert_eq!(
            ManifestValidator::validate(&input).unwrap_err(),
            ManifestValidationError::DestinationCollision
        );
    }
}
