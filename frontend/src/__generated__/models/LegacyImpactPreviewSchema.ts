/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LegacyImpactConfirmationSchema } from './LegacyImpactConfirmationSchema';
import type { LegacyImpactPlannedEffectsSchema } from './LegacyImpactPlannedEffectsSchema';
import type { LegacyImpactProblemSchema } from './LegacyImpactProblemSchema';
import type { LegacyImpactProposedMappingSchema } from './LegacyImpactProposedMappingSchema';
export type LegacyImpactPreviewSchema = {
    state: 'ready' | 'manual_mapping_required';
    proposed_mapping: (LegacyImpactProposedMappingSchema | null);
    reconnectable_catalog_count: number;
    unmatched_catalog_count: number;
    problems: Array<LegacyImpactProblemSchema>;
    planned_owned_effects: LegacyImpactPlannedEffectsSchema;
    confirmation: (LegacyImpactConfirmationSchema | null);
    source_immutable?: boolean;
    legacy_fallback_enabled?: boolean;
};

