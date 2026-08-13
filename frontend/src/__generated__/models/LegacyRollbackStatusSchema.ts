/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type LegacyRollbackStatusSchema = {
    migration_id: number;
    migration_version: number;
    platform_id: number;
    mapping_id: number;
    mapping_version: number;
    state: 'completed' | 'rolled_back';
    rollback_eligible: boolean;
    first_used: boolean;
    first_use_operation: ('scan' | 'hash' | 'stream' | 'play' | 'download' | null);
    expires_at: string;
    expired: boolean;
    source_immutable?: boolean;
    legacy_fallback_enabled?: boolean;
};

