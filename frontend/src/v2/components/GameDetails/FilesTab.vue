<script setup lang="ts">
// FilesTab — list of file-level details (name, extension, size, path,
// hashes). Each row renders via the feature-local FileRow component.
import FileRow from "@/v2/components/GameDetails/FileRow.vue";

defineOptions({ inheritAttrs: false });

export type FileRowEntry = { label: string; value: string; mono?: boolean };

defineProps<{ rows: FileRowEntry[] }>();
</script>

<template>
  <section class="r-v2-det-files">
    <FileRow
      v-for="row in rows"
      :key="row.label"
      :label="row.label"
      :value="row.value"
      :mono="row.mono"
    />
  </section>
</template>

<style scoped>
.r-v2-det-files {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 720px;
}
</style>
