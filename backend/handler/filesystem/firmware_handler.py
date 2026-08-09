import binascii
import hashlib

from config.config_manager import config_manager as cm
from exceptions.fs_exceptions import FirmwareNotFoundException
from exceptions.storage_exceptions import (
    MissingStorageTargetError,
    StorageResolutionError,
)
from utils.hashing import crc32_to_hex

from .base_handler import ExternalFSHandler
from .storage_policy import ExternalStorageDescriptor, StorageOperation


class FSFirmwareHandler(ExternalFSHandler):
    def __init__(self, storage: ExternalStorageDescriptor | None = None) -> None:
        if storage is None:
            from handler.filesystem import legacy_external_storage

            storage = legacy_external_storage
        super().__init__(base_path=storage._root_path, storage=storage)

    def get_firmware_fs_structure(self, fs_slug: str) -> str:
        cnfg = cm.get_config()
        return (
            f"{fs_slug}/{cnfg.FIRMWARE_FOLDER_NAME}"
            if cnfg.has_structure_path_b
            else f"{cnfg.FIRMWARE_FOLDER_NAME}/{fs_slug}"
        )

    async def get_firmware(self, platform_fs_slug: str):
        """Gets all filesystem firmware for a platform

        Args:
            platform: platform where firmware belong
        Returns:
            list with all the filesystem firmware for a platform
        """
        firmware_path = self.get_firmware_fs_structure(platform_fs_slug)
        try:
            fs_firmware_files = await self.list_files(path=firmware_path)
        except (FileNotFoundError, StorageResolutionError) as e:
            raise FirmwareNotFoundException(
                f"Firmware not found for platform {platform_fs_slug}"
            ) from e

        return [f for f in self.exclude_single_files(fs_firmware_files)]

    async def calculate_file_hashes(self, firmware_path: str, file_name: str) -> dict:
        file_path = f"{firmware_path}/{file_name}"
        try:
            with self.open_access(StorageOperation.READ, file_path) as reader:
                content = reader.read()
        except MissingStorageTargetError as error:
            raise FileNotFoundError(file_path) from error
        return {
            "crc_hash": crc32_to_hex(binascii.crc32(content)),
            "md5_hash": hashlib.md5(content, usedforsecurity=False).hexdigest(),
            "sha1_hash": hashlib.sha1(content, usedforsecurity=False).hexdigest(),
        }
