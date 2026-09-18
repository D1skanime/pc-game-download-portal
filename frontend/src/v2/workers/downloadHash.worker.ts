import { createSHA256 } from "hash-wasm";

type HashRequest =
  | { id: number; type: "reset" }
  | { id: number; type: "update"; chunk: ArrayBuffer }
  | { id: number; type: "digest" };

let hasher = createSHA256();
self.onmessage = async (event: MessageEvent<HashRequest>) => {
  const request = event.data;
  if (request.type === "reset") {
    hasher = createSHA256();
    await hasher;
    self.postMessage({ id: request.id, type: "ready" });
    return;
  }
  if (request.type === "update") {
    (await hasher).update(new Uint8Array(request.chunk));
    self.postMessage({ id: request.id, type: "updated" });
    return;
  }
  self.postMessage({
    id: request.id,
    type: "digest",
    digest: (await hasher).digest(),
  });
};
