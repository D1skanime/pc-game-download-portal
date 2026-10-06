export interface DataError {
  message: string;
  status?: number;
  cause?: unknown;
}

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: DataError | null;
}

export interface RequestContext {
  signal?: AbortSignal;
}

export interface Repository<TQuery, TResult> {
  query(input: TQuery, context?: RequestContext): Promise<TResult>;
}

export interface Mutation<TInput, TResult> {
  execute(input: TInput, context?: RequestContext): Promise<TResult>;
}

export interface PageQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  sort?: string;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface CatalogRepository<T> extends Repository<
  PageQuery,
  PageResult<T>
> {
  invalidate(): void;
}

export interface PermissionRepository {
  can(scope: string): boolean;
}

export interface AuthRepository<TUser = unknown> {
  currentUser(context?: RequestContext): Promise<TUser | null>;
}

export interface SettingsRepository<TSettings = unknown> {
  get(context?: RequestContext): Promise<TSettings>;
  update(value: TSettings, context?: RequestContext): Promise<TSettings>;
}

export interface DownloadRepository<
  TRequest = unknown,
  TResult = unknown,
> extends Mutation<TRequest, TResult> {
  cancel(id: string | number, context?: RequestContext): Promise<void>;
}

export interface MediaRepository<
  TRequest = unknown,
  TResult = unknown,
> extends Mutation<TRequest, TResult> {
  remove(id: string | number, context?: RequestContext): Promise<void>;
}

export interface ScanRepository<
  TRequest = unknown,
  TResult = unknown,
> extends Mutation<TRequest, TResult> {
  status(id: string | number, context?: RequestContext): Promise<TResult>;
}

export type LayoutKind = "classic-rom" | "pc" | "pc-nested";

export type ItemKind =
  "game" | "firmware" | "dlc" | "expansion" | "update" | "extra";

export type OperationKind =
  | "discovery"
  | "identification"
  | "metadata-refresh"
  | "media-sync"
  | "hash-repair"
  | "manual-match";

export type ScanType = "quick" | "full" | "new_platforms";

export type OperationScope =
  | { kind: "library" }
  | { kind: "platform"; platformIds: number[] }
  | { kind: "rom"; romIds: number[] }
  | {
      kind: "component";
      romId: number;
      componentId: number;
      componentKind: Exclude<ItemKind, "game" | "firmware">;
    }
  | { kind: "filesystem"; platformFsSlugs: string[] };

export interface LibraryProfile {
  rootId: string;
  mappingId: number;
  mappingRevision: number;
  layout: LayoutKind;
  itemKind: ItemKind;
  platformId?: number;
  platformFsSlug?: string;
}

export type OwnershipState = "manual" | "provider" | "legacy" | "unknown";

export interface ProviderPolicy {
  providers: string[];
  fallbackProviders: string[];
  allowUnexpectedLocale: boolean;
}

export type MetadataPolicyMode =
  "none" | "missing-only" | "provider-replace" | "complete-rescan";

export interface MetadataPolicy {
  mode: MetadataPolicyMode;
  fields: MetadataFieldTarget[];
}

export interface MetadataFieldTarget {
  field: string;
  locale: string;
  provider?: string;
  ownership?: OwnershipState;
}

export type MediaPolicyMode =
  "none" | "missing-only" | "provider-replace" | "complete-rescan";

export interface MediaPolicy {
  mode: MediaPolicyMode;
  targets: MediaTarget[];
}

export interface MediaTarget {
  role: string;
  locale?: string;
  region?: string;
  provider?: string;
  ownership?: OwnershipState;
}

export interface Provenance {
  provider: string;
  locale?: string;
  region?: string;
  ownership: OwnershipState;
  sourceId?: string;
}

export interface OperationCapabilities {
  discovery: boolean;
  creation: boolean;
  metadata: boolean;
  media: boolean;
  fileMutation: boolean;
  pcDlc: boolean;
  preview: boolean;
  retry: boolean;
  resume: boolean;
}

export interface PermissionContext {
  scopes: string[];
  actorId?: number;
}

export interface RetryInput {
  itemIds?: string[];
  maxAttempts: number;
  resumeFrom?: string;
}

export interface ExecutionPolicy {
  maxConcurrency: number;
  cancelable: boolean;
  resumable: boolean;
}

export interface OperationRequest {
  operationId: string;
  kind: OperationKind;
  scope: OperationScope;
  profiles: LibraryProfile[];
  uiLocale: string;
  metadataLocale: string;
  providerPolicy: ProviderPolicy;
  metadataPolicy: MetadataPolicy;
  mediaPolicy: MediaPolicy;
  capabilities: OperationCapabilities;
  preview: boolean;
  permissions: PermissionContext;
  idempotencyKey: string;
  jobId: string;
  retry?: RetryInput;
  execution: ExecutionPolicy;
  scanType?: ScanType;
  provenance?: Provenance;
}

export type OperationStatus =
  "queued" | "running" | "completed" | "cancelled" | "failed";

export type OperationItemOutcome =
  | "changed"
  | "unchanged"
  | "protected"
  | "not-found"
  | "skipped"
  | "failed"
  | "retryable";

export interface OperationItemResult {
  itemId: string;
  outcome: OperationItemOutcome;
  operationId: string;
  jobId: string;
  message?: string;
  provenance?: Provenance;
}

export interface OperationResult {
  operationId: string;
  jobId: string;
  status: OperationStatus;
  items: OperationItemResult[];
  preview: boolean;
}
