<script setup lang="ts">
// MissingFSBadge — tiny warning pill used in platform/ROM pickers to flag
// entries whose file is missing from disk. Replaces v1's
// `common/MissingFromFSIcon.vue` inside v2 contexts. Uses RTooltip so the
// tooltip styling matches the rest of v2.
import { RIcon, RTooltip } from "@v2/lib";

defineOptions({ inheritAttrs: false });

withDefaults(
  defineProps<{
    text: string;
    size?: number;
  }>(),
  {
    size: 14,
  },
);
</script>

<template>
  <span class="r-v2-missing-fs" role="img" :aria-label="text">
    <RTooltip :text="text" location="top" activator="parent" />
    <RIcon icon="mdi-folder-question" :size="size" />
  </span>
</template>

<style scoped>
.r-v2-missing-fs {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 7px;
  background: rgba(250, 204, 21, 0.14);
  border: 1px solid rgba(250, 204, 21, 0.3);
  color: #facc15;
  border-radius: var(--r-radius-pill);
  line-height: 1;
}
</style>
