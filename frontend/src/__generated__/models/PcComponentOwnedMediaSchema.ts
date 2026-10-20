/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PcComponentOwnedMediaPlacementSchema } from './PcComponentOwnedMediaPlacementSchema';
import type { RomComponentOwnedMediaOrigin } from './RomComponentOwnedMediaOrigin';
import type { RomComponentOwnedMediaRole } from './RomComponentOwnedMediaRole';
export type PcComponentOwnedMediaSchema = {
    id: number;
    role: RomComponentOwnedMediaRole;
    mime_type: string;
    owned_path: string;
    origin: RomComponentOwnedMediaOrigin;
    provider: (string | null);
    provider_media_id: (string | null);
    created_at: string;
    updated_at: string;
    placements?: Array<PcComponentOwnedMediaPlacementSchema>;
};

