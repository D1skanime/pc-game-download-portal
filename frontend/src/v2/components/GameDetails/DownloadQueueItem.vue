<script setup lang="ts">
import { RTag } from "@v2/lib";

defineProps<{ item: { destination: string; size: number; status: string } }>();
</script>
<template>
  <div class="download-queue-item">
    <span>{{ item.destination }}</span
    ><RTag :text="item.status" />
  </div>
</template>
