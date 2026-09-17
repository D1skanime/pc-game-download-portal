<script setup lang="ts">
import DownloadQueueItem from "./DownloadQueueItem.vue";

defineProps<{
  items: Array<{ destination: string; size: number; status: string }>;
}>();
</script>
<template>
  <section v-if="items.length" data-testid="download-manager">
    <DownloadQueueItem
      v-for="item in items"
      :key="item.destination"
      :item="item"
    />
  </section>
</template>
