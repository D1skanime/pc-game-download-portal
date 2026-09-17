export type DownloadState =
  | "QUEUED"
  | "PREPARING"
  | "READY"
  | "DOWNLOADING"
  | "PAUSED"
  | "VERIFYING"
  | "COMPLETED"
  | "AUTH_REQUIRED"
  | "SOURCE_CHANGED"
  | "MANIFEST_STALE"
  | "LOCAL_CONFLICT"
  | "DISK_FULL"
  | "PERMISSION_DENIED"
  | "NETWORK_ERROR"
  | "CHECKSUM_FAILED";

export interface JobSnapshot {
  jobId: string;
  state: DownloadState;
  fileName: string;
  completedBytes: number;
  totalBytes: number;
}

export interface ShellSnapshot {
  configuredOrigin: string | null;
  pairing: "unpaired" | "pending" | "paired";
  destinationRoot: string | null;
  manifestId: string | null;
  jobs: JobSnapshot[];
}

export interface DesktopBindings {
  invoke<T>(command: string, args?: Record<string, string>): Promise<T>;
  listen(
    event: "download_state",
    handler: (payload: ShellSnapshot) => void,
  ): Promise<() => void>;
}

const recoveryCopy: Record<DownloadState, string> = {
  QUEUED: "Waiting to start.",
  PREPARING: "Preparing original files.",
  READY: "Ready to download original files.",
  DOWNLOADING: "Downloading the original file.",
  PAUSED: "Paused. Resume when ready.",
  VERIFYING: "Verifying the original file.",
  COMPLETED: "Original file completed and verified.",
  AUTH_REQUIRED: "Authorization is required. Pair this desktop client again.",
  SOURCE_CHANGED: "The source changed. Submit a fresh manifest.",
  MANIFEST_STALE:
    "The manifest expired or was revoked. Submit a fresh manifest.",
  LOCAL_CONFLICT: "A local file already exists. Choose an explicit action.",
  DISK_FULL:
    "The local destination is full. Choose another destination or free space.",
  PERMISSION_DENIED:
    "The local destination denied access. Choose another destination.",
  NETWORK_ERROR:
    "The server connection failed. Check the connection and resume.",
  CHECKSUM_FAILED:
    "Verification failed. Resume to download the original file again.",
};

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  const units = ["KiB", "MiB", "GiB", "TiB"];
  let amount = value;
  let unit = "B";
  for (const next of units) {
    amount /= 1024;
    unit = next;
    if (amount < 1024) break;
  }
  return `${amount.toFixed(amount >= 10 ? 0 : 1)} ${unit}`;
}

export async function renderDesktopApp(
  root: HTMLElement,
  bindings: DesktopBindings,
): Promise<() => void> {
  let snapshot = await bindings.invoke<ShellSnapshot>("state_snapshot");
  root.innerHTML = "";

  const render = (): void => {
    root.innerHTML = `
      <section class="shell" aria-labelledby="title">
        <header class="shell__header">
          <p class="eyebrow">RomM Desktop</p>
          <h1 id="title">Download original files to this PC</h1>
          <p class="lede">This client transfers selected files directly to a local destination.</p>
        </header>
        <section class="card" aria-labelledby="connection-title">
          <h2 id="connection-title">Server and pairing</h2>
          <label>Server origin <input data-origin value="${snapshot.configuredOrigin ?? ""}" placeholder="https://server.example" /></label>
          <p>Configured server: <code>${snapshot.configuredOrigin ?? "Not configured"}</code></p>
          <button data-action="configure">Save server</button>
          <span class="status">Pairing: ${snapshot.pairing}</span>
        </section>
        <section class="card" aria-labelledby="download-title">
          <h2 id="download-title">Prepare a download</h2>
          <p>Manifest: <code>${snapshot.manifestId ?? "Not submitted"}</code></p>
          <p>Local destination: <code>${snapshot.destinationRoot ?? "Not selected"}</code></p>
          <button data-action="destination">Choose local destination</button>
          <label>Prepared manifest ID <input data-manifest value="${snapshot.manifestId ?? ""}" /></label>
          <button data-action="queue" ${snapshot.destinationRoot ? "" : "disabled"}>Queue original files</button>
        </section>
        <section class="jobs" aria-labelledby="jobs-title">
          <h2 id="jobs-title">Download status</h2>
          ${snapshot.jobs.length ? snapshot.jobs.map(renderJob).join("") : "<p>No downloads queued.</p>"}
        </section>
      </section>`;

    root
      .querySelector<HTMLButtonElement>('[data-action="configure"]')
      ?.addEventListener("click", async () => {
        const origin =
          root.querySelector<HTMLInputElement>("[data-origin]")?.value ?? "";
        await bindings.invoke("configure_origin", { origin });
      });
    root
      .querySelector<HTMLButtonElement>('[data-action="destination"]')
      ?.addEventListener("click", async () => {
        const handle = await bindings.invoke<string | null>(
          "choose_destination",
        );
        if (handle) {
          snapshot = { ...snapshot, destinationRoot: handle };
          render();
        }
      });
    root
      .querySelector<HTMLButtonElement>('[data-action="queue"]')
      ?.addEventListener("click", async () => {
        const manifestId =
          root.querySelector<HTMLInputElement>("[data-manifest]")?.value ?? "";
        const jobId = await bindings.invoke<string>("queue_manifest", {
          origin: snapshot.configuredOrigin ?? "",
          manifest_id: manifestId,
          destination_root: snapshot.destinationRoot ?? "",
        });
        snapshot = {
          ...snapshot,
          manifestId,
          jobs: [
            ...snapshot.jobs,
            {
              jobId,
              state: "QUEUED",
              fileName: "Original file",
              completedBytes: 0,
              totalBytes: 0,
            },
          ],
        };
        render();
      });
    root
      .querySelectorAll<HTMLButtonElement>("[data-conflict]")
      .forEach((button) => {
        button.addEventListener("click", async () => {
          await bindings.invoke("select_conflict_action", {
            job_id: button.dataset.jobId ?? "",
            action: button.dataset.conflict ?? "",
          });
        });
      });
  };

  const renderJob = (job: JobSnapshot): string => {
    const recovery = recoveryCopy[job.state];
    const recoveryAction = [
      "AUTH_REQUIRED",
      "SOURCE_CHANGED",
      "MANIFEST_STALE",
      "DISK_FULL",
      "PERMISSION_DENIED",
      "NETWORK_ERROR",
      "CHECKSUM_FAILED",
    ].includes(job.state)
      ? `<button data-recovery="${job.state}" data-job-id="${job.jobId}">Open recovery action</button>`
      : "";
    const conflict =
      job.state === "LOCAL_CONFLICT"
        ? `<div class="actions">
      <button data-conflict="overwrite" data-job-id="${job.jobId}">Overwrite</button>
      <button data-conflict="choose_another_destination" data-job-id="${job.jobId}">Choose another destination</button>
      <button data-conflict="skip" data-job-id="${job.jobId}">Skip</button>
    </div>`
        : "";
    return `<article class="job" data-state="${job.state}">
      <div class="job__heading"><strong>Original file: ${job.fileName}</strong><span>${job.state}</span></div>
      <p>${recovery}</p>${recoveryAction}
      <progress max="${job.totalBytes}" value="${job.completedBytes}"></progress>
      <small>${formatBytes(job.completedBytes)} of ${formatBytes(job.totalBytes)}</small>${conflict}
    </article>`;
  };

  render();
  return bindings.listen("download_state", (next) => {
    snapshot = next;
    render();
  });
}
