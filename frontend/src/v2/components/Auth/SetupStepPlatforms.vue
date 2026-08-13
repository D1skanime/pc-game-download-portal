<script setup lang="ts">
import { RAlert, RPlatformIcon } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { SetupLibraryInfo } from "@/services/api/setup";

const props = defineProps<{ libraryInfo: SetupLibraryInfo }>();
const { t } = useI18n();

const supportedBySlug = computed(
  () =>
    new Map(
      props.libraryInfo.supported_platforms.map((platform) => [
        platform.fs_slug,
        platform,
      ]),
    ),
);

const detectedPlatforms = computed(() =>
  props.libraryInfo.existing_platforms.map((existing) => {
    const supported = supportedBySlug.value.get(existing.fs_slug);
    return {
      fs_slug: existing.fs_slug,
      slug: supported?.slug ?? existing.fs_slug,
      name: supported?.display_name ?? supported?.name ?? existing.fs_slug,
      rom_count: existing.rom_count,
    };
  }),
);

const detectedStructure = computed(() => props.libraryInfo.detected_structure);
const structurePattern = computed(() =>
  detectedStructure.value === "struct_b"
    ? "{platform}/roms"
    : "roms/{platform}",
);
</script>

<template>
  <section class="r-setup-platforms">
    <p class="r-setup-platforms__lead">
      {{ t("setup.supported-platforms-lead") }}
    </p>

    <div
      class="r-setup-platforms__banner"
      :data-tone="detectedStructure ? 'info' : 'warning'"
    >
      <div class="r-setup-platforms__banner-text">
        <strong>{{ structurePattern }}</strong>
        <span>
          {{
            t("setup.detected-platforms", { count: detectedPlatforms.length })
          }}
        </span>
      </div>
    </div>

    <div
      v-if="detectedPlatforms.length"
      class="r-setup-platforms__detected-grid"
    >
      <div
        v-for="platform in detectedPlatforms"
        :key="platform.fs_slug"
        class="r-setup-platforms__platform-row"
      >
        <RPlatformIcon
          :slug="platform.slug"
          :fs-slug="platform.fs_slug"
          :name="platform.name"
          :size="32"
          :show-tooltip="false"
        />
        <span class="r-setup-platforms__platform-name">
          {{ platform.name }}
        </span>
        <span class="r-setup-platforms__rom-count">
          {{ platform.rom_count }}
        </span>
      </div>
    </div>

    <RAlert v-else type="info" density="compact">
      {{ t("setup.no-platforms-detected") }}
    </RAlert>
  </section>
</template>

<style scoped>
.r-setup-platforms {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
  min-height: 0;
  flex: 1 1 auto;
}

.r-setup-platforms__lead {
  margin: 0 auto;
  max-width: 900px;
  text-align: center;
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-md);
  line-height: var(--r-line-height-normal);
}

/* ── Structure banner ────────────────────────────────────────────── */
.r-setup-platforms__banner {
  display: flex;
  align-items: center;
  padding: var(--r-space-3) var(--r-space-4);
  border-radius: var(--r-radius-md);
  border: 1px solid var(--r-color-border);
  background: var(--r-color-surface);
}

.r-setup-platforms__banner[data-tone="info"] {
  border-color: color-mix(
    in srgb,
    var(--r-color-brand-primary) 30%,
    transparent
  );
  background: color-mix(in srgb, var(--r-color-brand-primary) 6%, transparent);
}

.r-setup-platforms__banner[data-tone="warning"] {
  border-color: color-mix(
    in srgb,
    var(--r-color-status-base-warning) 35%,
    transparent
  );
  background: color-mix(
    in srgb,
    var(--r-color-status-base-warning) 8%,
    transparent
  );
}

.r-setup-platforms__banner-text {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--r-space-2);
  font-size: var(--r-font-size-sm);
  color: var(--r-color-fg-secondary);
  min-width: 0;
}

.r-setup-platforms__banner-text strong {
  color: var(--r-color-fg);
  font-weight: var(--r-font-weight-semibold);
}

.r-setup-platforms__banner-pattern {
  font-family: var(--r-font-family-mono);
  font-size: var(--r-font-size-xs);
  padding: 2px 6px;
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-sm);
  color: var(--r-color-fg);
}

.r-setup-platforms__banner-meta {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
}

/* ── Two-column body ─────────────────────────────────────────────── */
.r-setup-platforms__columns {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--r-space-5);
}

/* Stacked on mobile: the two sections stack into ONE vertical scroll area
   (the columns wrapper) instead of the desktop 2-column split. The lead,
   banner and summary stay fixed; only this lists region scrolls, like
   desktop's per-column scroll. Flex column (not the grid) so the panes stack
   cleanly; each pane flows and the wrapper scrolls. */
html[data-bp~="sm-and-down"] .r-setup-platforms__columns {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-5);
  overflow-y: auto;
  overflow-x: hidden;
  /* Promote to its own layer so Chromium recomputes this flex+overflow
     region's height when the list re-renders on selection. Without it the
     region isn't re-laid-out until a forced reflow, so the content collapses
     out of view after picking a platform (step 3's list works because it
     never re-renders on interaction). */
  transform: translateZ(0);
}
html[data-bp~="sm-and-down"] .r-setup-platforms__pane {
  flex: 0 0 auto;
}
html[data-bp~="sm-and-down"] .r-setup-platforms__pane-scroll {
  flex: 0 0 auto;
  overflow: visible;
  padding-right: 0;
}

