<script setup lang="ts">
// RMenuDivider — the 1px hairline used between menu groups.
defineOptions({ inheritAttrs: true });
withDefaults(defineProps<{ noGutters?: boolean }>(), { noGutters: false });
</script>

<template>
  <div
    class="r-menu-divider"
    role="separator"
    :class="{ 'my-2': !noGutters }"
  />
</template>

<style scoped>
.r-menu-divider {
  height: 1px;
  background: var(--r-color-border);
  margin: 0px 2px;
}
</style>
