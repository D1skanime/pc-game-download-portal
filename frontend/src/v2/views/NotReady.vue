<script setup lang="ts">
import { useRoute } from "vue-router";
import { useUiVersion } from "@/composables/useUiVersion";

const route = useRoute();
const uiVersion = useUiVersion();

function switchToV1() {
  uiVersion.value = "v1";
}
</script>

<template>
  <section class="r-v2-notready">
    <h1>Not available in the new UI yet</h1>
    <p>
      <code>{{ route.fullPath }}</code> hasn't been migrated to v2. Switch back
      to v1 to use it, or navigate to a v2-ready route.
    </p>
    <button class="r-v2-notready__btn" @click="switchToV1">
      Switch back to v1
    </button>
  </section>
</template>

<style scoped>
.r-v2-notready {
  max-width: 640px;
  margin: 0 auto;
  padding: var(--r-space-8);
  text-align: center;
  color: var(--r-color-fg);
}

.r-v2-notready h1 {
  font-size: var(--r-font-size-2xl);
  font-weight: var(--r-font-weight-semibold);
  margin-bottom: var(--r-space-4);
}

.r-v2-notready p {
  color: var(--r-color-fg-muted);
  margin-bottom: var(--r-space-6);
}

.r-v2-notready code {
  font-family: var(--r-font-family-mono);
  background-color: var(--r-color-surface);
  padding: 2px 6px;
  border-radius: var(--r-radius-sm);
}

.r-v2-notready__btn {
  appearance: none;
  border: 0;
  background-color: var(--r-color-brand-primary);
  color: #fff;
  padding: var(--r-space-3) var(--r-space-5);
  border-radius: var(--r-radius-md);
  font-size: var(--r-font-size-sm);
  font-weight: var(--r-font-weight-medium);
  cursor: pointer;
}

.r-v2-notready__btn:hover {
  background-color: var(--r-color-brand-primary-hover);
}
</style>
