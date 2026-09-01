/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PcMetadataMediaSchema } from './PcMetadataMediaSchema';
export type PcMetadataCandidateSchema = {
    id: string;
    provider: string;
    title: string;
    provider_ids: Record<string, (number | string)>;
    description_available: boolean;
    media: Array<PcMetadataMediaSchema>;
};

