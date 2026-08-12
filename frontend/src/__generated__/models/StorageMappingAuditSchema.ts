/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StorageMappingAuditAction } from './StorageMappingAuditAction';
import type { StorageMappingSnapshotSchema } from './StorageMappingSnapshotSchema';
export type StorageMappingAuditSchema = {
    id: number;
    actor_user_id: number;
    actor_display_name: string;
    platform_id: number;
    mapping_id: number;
    action: StorageMappingAuditAction;
    old: (StorageMappingSnapshotSchema | null);
    new: (StorageMappingSnapshotSchema | null);
    created_at: string;
};

