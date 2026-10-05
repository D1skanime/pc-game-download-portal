import type {
  AuthRepository,
  CatalogRepository,
  DataError,
  DownloadRepository,
  MediaRepository,
  PageQuery,
  PageResult,
  PermissionRepository,
  Repository,
  RequestContext,
  ScanRepository,
  SettingsRepository,
} from "../contracts";
import { throwIfAborted, toDataError } from "../errors";

export interface LegacyQuery<TInput, TResult> {
  (input: TInput, context?: RequestContext): Promise<TResult>;
}

export function createRepository<TInput, TResult>(
  query: LegacyQuery<TInput, TResult>,
): Repository<TInput, TResult> {
  return {
    async query(input, context) {
      throwIfAborted(context?.signal);
      try {
        return await query(input, context);
      } catch (error) {
        throw toDataError(error);
      }
    },
  };
}

export function createCatalogRepository<T>(
  query: LegacyQuery<PageQuery, PageResult<T>>,
  invalidate: () => void = () => undefined,
): CatalogRepository<T> {
  const repository = createRepository(query);
  return {
    query: repository.query,
    invalidate,
  };
}

export function createAuthRepository<TUser>(
  query: LegacyQuery<void, TUser | null>,
): AuthRepository<TUser> {
  return {
    currentUser: (context) => createRepository(query).query(undefined, context),
  };
}

export function createSettingsRepository<TSettings>(
  get: LegacyQuery<void, TSettings>,
  update: LegacyQuery<TSettings, TSettings>,
): SettingsRepository<TSettings> {
  const getter = createRepository(get);
  const updater = createRepository(update);
  return {
    get: (context) => getter.query(undefined, context),
    update: (value, context) => updater.query(value, context),
  };
}

export function createPermissionRepository(
  read: (scope: string) => boolean,
): PermissionRepository {
  return { can: read };
}

export function createMutationRepository<TInput, TResult>(
  execute: LegacyQuery<TInput, TResult>,
  cancel: (id: string | number, context?: RequestContext) => Promise<void>,
): DownloadRepository<TInput, TResult> &
  MediaRepository<TInput, TResult> &
  ScanRepository<TInput, TResult> {
  const mutation = createRepository(execute);
  return {
    execute: mutation.query,
    cancel: async (id, context) => {
      throwIfAborted(context?.signal);
      await cancel(id, context);
    },
    remove: async (id, context) => {
      throwIfAborted(context?.signal);
      await cancel(id, context);
    },
    status: async (id, context) => {
      throwIfAborted(context?.signal);
      return (await cancel(id, context)) as TResult;
    },
  };
}

export function isDataError(error: unknown): error is DataError {
  return Boolean(error && typeof error === "object" && "message" in error);
}
