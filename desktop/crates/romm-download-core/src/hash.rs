use std::{fs, io::Read, path::Path};

use sha2::{Digest, Sha256};

use crate::FinalizationError;

pub(crate) fn verify_sha256(
    path: &Path,
    expected_size: u64,
    expected_sha256: &str,
) -> Result<(), FinalizationError> {
    let metadata = fs::metadata(path).map_err(FinalizationError::from_io)?;
    if metadata.len() != expected_size {
        return Err(FinalizationError::ChecksumFailed);
    }

    let mut file = fs::File::open(path).map_err(FinalizationError::from_io)?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer).map_err(FinalizationError::from_io)?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    if format!("{:x}", digest.finalize()) == expected_sha256 {
        Ok(())
    } else {
        Err(FinalizationError::ChecksumFailed)
    }
}
