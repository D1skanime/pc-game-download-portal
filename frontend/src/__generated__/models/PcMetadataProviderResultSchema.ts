/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PcMetadataCandidateSchema } from './PcMetadataCandidateSchema';
export type PcMetadataProviderResultSchema = {
    provider: string;
    available: boolean;
    candidates: Array<PcMetadataCandidateSchema>;
    reason?: (string | null);
};

