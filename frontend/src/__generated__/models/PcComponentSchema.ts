/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PcComponentManifestMemberSchema } from './PcComponentManifestMemberSchema';
import type { RomComponentKind } from './RomComponentKind';
export type PcComponentSchema = {
    relative_path: string;
    kind: RomComponentKind;
    manifest_members: Array<PcComponentManifestMemberSchema>;
};

