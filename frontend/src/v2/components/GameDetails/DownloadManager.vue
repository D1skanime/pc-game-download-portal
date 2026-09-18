<script setup lang="ts">
import { isEnhancedDownloadSupported } from "@/v2/composables/useBrowserDownloadQueue";
import DownloadQueueItem from "./DownloadQueueItem.vue";

defineProps<{
  items: Array<{ destination: string; size: number; status: string }>;
}>();
</script>
<template>
  <p v-if="isEnhancedDownloadSupported()" data-testid="enhanced-download-mode">
    Enhanced folder download
  </p>
  <section v-if="items.length" data-testid="download-manager">
    <DownloadQueueItem
      v-for="item in items"
      :key="item.destination"
      :item="item"
    />
  </section>
</template>
