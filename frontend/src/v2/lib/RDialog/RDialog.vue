<script setup lang="ts">
// RDialog — v2 dialog primitive. Wraps Vuetify's v-dialog with a
// glass-card surface and a slot layout that matches every v2 dialog
// (header · toolbar · prepend · content · append · empty-state · footer).
// v1's `src/components/common/RDialog.vue` is unrelated — the v1 UI keeps
// its own dialog primitive since we treat v1 as frozen until Wave 10.
//
// Slots
//   header       title bar content (left of the close button)
//   toolbar      optional secondary toolbar row below the header
//   prepend      content above the main body
//   content      main body (always rendered unless loading / empty)
//   append       content below the main body
//   empty-state  custom empty state (else picks by `emptyStateType`)
//   footer       optional footer toolbar row
//
// Props mirror the v1 RDialog API to keep slot contents portable; that's
// just naming — there's no runtime relationship between them.
import { computed, useSlots } from "vue";
import { useTheme } from "vuetify";
import { VDialog } from "vuetify/components/VDialog";
import EmptyFirmware from "@/components/common/EmptyStates/EmptyFirmware.vue";
import EmptyGame from "@/components/common/EmptyStates/EmptyGame.vue";
import EmptyPlatform from "@/components/common/EmptyStates/EmptyPlatform.vue";
import RIsotipo from "@/components/common/RIsotipo.vue";
import RIcon from "@/v2/lib/RIcon/RIcon.vue";

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    loadingCondition?: boolean;
    emptyStateCondition?: boolean;
    emptyStateType?: string | null;
    expandContentOnEmptyState?: boolean;
    scrollContent?: boolean;
    showRommIcon?: boolean;
    icon?: string | null;
    width?: number | string;
    height?: number | string;
  }>(),
  {
    loadingCondition: false,
    emptyStateCondition: false,
    emptyStateType: null,
    expandContentOnEmptyState: false,
    scrollContent: false,
    showRommIcon: false,
    icon: null,
    width: "auto",
    height: "auto",
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "close"): void;
}>();

const theme = useTheme();
const slots = useSlots();

// Recomputed per render — swap between v2 tokens when the theme flips.
const scrimColor = computed(() =>
  theme.global.name.value.endsWith("-light") ||
  theme.global.name.value === "light"
    ? "white"
    : "black",
);

function closeDialog() {
  emit("update:modelValue", false);
  emit("close");
}

void props;
</script>

<template>
  <VDialog
    :model-value="modelValue"
    :width="width"
    scroll-strategy="block"
    no-click-animation
    persistent
    z-index="9999"
    :scrim="scrimColor"
    content-class="r-dialog"
    @click:outside="closeDialog"
    @keydown.esc="closeDialog"
  >
    <div
      class="r-dialog__panel"
      :style="{
        minHeight: typeof height === 'number' ? `${height}px` : height,
        maxHeight: typeof height === 'number' ? `${height}px` : height,
      }"
    >
      <!-- Header bar -->
      <header class="r-dialog__header">
        <RIcon v-if="icon" :icon="icon" size="18" class="r-dialog__lead-icon" />
        <RIsotipo v-if="showRommIcon" :size="22" class="r-dialog__lead-icon" />
        <div class="r-dialog__header-slot">
          <slot name="header" />
        </div>
        <button
          type="button"
          class="r-dialog__close"
          aria-label="Close"
          @click="closeDialog"
        >
          <RIcon icon="mdi-close" size="16" />
        </button>
      </header>

      <!-- Optional secondary toolbar -->
      <div v-if="slots.toolbar" class="r-dialog__toolbar">
        <slot name="toolbar" />
      </div>

      <!-- Prepend -->
      <div v-if="slots.prepend" class="r-dialog__prepend">
        <slot name="prepend" />
      </div>

      <!-- Body (or loading / empty state) -->
      <div
        class="r-dialog__body"
        :class="{ 'r-dialog__body--scroll': scrollContent }"
      >
        <div v-if="loadingCondition" class="r-dialog__state">
          <div class="r-dialog__spinner" aria-label="Loading" />
        </div>

        <div v-else-if="emptyStateCondition" class="r-dialog__state">
          <EmptyGame v-if="emptyStateType === 'game'" />
          <EmptyPlatform v-else-if="emptyStateType === 'platform'" />
          <EmptyFirmware v-else-if="emptyStateType === 'firmware'" />
          <slot v-else name="empty-state" />
        </div>

        <slot v-else name="content" />
      </div>

      <!-- Append -->
      <div v-if="slots.append" class="r-dialog__append">
        <slot name="append" />
      </div>

      <!-- Footer bar -->
      <footer v-if="slots.footer" class="r-dialog__footer">
        <slot name="footer" />
      </footer>
    </div>
  </VDialog>
</template>

<style scoped>
/* Scoped styles apply to the r-dialog__* elements inside the dialog
   content. Vuetify teleports v-dialog to <body>, but the root class we
   style here is emitted on the content, so scoped styles still reach it
   via the usual data-v attribute pipeline. The outer `.r-dialog`
   override (padding/bg) lives in global.css because it lands on a root
   element outside this component's scope. */
.r-dialog__panel {
  display: flex;
  flex-direction: column;
  background: rgba(13, 17, 23, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow:
    0 20px 48px rgba(0, 0, 0, 0.55),
    0 4px 12px rgba(0, 0, 0, 0.35);
  overflow: hidden;
  color: var(--r-color-fg);
}

.r-dialog__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 10px 12px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
}

.r-dialog__lead-icon {
  flex-shrink: 0;
  color: rgba(255, 255, 255, 0.65);
}

.r-dialog__header-slot {
  flex: 1;
  min-width: 0;
  font-size: var(--r-font-size-md);
  font-weight: var(--r-font-weight-semibold);
  color: rgba(255, 255, 255, 0.92);
}

.r-dialog__close {
  appearance: none;
  background: transparent;
  border: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.55);
  cursor: pointer;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-dialog__close:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.r-dialog__toolbar {
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.r-dialog__prepend,
.r-dialog__append {
  padding: 0;
}

.r-dialog__body {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 18px;
}

.r-dialog__body--scroll {
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.15) transparent;
}

.r-dialog__state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 28px 0;
}

.r-dialog__spinner {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.12);
  border-top-color: var(--r-color-brand-primary);
  animation: r-dialog-spin 0.8s linear infinite;
}

@keyframes r-dialog-spin {
  to {
    transform: rotate(360deg);
  }
}

.r-dialog__footer {
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.03);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Light theme — dialog root carries .r-v2-light only when the app shell
   does (teleported content inherits the body data-theme, not our wrapper).
   We still shift surfaces via Vuetify's theme tokens so the panel reads
   correctly against a light scrim. */
:global(.r-v2.r-v2-light) .r-dialog__panel,
:global(.v-overlay__content.r-dialog .r-dialog__panel) {
  /* kept dark-on-dark by default; Vuetify themes kick in via CSS vars */
}
</style>
