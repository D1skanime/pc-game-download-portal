/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CatalogRemovalErrorSchema } from './CatalogRemovalErrorSchema';
import type { CatalogRemovalItemSchema } from './CatalogRemovalItemSchema';
export type CatalogRemovalResponse = {
    successful_items: number;
    failed_ids: Array<number>;
    errors: Array<CatalogRemovalErrorSchema>;
    items: Array<CatalogRemovalItemSchema>;
    source_files_preserved?: boolean;
    retained_user_data?: boolean;
};

