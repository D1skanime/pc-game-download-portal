/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RomOwnedMediaOrigin } from './RomOwnedMediaOrigin';
import type { RomOwnedMediaPlacementSchema } from './RomOwnedMediaPlacementSchema';
import type { RomOwnedMediaRole } from './RomOwnedMediaRole';
import type { RomOwnedMediaState } from './RomOwnedMediaState';
export type RomOwnedMediaSchema = {
    id: number;
    origin: RomOwnedMediaOrigin;
    role: RomOwnedMediaRole;
    state: RomOwnedMediaState;
    display_label: string;
    mime_type: string;
    owned_path: (string | null);
    provider: (string | null);
    provider_media_id: (string | null);
    placements?: Array<RomOwnedMediaPlacementSchema>;
    created_at: string;
    updated_at: string;
};

