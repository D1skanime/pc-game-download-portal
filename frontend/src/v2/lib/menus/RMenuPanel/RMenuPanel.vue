<script setup lang="ts">
// RMenuPanel — the shared glass "menu body" from the mockup.
//
// Use inside any menu surface (RMenu's default slot, a custom popover,
// settings drawers) to get the consistent visual
// language: 14px rounded, 28px backdrop blur, double-layer drop shadow,
// subtle white border. The caller composes its own content (RMenuHeader,
// RMenuItem, RMenuDivider) inside.

defineOptions({ inheritAttrs: false });

interface Props {
  width?: string | number;
  padding?: string;
}

const props = withDefaults(defineProps<Props>(), {
  width: "236px",
  padding: "6px",
});

const resolvedWidth =
  typeof props.width === "number" ? `${props.width}px` : props.width;
</script>

<template>
  <div class="r-menu-panel" :style="{ width: resolvedWidth, padding }">
    <slot />
  </div>
</template>

<style scoped>
.r-menu-panel {
  background: var(--r-color-panel);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  border: 1px solid var(--r-color-panel-border);
  border-radius: var(--r-radius-card);
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.7),
    0 4px 20px rgba(0, 0, 0, 0.4);
  color: var(--r-color-fg);
  font-family: var(--r-font-family-sans);
  display: flex;
  flex-direction: column;
}
</style>
