/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PcMetadataMediaSchema } from './PcMetadataMediaSchema';
import type { SteamMetadataSchema } from './SteamMetadataSchema';
export type PcMetadataCandidateSchema = {
    id: string;
    provider: string;
    title: string;
    provider_ids: Record<string, (number | string)>;
    description_available: boolean;
    steam_metadata?: (SteamMetadataSchema | null);
    media: Array<PcMetadataMediaSchema>;
};

