/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PcAutomationBatchItemRequest } from './PcAutomationBatchItemRequest';
import type { PcAutomationTargetKind } from './PcAutomationTargetKind';
export type PcAutomationBatchRequest = {
    target_kind: PcAutomationTargetKind;
    candidate_fingerprint: string;
    items: Array<PcAutomationBatchItemRequest>;
};
