mod commands;

use std::sync::Mutex;

use commands::{NativeShell, QueueRequest, ShellSnapshot};
use tauri::State;
use tauri_plugin_dialog::DialogExt;

struct ShellState(Mutex<NativeShell>);

#[tauri::command]
fn configure_origin(state: State<'_, ShellState>, origin: String) -> Result<(), String> {
    state
        .0
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
        .0
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
        .0
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
    state.0.lock().map_err(|_| "command_unavailable".to_owned())?.pause(&job_id);
    Ok(())
}

#[tauri::command]
fn resume(state: State<'_, ShellState>, job_id: String) -> Result<(), String> {
    state.0.lock().map_err(|_| "command_unavailable".to_owned())?.resume(&job_id);
    Ok(())
}

#[tauri::command]
fn skip(state: State<'_, ShellState>, job_id: String) -> Result<(), String> {
    state.0.lock().map_err(|_| "command_unavailable".to_owned())?.skip(&job_id);
    Ok(())
}

#[tauri::command]
fn select_conflict_action(
    state: State<'_, ShellState>,
    job_id: String,
    action: String,
) -> Result<(), String> {
    state
        .0
        .lock()
        .map_err(|_| "command_unavailable".to_owned())?
        .select_conflict_action(&job_id, &action)
        .map_err(|_| "invalid_conflict_action".to_owned())
}

#[tauri::command]
fn state_snapshot(state: State<'_, ShellState>) -> Result<ShellSnapshot, String> {
    Ok(state
        .0
        .lock()
        .map_err(|_| "command_unavailable".to_owned())?
        .state_snapshot())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(ShellState(Mutex::new(NativeShell::new())))
        .invoke_handler(tauri::generate_handler![
            configure_origin,
            choose_destination,
            queue_manifest,
            pause,
            resume,
            skip,
            select_conflict_action,
            state_snapshot
        ])
        .run(tauri::generate_context!())
        .expect("failed to run RomM Desktop");
}
