use std::{collections::HashMap, str::FromStr};

use romm_download_core::{ConfiguredOrigin, DestinationRootHandle, DestinationRootRegistry, ManifestId};
use serde::Serialize;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConflictAction {
    Overwrite,
    ChooseAnotherDestination,
    Skip,
}

impl ConflictAction {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Overwrite => "overwrite",
            Self::ChooseAnotherDestination => "choose_another_destination",
            Self::Skip => "skip",
        }
    }
}

#[derive(Debug)]
pub struct QueueRequest {
    pub origin: String,
    pub manifest_id: String,
    pub destination_root: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct RedactedJobSnapshot {
    pub job_id: String,
    pub state: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ShellSnapshot {
    pub jobs: Vec<RedactedJobSnapshot>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CommandBoundaryError {
    InvalidOrigin,
    InvalidManifestId,
    UnknownDestinationRoot,
    InvalidConflictAction,
}

/// Holds only core-issued root references and redacted shell state.
pub struct NativeShell {
    roots: DestinationRootRegistry,
    handles: HashMap<String, DestinationRootHandle>,
    jobs: HashMap<String, RedactedJobSnapshot>,
    configured_origin: Option<ConfiguredOrigin>,
    next_job_id: u64,
}

impl NativeShell {
    pub fn new() -> Self {
        Self {
            roots: DestinationRootRegistry::new(),
            handles: HashMap::new(),
            jobs: HashMap::new(),
            configured_origin: None,
            next_job_id: 1,
        }
    }

    pub fn configure_origin(&mut self, origin: &str) -> Result<(), CommandBoundaryError> {
        self.configured_origin = Some(
            ConfiguredOrigin::parse(origin).map_err(|_| CommandBoundaryError::InvalidOrigin)?,
        );
        Ok(())
    }

    /// The native chooser is the only caller permitted to provide a filesystem path.
    pub fn register_native_selection(
        &mut self,
        selected_path: impl AsRef<std::path::Path>,
    ) -> Result<String, CommandBoundaryError> {
        let handle = self
            .roots
            .register_native_selection(selected_path)
            .map_err(|_| CommandBoundaryError::UnknownDestinationRoot)?;
        let public_handle = format!("destination-{}", self.handles.len() + 1);
        self.handles.insert(public_handle.clone(), handle);
        Ok(public_handle)
    }

    pub fn queue(&mut self, request: QueueRequest) -> Result<String, CommandBoundaryError> {
        let origin = ConfiguredOrigin::parse(&request.origin)
            .map_err(|_| CommandBoundaryError::InvalidOrigin)?;
        if self.configured_origin.as_ref() != Some(&origin) {
            return Err(CommandBoundaryError::InvalidOrigin);
        }
        ManifestId::from_str(&request.manifest_id)
            .map_err(|_| CommandBoundaryError::InvalidManifestId)?;
        if !self.handles.contains_key(&request.destination_root) {
            return Err(CommandBoundaryError::UnknownDestinationRoot);
        }

        let job_id = format!("job-{}", self.next_job_id);
        self.next_job_id += 1;
        self.jobs.insert(
            job_id.clone(),
            RedactedJobSnapshot {
                job_id: job_id.clone(),
                state: "QUEUED".to_owned(),
            },
        );
        Ok(job_id)
    }

    pub fn select_conflict_action(
        &mut self,
        job_id: &str,
        action: &str,
    ) -> Result<(), CommandBoundaryError> {
        let state = match action {
            "overwrite" => ConflictAction::Overwrite.as_str(),
            "choose_another_destination" => ConflictAction::ChooseAnotherDestination.as_str(),
            "skip" => ConflictAction::Skip.as_str(),
            _ => return Err(CommandBoundaryError::InvalidConflictAction),
        };
        if let Some(job) = self.jobs.get_mut(job_id) {
            job.state = state.to_ascii_uppercase();
        }
        Ok(())
    }

    pub fn pause(&mut self, job_id: &str) {
        self.set_state(job_id, "PAUSED");
    }

    pub fn resume(&mut self, job_id: &str) {
        self.set_state(job_id, "QUEUED");
    }

    pub fn skip(&mut self, job_id: &str) {
        self.set_state(job_id, "SKIPPED");
    }

    pub fn state_snapshot(&self) -> ShellSnapshot {
        ShellSnapshot {
            jobs: self.jobs.values().cloned().collect(),
        }
    }

    #[cfg(test)]
    #[allow(dead_code)]
    pub const fn public_command_names() -> [&'static str; 8] {
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
    }

    fn set_state(&mut self, job_id: &str, state: &str) {
        if let Some(job) = self.jobs.get_mut(job_id) {
            job.state = state.to_owned();
        }
    }

    #[cfg(test)]
    #[allow(dead_code)]
    pub fn for_test() -> Self {
        let mut shell = Self::new();
        shell.configure_origin("https://romm.example").expect("origin");
        shell
    }

    #[cfg(test)]
    #[allow(dead_code)]
    pub fn register_test_root(&mut self) -> Result<String, CommandBoundaryError> {
        self.register_native_selection(std::env::temp_dir())
    }
}

impl Default for NativeShell {
    fn default() -> Self {
        Self::new()
    }
}
