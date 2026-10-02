/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PcAutomationQueueState } from './PcAutomationQueueState';
import type { PcAutomationTargetKind } from './PcAutomationTargetKind';
export type PcAutomationQueueItemSchema = {
    id: number;
    rom_id: number;
    component_id: (number | null);
    target_kind: PcAutomationTargetKind;
    candidate_fingerprint: string;
    candidate_title: (string | null);
    candidate_cover_url: (string | null);
    provider: (string | null);
    reason: (string | null);
    state: PcAutomationQueueState;
    expected_queue_version: string;
    expected_target_version: string;
};
