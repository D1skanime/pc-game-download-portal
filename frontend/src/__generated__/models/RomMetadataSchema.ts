/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MetadataCompanyRoleSchema } from './MetadataCompanyRoleSchema';
import type { MetadataFacetOptionSchema } from './MetadataFacetOptionSchema';
export type RomMetadataSchema = {
    rom_id: number;
    genres: Array<string>;
    franchises: Array<string>;
    collections: Array<string>;
    companies: Array<string>;
    main_developer: (string | null);
    publishers?: Array<string>;
    themes?: Array<string>;
    genre_ids?: Array<string>;
    theme_ids?: Array<string>;
    genre_options?: Array<MetadataFacetOptionSchema>;
    theme_options?: Array<MetadataFacetOptionSchema>;
    company_roles?: Array<MetadataCompanyRoleSchema>;
    game_modes: Array<string>;
    age_ratings: Array<string>;
    player_count: string;
    first_release_date: (number | null);
    pc_release_date: (number | null);
    average_rating: (number | null);
};

