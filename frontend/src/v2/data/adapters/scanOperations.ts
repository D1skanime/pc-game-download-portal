import axios, { type AxiosResponse } from "axios";
import { effectScope, watch } from "vue";
import api from "@/services/api";
import useAuthStore from "@/stores/auth";
import type {
  OperationRequest,
  ScanOperationMutationRequest,
  ScanOperationRequest,
  ScanOperationSnapshot,
} from "../contracts";
import {
  OperationTranslationError,
  toScanOperationRequest,
} from "../operations";

const options = { timeout: 5000 };
const storagePrefix = "pgdp.scan-operation.";
type Session = { actor: number; generation: number };
type Identity = { request_key: string; operation_id?: string };
let currentActor: number | undefined;
let generation = 0;
let identity: Identity | undefined;
let owner: ReturnType<typeof useAuthStore> | undefined;
let stopWatching: (() => void) | undefined;
let installed = false;
let flight:
  | {
      actor: number;
      signature: string;
      promise: Promise<ScanOperationSnapshot>;
    }
  | undefined;

function storage(): Storage | undefined {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
}

function clear() {
  if (currentActor !== undefined) {
    try {
      storage()?.removeItem(storagePrefix + currentActor);
    } catch {
      /* Storage may be disabled. */
    }
  }
  identity = undefined;
  flight = undefined;
  generation += 1;
}

function session(): Session {
  const auth = useAuthStore();
  if (owner !== auth) {
    stopWatching?.();
    clear();
    owner = auth;
    currentActor = auth.user?.id;
    const scope = effectScope(true);
    scope.run(() =>
      watch(
        () => auth.user?.id,
        (actor) => {
          clear();
          currentActor = actor;
        },
        { flush: "sync" },
      ),
    );
    stopWatching = () => scope.stop();
  }
  if (!installed) {
    installed = true;
    api.interceptors.response.use(
      (response) => {
        if (response.config.url === "/logout") clear();
        return response;
      },
      (error: unknown) => {
        if (axios.isAxiosError(error) && error.response?.status === 401)
          clear();
        return Promise.reject(error);
      },
    );
  }
  if (
    !Number.isSafeInteger(currentActor) ||
    !currentActor ||
    currentActor < 1
  ) {
    throw new OperationTranslationError("scan_authentication_required");
  }
  return { actor: currentActor, generation };
}

function assertSession(context: Session) {
  if (context.actor !== currentActor || context.generation !== generation) {
    throw new OperationTranslationError("scan_session_changed");
  }
}

function requestKey(key: string): string {
  if (typeof key !== "string" || !/^[a-z0-9][a-z0-9_-]{0,95}$/.test(key)) {
    throw new OperationTranslationError("invalid_scan_request_key");
  }
  return key;
}

function readIdentity(context: Session): Identity | undefined {
  assertSession(context);
  if (identity) return identity;
  try {
    const raw = storage()?.getItem(storagePrefix + context.actor);
    if (!raw) return undefined;
    if (raw.length > 512) throw new Error("invalid_scan_identity");
    const parsed = JSON.parse(raw);
    requestKey(parsed.request_key);
    if (
      parsed.operation_id !== undefined &&
      (typeof parsed.operation_id !== "string" ||
        !/^[a-z0-9-]{1,128}$/.test(parsed.operation_id))
    ) {
      throw new Error("invalid_scan_identity");
    }
    identity = {
      request_key: parsed.request_key,
      operation_id: parsed.operation_id,
    };
  } catch {
    try {
      storage()?.removeItem(storagePrefix + context.actor);
    } catch {
      /* Storage may be disabled. */
    }
  }
  return identity;
}

function saveIdentity(context: Session, value: Identity) {
  assertSession(context);
  identity = value;
  try {
    storage()?.setItem(storagePrefix + context.actor, JSON.stringify(value));
  } catch {
    /* Server lookup remains authoritative. */
  }
}

function confirmed(
  context: Session,
  snapshot: ScanOperationSnapshot,
  key?: string,
  id?: string,
) {
  assertSession(context);
  if (
    (key !== undefined && snapshot.request_key !== key) ||
    (id !== undefined && snapshot.id !== id)
  ) {
    throw new OperationTranslationError("scan_response_identity_mismatch");
  }
  saveIdentity(context, {
    request_key: snapshot.request_key,
    operation_id: snapshot.id,
  });
  return snapshot;
}

function statusCode(error: unknown) {
  return axios.isAxiosError(error) ? error.response?.status : undefined;
}
function uncertain(error: unknown) {
  return (
    axios.isAxiosError(error) &&
    (!error.response || error.response.status >= 500)
  );
}

async function lookup(context: Session, key: string) {
  const { data } = await api.get<ScanOperationSnapshot>(
    `/scan-operations/by-request/${requestKey(key)}`,
    options,
  );
  return confirmed(context, data, key);
}

async function byRequest(key: string) {
  return lookup(session(), key);
}

async function status(id: string, offset = 0, limit = 100) {
  const context = session();
  const { data } = await api.get<ScanOperationSnapshot>(
    `/scan-operations/${encodeURIComponent(id)}`,
    {
      ...options,
      params: { offset, limit },
    },
  );
  return confirmed(context, data, undefined, id);
}

