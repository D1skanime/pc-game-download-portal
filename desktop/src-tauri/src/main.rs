mod auth;
mod commands;

use std::{
    sync::Mutex,
    time::{SystemTime, UNIX_EPOCH},
};

use auth::{
    AuthSnapshot, DeviceAuthClient, KeyringTokenStore, PairingInfo, ReqwestDeviceAuthTransport,
};
use commands::{NativeShell, QueueRequest, ShellSnapshot};
use tauri::State;
use tauri_plugin_dialog::DialogExt;

type NativeDeviceAuth = DeviceAuthClient<ReqwestDeviceAuthTransport, KeyringTokenStore>;

struct ShellState {
    shell: Mutex<NativeShell>,
    auth: Mutex<Option<NativeDeviceAuth>>,
}

#[tauri::command]
fn configure_origin(state: State<'_, ShellState>, origin: String) -> Result<(), String> {
    state
        .shell
        .lock()
        .map_err(|_| "command_unavailable".to_owned())?
        .configure_origin(&origin)
        .map_err(|_| "invalid_origin".to_owned())
}

#[tauri::command]
fn choose_destination(
    app: tauri::AppHandle,
    state: State<'_, ShellState>,
) -> Result<Option<String>, String> {
    let Some(selected) = app.dialog().file().blocking_pick_folder() else {
        return Ok(None);
    };
    let selected_path = selected.as_path().ok_or_else(|| "invalid_destination".to_owned())?;
    state
        .shell
        .lock()
        .map_err(|_| "command_unavailable".to_owned())?
        .register_native_selection(selected_path)
        .map(Some)
        .map_err(|_| "invalid_destination".to_owned())
}

#[tauri::command]
fn queue_manifest(
    state: State<'_, ShellState>,
    origin: String,
    manifest_id: String,
    destination_root: String,
) -> Result<String, String> {
    state
        .shell
        .lock()
        .map_err(|_| "command_unavailable".to_owned())?
        .queue(QueueRequest {
            origin,
            manifest_id,
            destination_root,
        })
        .map_err(|_| "invalid_queue_request".to_owned())
}

#[tauri::command]
fn pause(state: State<'_, ShellState>, job_id: String) -> Result<(), String> {
    state.shell.lock().map_err(|_| "command_unavailable".to_owned())?.pause(&job_id);
    Ok(())
}

#[tauri::command]
fn resume(state: State<'_, ShellState>, job_id: String) -> Result<(), String> {
    state.shell.lock().map_err(|_| "command_unavailable".to_owned())?.resume(&job_id);
    Ok(())
}

#[tauri::command]
fn skip(state: State<'_, ShellState>, job_id: String) -> Result<(), String> {
    state.shell.lock().map_err(|_| "command_unavailable".to_owned())?.skip(&job_id);
    Ok(())
}

#[tauri::command]
fn select_conflict_action(
    state: State<'_, ShellState>,
    job_id: String,
    action: String,
) -> Result<(), String> {
    state
        .shell
        .lock()
        .map_err(|_| "command_unavailable".to_owned())?
        .select_conflict_action(&job_id, &action)
        .map_err(|_| "invalid_conflict_action".to_owned())
}

#[tauri::command]
fn state_snapshot(state: State<'_, ShellState>) -> Result<ShellSnapshot, String> {
    Ok(state
        .shell
        .lock()
        .map_err(|_| "command_unavailable".to_owned())?
        .state_snapshot())
}

#[tauri::command]
fn start_device_pairing(
    state: State<'_, ShellState>,
    origin: String,
    client_device_identifier: String,
    name: String,
    platform: String,
    client_version: String,
) -> Result<PairingInfo, String> {
    if !state
        .shell
        .lock()
        .map_err(|_| "command_unavailable".to_owned())?
        .is_configured_origin(&origin)
    {
        return Err("invalid_origin".to_owned());
    }
    let transport = ReqwestDeviceAuthTransport::new().map_err(|_| "auth_unavailable".to_owned())?;
    let store = KeyringTokenStore::new().map_err(|_| "auth_unavailable".to_owned())?;
    let mut client = DeviceAuthClient::new(&origin, transport, store)
        .map_err(|_| "invalid_origin".to_owned())?;
    let pairing = client
        .start(
            &client_device_identifier,
            &name,
            &platform,
            &client_version,
            now_epoch()?,
        )
        .map_err(|_| "auth_required".to_owned())?;
    *state.auth.lock().map_err(|_| "command_unavailable".to_owned())? = Some(client);
    Ok(pairing)
}

#[tauri::command]
fn poll_device_pairing(state: State<'_, ShellState>) -> Result<AuthSnapshot, String> {
    let mut auth = state.auth.lock().map_err(|_| "command_unavailable".to_owned())?;
    let client = auth.as_mut().ok_or_else(|| "auth_required".to_owned())?;
    client.poll(now_epoch()?).map_err(|_| "auth_required".to_owned())?;
    Ok(client.snapshot())
}

fn now_epoch() -> Result<u64, String> {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .map_err(|_| "auth_unavailable".to_owned())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(ShellState {
            shell: Mutex::new(NativeShell::new()),
            auth: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            configure_origin,
            choose_destination,
            queue_manifest,
            pause,
            resume,
            skip,
            select_conflict_action,
            state_snapshot,
            start_device_pairing,
            poll_device_pairing
        ])
        .run(tauri::generate_context!())
        .expect("failed to run RomM Desktop");
}
