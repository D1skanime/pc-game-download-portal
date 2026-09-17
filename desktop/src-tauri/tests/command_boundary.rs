#[path = "../src/commands.rs"]
mod commands;

use commands::{ConflictAction, NativeShell, QueueRequest};

#[test]
fn webview_cannot_supply_a_destination_path_or_forge_a_handle() {
    let mut shell = NativeShell::for_test();

    assert!(shell
        .queue(QueueRequest {
            origin: "https://romm.example".to_owned(),
            manifest_id: "00000000-0000-0000-0000-000000000001".to_owned(),
            destination_root: "C:\\users\\attacker".to_owned(),
        })
        .is_err());
    assert!(shell
        .queue(QueueRequest {
            origin: "https://romm.example".to_owned(),
            manifest_id: "00000000-0000-0000-0000-000000000001".to_owned(),
            destination_root: "forged-root-handle".to_owned(),
        })
        .is_err());
}

#[test]
fn webview_cannot_submit_manifest_json_or_cross_origin_urls() {
    let mut shell = NativeShell::for_test();
    let root = shell.register_test_root().expect("test root");

    assert!(shell
        .queue(QueueRequest {
            origin: "https://attacker.example/path".to_owned(),
            manifest_id: "{\"members\":[]}".to_owned(),
            destination_root: root,
        })
        .is_err());
}

#[test]
fn webview_has_no_raw_token_shell_or_filesystem_command_surface() {
    let command_names = NativeShell::public_command_names();

    assert_eq!(
        command_names,
        [
            "configure_origin",
            "choose_destination",
            "queue_manifest",
            "pause",
            "resume",
            "skip",
            "select_conflict_action",
            "state_snapshot",
        ]
    );
    assert!(!command_names.iter().any(|name| {
        name.contains("token")
            || name.contains("shell")
            || name.contains("filesystem")
            || name.contains("path")
    }));
}

#[test]
fn conflict_choices_are_closed_and_state_is_redacted() {
    assert_eq!(ConflictAction::Skip.as_str(), "skip");
    assert_eq!(ConflictAction::Overwrite.as_str(), "overwrite");
    assert_eq!(ConflictAction::ChooseAnotherDestination.as_str(), "choose_another_destination");
}