async function active() {
  const context = session();
  const { data } = await api.get<ScanOperationSnapshot | null>(
    "/scan-operations/active",
    options,
  );
  assertSession(context);
  return data === null ? null : confirmed(context, data);
}

async function restore() {
  const context = session();
  const saved = readIdentity(context);
  if (saved) {
    try {
      return saved.operation_id
        ? await status(saved.operation_id)
        : await lookup(context, saved.request_key);
    } catch (error) {
      if (statusCode(error) !== 404) throw error;
      clear();
      return active();
    }
  }
  assertSession(context);
  return active();
}

async function post(context: Session, payload: ScanOperationRequest) {
  assertSession(context);
  const { data } = await api.post<ScanOperationSnapshot>(
    "/scan-operations",
    payload,
    { timeout: 10000 },
  );
  return confirmed(context, data, payload.request_key);
}

async function submitRequest(context: Session, payload: ScanOperationRequest) {
  const saved = readIdentity(context);
  if (saved) {
    try {
      const previous = await lookup(context, saved.request_key);
      if (
        saved.request_key !== payload.request_key &&
        ["accepted", "queued", "running", "stopping", "recovering"].includes(
          previous.state,
        )
      )
        return previous;
    } catch (error) {
      if (statusCode(error) !== 404) throw error;
      // An authoritative absence permits a new identity after a database reset.
    }
  }
  saveIdentity(context, { request_key: payload.request_key });
  // Lost acknowledgements are reconciled with GETs, never a second blind POST.
  try {
    return await post(context, payload);
  } catch (error) {
    if (!uncertain(error)) throw error;
    try {
      return await lookup(context, payload.request_key);
    } catch {
      throw error;
    }
  }
}

async function submit(input: OperationRequest): Promise<ScanOperationSnapshot> {
  const context = session();
  const payload: ScanOperationRequest = JSON.parse(
    JSON.stringify(toScanOperationRequest(input)),
  );
  const signature = JSON.stringify(payload);
  if (flight?.actor === context.actor) {
    if (flight.signature !== signature)
      throw new OperationTranslationError("scan_submission_pending");
    return flight.promise;
  }
  const promise = submitRequest(context, payload).finally(() => {
    if (flight?.promise === promise) flight = undefined;
  });
  flight = { actor: context.actor, signature, promise };
  return promise;
}

function mutationBody(
  snapshot: ScanOperationSnapshot,
  key: string,
  itemIds: number[] = [],
): ScanOperationMutationRequest {
  if (
    !Number.isSafeInteger(snapshot.version) ||
    snapshot.version < 1 ||
    itemIds.length > 100 ||
    itemIds.some((id) => !Number.isSafeInteger(id) || id < 1)
  ) {
    throw new OperationTranslationError("invalid_scan_mutation");
  }
  return {
    request_key: requestKey(key),
    expected_version: snapshot.version,
    item_ids: [...new Set(itemIds)].sort((a, b) => a - b),
  };
}

async function mutate(
  context: Session,
  snapshot: ScanOperationSnapshot,
  send: () => Promise<AxiosResponse<ScanOperationSnapshot>>,
) {
  assertSession(context);
  try {
    return confirmed(
      context,
      (await send()).data,
      snapshot.request_key,
      snapshot.id,
    );
  } catch (error) {
    if (!uncertain(error)) throw error;
    const current = await lookup(context, snapshot.request_key);
    if (current.id !== snapshot.id)
      throw new OperationTranslationError("scan_response_identity_mismatch");
    // Any confirmed progress is returned before another explicit action.
    if (current.version !== snapshot.version) return current;
    assertSession(context);
    try {
      return confirmed(
        context,
        (await send()).data,
        snapshot.request_key,
        snapshot.id,
      );
    } catch (retryError) {
      if (!uncertain(retryError)) throw retryError;
      return lookup(context, snapshot.request_key);
    }
  }
}

async function cancel(
  snapshot: ScanOperationSnapshot,
  key: string = crypto.randomUUID(),
) {
  const context = session();
  const body = mutationBody(snapshot, key);
  return mutate(context, snapshot, () =>
    api.post<ScanOperationSnapshot>(
      `/scan-operations/${encodeURIComponent(snapshot.id)}/cancel`,
      body,
      options,
    ),
  );
}

async function resume(
  snapshot: ScanOperationSnapshot,
  key: string = crypto.randomUUID(),
) {
  const context = session();
  const body = mutationBody(snapshot, key);
  return mutate(context, snapshot, () =>
    api.post<ScanOperationSnapshot>(
      `/scan-operations/${encodeURIComponent(snapshot.id)}/resume`,
      body,
      options,
    ),
  );
}

async function retryMetadata(
  snapshot: ScanOperationSnapshot,
  itemIds: number[],
  key: string = crypto.randomUUID(),
) {
  const context = session();
  if (!itemIds.length)
    throw new OperationTranslationError("metadata_items_required");
  const body = mutationBody(snapshot, key, itemIds);
  return mutate(context, snapshot, () =>
    api.post<ScanOperationSnapshot>(
      `/scan-operations/${encodeURIComponent(snapshot.id)}/retry-metadata`,
      body,
      options,
    ),
  );
}

export default {
  submit,
  byRequest,
  active,
  status,
  restore,
  cancel,
  resume,
  retryMetadata,
};
