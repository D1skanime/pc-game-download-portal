/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SetupFolderMappingSchema } from './SetupFolderMappingSchema';
import type { SetupRecoverySnapshot } from './SetupRecoverySnapshot';
import type { SetupRootHealthSchema } from './SetupRootHealthSchema';
export type SetupFolderAssignmentResponse = {
    mappings: Array<SetupFolderMappingSchema>;
    ready: boolean;
    root_health: SetupRootHealthSchema;
    recovery: SetupRecoverySnapshot;
};