.r-setup-platforms__pane {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}

.r-setup-platforms__pane-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: var(--r-space-1);
}

.r-setup-platforms__section-head {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
}

.r-setup-platforms__section-title {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
  margin: 0;
  font-size: var(--r-font-size-sm);
  font-weight: var(--r-font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--r-color-fg-secondary);
}

/* ── Toolbar ─────────────────────────────────────────────────────── */
.r-setup-platforms__toolbar {
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
  min-width: 0;
}

.r-setup-platforms__search {
  flex: 1 1 auto;
  min-width: 0;
}

/* ── Items list (shared) ─────────────────────────────────────────── */
.r-setup-platforms__items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--r-space-1);
}

/* Inside the manufacturer-group collapsible — rows go edge-to-edge,
   no outer inset. Each row strips its card chrome (border, radius,
   background) and switches to a top-border separator so the body of
   the collapsible reads as a flat list rather than a stack of small
   cards (matches the Scan view's ScanPlatform body). */
.r-setup-platforms__items--nested {
  padding: 0;
  margin-top: 0;
  gap: 0;
}

.r-setup-platforms__items--nested .r-setup-platforms__item {
  border: 0;
  border-radius: 0;
  background: transparent;
  border-top: 1px solid var(--r-color-border);
  padding: var(--r-space-2) var(--r-space-3);
}
.r-setup-platforms__items--nested .r-setup-platforms__item:first-child {
  border-top: 0;
}

/* Selected / available hover states stay informative but lose the
   border-color shift (no border to colour). */
.r-setup-platforms__items--nested
  .r-setup-platforms__item[data-state="selected"] {
  background: color-mix(
    in srgb,
    var(--r-color-status-base-success) 10%,
    transparent
  );
}
.r-setup-platforms__items--nested
  .r-setup-platforms__item[data-state="available"]:hover {
  background: var(--r-color-surface-hover);
}

.r-setup-platforms__item {
  display: grid;
  grid-template-columns: 18px 28px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--r-space-3);
  padding: var(--r-space-2) var(--r-space-3);
  min-height: 44px;
  border-radius: var(--r-radius-md);
  border: 1px solid var(--r-color-border);
  background: var(--r-color-surface);
  cursor: pointer;
  transition:
    background 150ms ease,
    border-color 150ms ease;
}

/* Detected items have no leading checkbox column. */
.r-setup-platforms__item[data-state="detected"] {
  grid-template-columns: 28px minmax(0, 1fr) auto;
  background: color-mix(in srgb, var(--r-color-brand-primary) 8%, transparent);
  border-color: color-mix(
    in srgb,
    var(--r-color-brand-primary) 25%,
    transparent
  );
  cursor: default;
}

.r-setup-platforms__item[data-state="selected"] {
  background: color-mix(
    in srgb,
    var(--r-color-status-base-success) 10%,
    transparent
  );
  border-color: color-mix(
    in srgb,
    var(--r-color-status-base-success) 30%,
    transparent
  );
}

.r-setup-platforms__item[data-state="available"]:hover {
  background: var(--r-color-surface-hover);
  border-color: var(--r-color-border-strong);
}

.r-setup-platforms__item-icon {
  width: 26px;
  height: 26px;
  border-radius: var(--r-radius-sm);
  background: var(--r-color-surface);
  padding: 2px;
  flex-shrink: 0;
}

.r-setup-platforms__item-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.r-setup-platforms__item-name {
  font-size: var(--r-font-size-md);
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.r-setup-platforms__item-slug {
  font-family: var(--r-font-family-mono);
  font-size: var(--r-font-size-xs);
  color: var(--r-color-fg-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.r-setup-platforms__item-state {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
}

/* ── Groups (browse mode) ────────────────────────────────────────── */
.r-setup-platforms__groups {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
}

.r-setup-platforms__group {
  border-radius: var(--r-radius-md);
}

.r-setup-platforms__group-label {
  font-weight: var(--r-font-weight-semibold);
  font-size: var(--r-font-size-md);
  color: var(--r-color-fg);
}

.r-setup-platforms__group-count {
  font-size: var(--r-font-size-xs);
  color: var(--r-color-fg-muted);
  padding: 2px var(--r-space-2);
  border-radius: var(--r-radius-pill);
  background: color-mix(in srgb, var(--r-color-fg) 6%, transparent);
}

/* ── Summary ─────────────────────────────────────────────────────── */
.r-setup-platforms__summary {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
  padding: var(--r-space-3);
  border-radius: var(--r-radius-md);
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border);
}

.r-setup-platforms__summary :deep(.r-icon) {
  flex-shrink: 0;
}

.r-setup-platforms__summary-text {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--r-space-2);
  font-size: var(--r-font-size-sm);
  color: var(--r-color-fg-secondary);
}

.r-setup-platforms__summary-text strong {
  color: var(--r-color-fg);
  font-weight: var(--r-font-weight-semibold);
}

.r-setup-platforms__summary-pattern {
  font-family: var(--r-font-family-mono);
  font-size: var(--r-font-size-xs);
  color: var(--r-color-fg-muted);
}
</style>
