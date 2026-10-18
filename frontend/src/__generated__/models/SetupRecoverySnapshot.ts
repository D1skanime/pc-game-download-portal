/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SetupFolderMappingSchema } from './SetupFolderMappingSchema';
import type { SetupFolderSchema } from './SetupFolderSchema';
import type { SetupRootHealthSchema } from './SetupRootHealthSchema';
export type SetupRecoverySnapshot = {
    enrolled: boolean;
    setup_complete: boolean;
    current_step: 'account' | 'folders' | 'complete';
    saved_assignments: Array<SetupFolderMappingSchema>;
    missing_assignments: Array<SetupFolderSchema>;
    root_health: SetupRootHealthSchema;
    cause_code: ('root_missing' | 'root_unreadable' | 'root_not_read_only' | 'root_inactive' | 'root_discovery_failed' | 'assignments_missing' | 'mapping_conflict' | null);
    next_action: 'create_admin' | 'retry_check' | 'assign_missing' | 'resolve_conflicts' | 'start_first_scan';
};

