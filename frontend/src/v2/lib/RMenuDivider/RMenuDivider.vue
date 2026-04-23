<script setup lang="ts">
// RMenuDivider — the 1px hairline used between menu groups.
defineOptions({ inheritAttrs: false });
</script>

<template>
  <div class="r-menu-divider" role="separator" />
</template>

<style scoped>
.r-menu-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.07);
  margin: 4px 2px;
}

.r-v2.r-v2-light .r-menu-divider {
  background: rgba(17, 17, 23, 0.09);
}
</style>
