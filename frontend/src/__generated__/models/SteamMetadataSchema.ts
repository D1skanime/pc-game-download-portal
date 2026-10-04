/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SteamTextVariantSchema } from './SteamTextVariantSchema';
export type SteamMetadataSchema = {
    app_id?: (number | null);
    source?: (string | null);
    developers?: (Array<string> | null);
    publishers?: (Array<string> | null);
    platforms?: (Record<string, boolean> | null);
    release_date?: (Record<string, (string | boolean)> | null);
    language?: (string | null);
    fallback_language?: (string | null);
    fallback_fields?: (Array<string> | null);
    fields?: (Array<string> | null);
    type?: (string | null);
    fullgame?: (Record<string, (number | string)> | null);
    genres?: (Array<string> | null);
    categories?: (Array<string> | null);
    dlc_ids?: (Array<number> | null);
    text_variants?: (Record<string, SteamTextVariantSchema> | null);
};
