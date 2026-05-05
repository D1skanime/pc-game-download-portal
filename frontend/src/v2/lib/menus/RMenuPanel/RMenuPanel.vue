<script setup lang="ts">
// RMenuPanel — content container inside RMenu's slot.
//
// The v2 glass paint (background, blur, border, radius, shadow) lives
// on the parent overlay (`.r-menu` in RMenu) so RMenu and RSelect's
// dropdown share the exact same single rendering layer. RMenuPanel is
// the inner layout container: width + padding + flex column for
// header / items / dividers. Painting it again here would compound
// the backdrop-filter blur and shift the perceived colour vs. RSelect.

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
  display: flex;
  flex-direction: column;
}
</style>
