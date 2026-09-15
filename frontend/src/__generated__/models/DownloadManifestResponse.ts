/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DownloadManifestComponentSchema } from './DownloadManifestComponentSchema';
import type { DownloadManifestMemberSchema } from './DownloadManifestMemberSchema';
export type DownloadManifestResponse = {
    schema_version?: number;
    id: string;
    created_at: string;
    expires_at: string;
    components: Array<DownloadManifestComponentSchema>;
    members: Array<DownloadManifestMemberSchema>;
};

