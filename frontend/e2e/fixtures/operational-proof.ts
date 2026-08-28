import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { gotoHydrated, login, seedUiState } from "./auth";

export const WORKFLOW_SLUGS = {
  mappingCreate: "mapping-create",
  mappingUpdate: "mapping-update",
  mappingRemove: "mapping-remove",
  browseTest: "browse-test",
  preview: "preview",
  scanHash: "scan-hash",
  metadataMatch: "metadata-match",
  streamPlay: "stream-play",
  singleDownload: "single-download",
  multiDownload: "multi-download",
  legacyMigration: "legacy-migration",
  supportedRollback: "supported-rollback",
  gameCatalogRemoval: "game-catalog-removal",
  platformMappingRemoval: "platform-mapping-removal",
} as const;

export type WorkflowSlug = (typeof WORKFLOW_SLUGS)[keyof typeof WORKFLOW_SLUGS];

export interface ProofCheckpoint {
  slug: WorkflowSlug;
  startedAt: string;
  initialUrl: string;
  routeHint: string;
}

interface JsonPage<T> {
  items?: T[];
}

export interface FilesystemPlatform {
  id: number;
  display_name?: string | null;
  name?: string | null;
}

export interface StorageRoot {
  id: number;
  name: string;
  active: boolean;
  health?: { reachable?: boolean };
}

export interface RomSummary {
  id: number;
  name?: string | null;
  fs_name?: string | null;
  platform_id?: number | null;
  files?: Array<{ id: number }>;
}

const ARTIFACTS_DIR = process.env.PHASE9_BROWSER_ARTIFACTS_DIR;

function nowIso() {
  return new Date().toISOString();
}

async function writeWorkflowArtifact(
  slug: WorkflowSlug,
  fileName: string,
  payload: Record<string, unknown>,
) {
  if (!ARTIFACTS_DIR) return;
  const workflowDir = path.join(ARTIFACTS_DIR, "workflows", slug);
  await mkdir(workflowDir, { recursive: true });
  await writeFile(
    path.join(workflowDir, fileName),
    `${JSON.stringify(payload, null, 2)}\n`,
    "utf8",
  );
}

async function getJson<T>(request: APIRequestContext, url: string): Promise<T> {
  const response = await request.get(url);
  expect(response.ok(), `GET ${url} should succeed`).toBe(true);
  return (await response.json()) as T;
}

export async function beginWorkflow(
  page: Page,
  slug: WorkflowSlug,
  routeHint: string,
) {
  const checkpoint: ProofCheckpoint = {
    slug,
    startedAt: nowIso(),
    initialUrl: page.url(),
    routeHint,
  };
  await writeWorkflowArtifact(slug, "browser.json", {
    schema_version: "phase9.browser.v1",
    workflow: slug,
    route_hint: routeHint,
    started_at: checkpoint.startedAt,
    initial_url: checkpoint.initialUrl,
    status: "started",
  });
  return checkpoint;
}

export async function completeWorkflow(
  page: Page,
  checkpoint: ProofCheckpoint,
  details: {
    status?: "passed" | "failed";
    headings?: string[];
    notes?: string[];
  } = {},
) {
  await writeWorkflowArtifact(checkpoint.slug, "browser.json", {
    schema_version: "phase9.browser.v1",
    workflow: checkpoint.slug,
    route_hint: checkpoint.routeHint,
    started_at: checkpoint.startedAt,
    completed_at: nowIso(),
    final_url: page.url(),
    status: details.status ?? "passed",
    headings: details.headings ?? [],
    notes: details.notes ?? [],
  });
}

export async function runWorkflow(
  page: Page,
  slug: WorkflowSlug,
  routeHint: string,
  action: (checkpoint: ProofCheckpoint) => Promise<void>,
) {
  const checkpoint = await beginWorkflow(page, slug, routeHint);
  try {
    await action(checkpoint);
    await completeWorkflow(page, checkpoint);
  } catch (error) {
    await completeWorkflow(page, checkpoint, {
      status: "failed",
      notes: [error instanceof Error ? error.message : String(error)],
    });
    throw error;
  }
}

export async function loginToV2(page: Page, path = "/") {
  await seedUiState(page, "dark");
  await login(page, "admin");
  await gotoHydrated(page, path);
}

export async function listFilesystemPlatforms(page: Page) {
  return getJson<FilesystemPlatform[]>(
    page.request,
    "/api/platforms/filesystem",
  );
}

export async function listStorageRoots(page: Page) {
  return getJson<StorageRoot[]>(page.request, "/api/storage/roots");
}

export async function listRoms(page: Page, query = "limit=10&order_by=name") {
  return getJson<JsonPage<RomSummary>>(page.request, `/api/roms?${query}`);
}

export async function firstFilesystemPlatform(page: Page) {
  const platforms = await listFilesystemPlatforms(page);
  expect(
    platforms.length,
    "expected at least one filesystem platform",
  ).toBeGreaterThan(0);
  return platforms[0];
}

export async function firstRom(page: Page) {
  const body = await listRoms(page);
  const rom = body.items?.[0];
  expect(rom, "expected at least one ROM").toBeTruthy();
  return rom as RomSummary;
}

export async function firstPlayableRom(page: Page) {
  const body = await listRoms(page, "limit=10&order_by=name&playable=true");
  const rom = body.items?.[0] ?? (await firstRom(page));
  return rom;
}

export async function expectHeading(page: Page, name: string | RegExp) {
  await expect(page.getByRole("heading", { name }).first()).toBeVisible();
}
