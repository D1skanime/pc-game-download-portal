<script setup lang="ts">
// RMenuPanel — the shared glass "menu body" from the mockup.
//
// Use inside any menu surface (RMenu's default slot, a custom popover like
// GameContextMenu, settings drawers) to get the consistent visual
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
  background: rgba(16, 12, 28, 0.97);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.7),
    0 4px 20px rgba(0, 0, 0, 0.4);
  color: #fff;
  font-family: var(--r-font-family-sans);
  display: flex;
  flex-direction: column;
}

/* Light-mode variant uses an off-white glass surface. */
.r-v2.r-v2-light .r-menu-panel {
  background: rgba(255, 255, 255, 0.97);
  border-color: rgba(17, 17, 23, 0.1);
  color: var(--r-color-fg);
}
</style>
