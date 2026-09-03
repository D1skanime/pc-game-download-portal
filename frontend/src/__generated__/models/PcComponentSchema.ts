/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PcComponentLocalMediaSchema } from './PcComponentLocalMediaSchema';
import type { PcComponentManifestMemberSchema } from './PcComponentManifestMemberSchema';
import type { PcComponentMetadataSchema } from './PcComponentMetadataSchema';
import type { PcComponentOwnedMediaSchema } from './PcComponentOwnedMediaSchema';
import type { RomComponentKind } from './RomComponentKind';
export type PcComponentSchema = {
    id: number;
    relative_path: string;
    kind: RomComponentKind;
    manifest_members: Array<PcComponentManifestMemberSchema>;
    component_metadata?: (PcComponentMetadataSchema | null);
    local_media?: Array<PcComponentLocalMediaSchema>;
    owned_media?: Array<PcComponentOwnedMediaSchema>;
};

