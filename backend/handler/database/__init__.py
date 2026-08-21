from .client_tokens_handler import DBClientTokensHandler
from .collections_handler import DBCollectionsHandler
from .device_save_sync_handler import DBDeviceSaveSyncHandler
from .devices_handler import DBDevicesHandler
from .firmware_handler import DBFirmwareHandler
from .legacy_migration_handler import DBLegacyMigrationHandler
from .manual_handler import DBPrimaryManualHandler
from .mapping_previews_handler import DBMappingPreviewsHandler
from .music_playlists_handler import DBMusicPlaylistsHandler
from .permissions_handler import DBPermissionsHandler
from .platforms_handler import DBPlatformsHandler
from .play_sessions_handler import DBPlaySessionsHandler
from .roms_handler import DBRomsHandler
from .saves_handler import DBSavesHandler
from .screenshots_handler import DBScreenshotsHandler
from .states_handler import DBStatesHandler
from .stats_handler import DBStatsHandler
from .storage_handler import DBStorageHandler
from .sync_sessions_handler import DBSyncSessionsHandler
from .users_handler import DBUsersHandler

db_client_token_handler = DBClientTokensHandler()
db_collection_handler = DBCollectionsHandler()
db_device_handler = DBDevicesHandler()
db_device_save_sync_handler = DBDeviceSaveSyncHandler()
db_firmware_handler = DBFirmwareHandler()
db_legacy_migration_handler = DBLegacyMigrationHandler()
db_mapping_previews_handler = DBMappingPreviewsHandler()
db_primary_manual_handler = DBPrimaryManualHandler()
db_music_playlist_handler = DBMusicPlaylistsHandler()
db_permission_handler = DBPermissionsHandler()
db_platform_handler = DBPlatformsHandler()
db_play_session_handler = DBPlaySessionsHandler()
db_rom_handler = DBRomsHandler()
db_save_handler = DBSavesHandler()
db_screenshot_handler = DBScreenshotsHandler()
db_state_handler = DBStatesHandler()
db_stats_handler = DBStatsHandler()
db_storage_handler = DBStorageHandler()
db_sync_session_handler = DBSyncSessionsHandler()
db_user_handler = DBUsersHandler()
