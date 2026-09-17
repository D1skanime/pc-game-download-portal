use std::sync::{Arc, Mutex};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SchedulerError {
    InvalidLimit,
    AtCapacity,
}

/// Conservative whole-file transfer permit scheduler.
#[derive(Debug)]
pub struct TransferScheduler {
    limit: usize,
    active: Arc<Mutex<usize>>,
}

impl Default for TransferScheduler {
    fn default() -> Self {
        Self::new(2).expect("default scheduler limit is valid")
    }
}

impl TransferScheduler {
    pub fn new(limit: usize) -> Result<Self, SchedulerError> {
        if !(2..=4).contains(&limit) {
            return Err(SchedulerError::InvalidLimit);
        }
        Ok(Self {
            limit,
            active: Arc::new(Mutex::new(0)),
        })
    }

    pub fn limit(&self) -> usize {
        self.limit
    }

    pub fn active(&self) -> usize {
        *self.active.lock().expect("scheduler lock is not poisoned")
    }

    pub fn acquire(&self) -> Result<TransferPermit, SchedulerError> {
        let mut active = self.active.lock().expect("scheduler lock is not poisoned");
        if *active >= self.limit {
            return Err(SchedulerError::AtCapacity);
        }
        *active += 1;
        Ok(TransferPermit {
            active: Arc::clone(&self.active),
        })
    }
}

/// Releases capacity for every return path, including errors and cancellation.
#[derive(Debug)]
pub struct TransferPermit {
    active: Arc<Mutex<usize>>,
}

impl Drop for TransferPermit {
    fn drop(&mut self) {
        let mut active = self.active.lock().expect("scheduler lock is not poisoned");
        *active = active.saturating_sub(1);
    }
}
