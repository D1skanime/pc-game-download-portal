/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StorageConflictErrorCode } from './StorageConflictErrorCode';
export type StorageConflictDetail = {
    code: StorageConflictErrorCode;
    message: string;
    platform_id?: (number | null);
    mapping_id?: (number | null);
    current_version?: (number | null);
};
