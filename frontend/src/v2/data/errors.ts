import type { DataError } from "./contracts";

export function toDataError(error: unknown): DataError {
  const candidate = error as {
    message?: unknown;
    response?: { status?: unknown; data?: { detail?: unknown } };
  };
  const message =
    typeof candidate?.response?.data?.detail === "string"
      ? candidate.response.data.detail
      : typeof candidate?.message === "string"
        ? candidate.message
        : "Request failed";
  const status =
    typeof candidate?.response?.status === "number"
      ? candidate.response.status
      : undefined;
  return { message, status, cause: error };
}

export function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    throw new DOMException("The request was aborted", "AbortError");
  }
}
