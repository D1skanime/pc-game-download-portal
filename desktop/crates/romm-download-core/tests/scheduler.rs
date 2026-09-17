use romm_download_core::{SchedulerError, TransferScheduler};

#[test]
fn bounds_whole_file_streams_and_releases_each_outcome() {
    let scheduler = TransferScheduler::new(2).unwrap();
    let first = scheduler.acquire().unwrap();
    let second = scheduler.acquire().unwrap();
    assert_eq!(scheduler.acquire().unwrap_err(), SchedulerError::AtCapacity);
    drop(first);
    let replacement = scheduler.acquire().unwrap();
    drop(second);
    drop(replacement);
    assert_eq!(scheduler.active(), 0);
}

#[test]
fn accepts_only_the_conservative_configured_limit_range() {
    assert_eq!(
        TransferScheduler::new(1).unwrap_err(),
        SchedulerError::InvalidLimit
    );
    assert_eq!(
        TransferScheduler::new(5).unwrap_err(),
        SchedulerError::InvalidLimit
    );
    assert_eq!(TransferScheduler::default().limit(), 2);
    assert_eq!(TransferScheduler::new(4).unwrap().limit(), 4);
}
