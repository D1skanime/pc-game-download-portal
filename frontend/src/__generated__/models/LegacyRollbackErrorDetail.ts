/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LegacyRollbackErrorCode } from './LegacyRollbackErrorCode';
export type LegacyRollbackErrorDetail = {
    code: LegacyRollbackErrorCode;
    message: string;
    migration_id?: (number | null);
    platform_id?: (number | null);
    current_version?: (number | null);
};

