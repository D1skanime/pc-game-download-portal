/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ScanInventoryFacts = {
    rom_id: number;
    inventory_state: 'unchanged' | 'changed' | 'refresh_required' | 'incomplete';
    inventory_reason?: (string | null);
    identified_windows?: (boolean | null);
    existing_game: boolean;
    retry_eligible?: (boolean | null);
    retry_state?: 'not_scheduled' | 'cooldown' | 'due' | 'budget_deferred' | 'configuration_blocked' | 'baseline_required' | 'not_selected' | 'explicit' | 'initial';
    next_eligible_at?: (string | null);
    is_identifying?: boolean;
};

