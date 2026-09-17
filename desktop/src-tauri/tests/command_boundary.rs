#[path = "../src/commands.rs"]
mod commands;
#[path = "../src/auth.rs"]
mod auth;

use auth::{AuthState, DeviceAuthClient, DeviceAuthHttpResponse, DeviceAuthTransport, TokenStore};
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
            "start_device_pairing",
            "poll_device_pairing",
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

    let mut shell = NativeShell::for_test();
    let root = shell.register_test_root().expect("test root");
    let job_id = shell
        .queue(QueueRequest {
            origin: "https://romm.example".to_owned(),
            manifest_id: "00000000-0000-0000-0000-000000000001".to_owned(),
            destination_root: root,
        })
        .expect("opaque queue request");
    shell.pause(&job_id);
    shell.resume(&job_id);
    shell
        .select_conflict_action(&job_id, "skip")
        .expect("closed conflict action");
    shell.skip(&job_id);

    let snapshot = shell.state_snapshot();
    assert_eq!(snapshot.jobs.len(), 1);
    assert_eq!(snapshot.jobs[0].state, "SKIPPED");
    assert!(!format!("{snapshot:?}").contains("romm.example"));
}

#[derive(Default)]
struct MockTransport {
    responses: Vec<DeviceAuthHttpResponse>,
    requests: Vec<(String, String)>,
}

impl DeviceAuthTransport for MockTransport {
    fn send(
        &mut self,
        method: &str,
        url: &str,
        _body: &str,
    ) -> Result<DeviceAuthHttpResponse, ()> {
        self.requests.push((method.to_owned(), url.to_owned()));
        Ok(self.responses.remove(0))
    }
}

#[derive(Default)]
struct MemoryTokenStore(Option<String>);

impl TokenStore for MemoryTokenStore {
    fn save(&mut self, token: &str) -> Result<(), ()> {
        self.0 = Some(token.to_owned());
        Ok(())
    }

    fn load(&self) -> Result<Option<String>, ()> {
        Ok(self.0.clone())
    }

    fn clear(&mut self) -> Result<(), ()> {
        self.0 = None;
        Ok(())
    }
}

#[test]
fn device_pairing_uses_only_roms_read_and_keeps_the_token_out_of_snapshots() {
    let transport = MockTransport {
        responses: vec![
            DeviceAuthHttpResponse::json(
                201,
                r#"{"device_code":"private-device-code","user_code":"ABCD-EFGH","verification_path":"/pair/device","verification_path_complete":"/pair/device?user_code=ABCD-EFGH","expires_in":300,"interval":5}"#,
            ),
            DeviceAuthHttpResponse::json(
                200,
                r#"{"access_token":"rmm_secret","device_id":"1","scopes":["roms.read"],"expires_at":null}"#,
            ),
        ],
        ..Default::default()
    };
    let mut client = DeviceAuthClient::new("https://romm.example", transport, MemoryTokenStore::default())
        .expect("configured origin");

    let pairing = client.start("native-id", "RomM Desktop", "linux", "0.1.0", 100).expect("init");
    assert_eq!(pairing.user_code, "ABCD-EFGH");
    assert_eq!(pairing.verification_url, "https://romm.example/pair/device");
    assert_eq!(client.snapshot().state, AuthState::Pairing);
    assert!(!format!("{:?}", client.snapshot()).contains("rmm_secret"));

    assert_eq!(client.poll(105).expect("token"), AuthState::Paired);
    assert!(client.token_is_stored().expect("stored token"));
}

#[test]
fn expired_or_unauthorized_pairing_requires_repair_without_retaining_a_token() {
    let transport = MockTransport {
        responses: vec![DeviceAuthHttpResponse::json(
            201,
            r#"{"device_code":"private-device-code","user_code":"ABCD-EFGH","verification_path":"/pair/device","verification_path_complete":"/pair/device?user_code=ABCD-EFGH","expires_in":5,"interval":5}"#,
        )],
        ..Default::default()
    };
    let mut client = DeviceAuthClient::new(
        "https://romm.example",
        transport,
        MemoryTokenStore(Some("rmm_previous".to_owned())),
    )
        .expect("configured origin");

    client.start("native-id", "RomM Desktop", "windows", "0.1.0", 100).expect("init");
    assert_eq!(client.poll(106).expect("expired"), AuthState::AuthRequired);
    assert!(!client.token_is_stored().expect("cleared token"));
}
