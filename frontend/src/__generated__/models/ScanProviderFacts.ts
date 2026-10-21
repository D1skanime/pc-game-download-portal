/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ScanProviderFacts = {
    state: 'no_request' | 'cached' | 'matched' | 'no_match' | 'failed' | 'requested';
    invoked: boolean;
    requests: number;
    cached?: (boolean | null);
    is_identifying?: boolean;
};

