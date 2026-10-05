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
