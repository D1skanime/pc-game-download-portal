<script setup lang="ts">
import { RBtn, RSpinner } from "@v2/lib";
import { computed, onMounted, onUnmounted, ref } from "vue";

defineOptions({ inheritAttrs: false });

interface Props {
  loading?: boolean;
  disabled?: boolean;
  autoTrigger?: boolean; // Auto-load when scrolled into view
  remaining?: number; // optional label hint
}

const props = withDefaults(defineProps<Props>(), {
  autoTrigger: true,
  remaining: undefined,
});

const emit = defineEmits<{
  (e: "load"): void;
}>();

const sentinel = ref<HTMLElement | null>(null);
let observer: IntersectionObserver | null = null;

function trigger() {
  if (props.loading || props.disabled) return;
  emit("load");
}

onMounted(() => {
  if (!props.autoTrigger || !sentinel.value) return;
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) trigger();
    },
    { rootMargin: "400px" },
  );
  observer.observe(sentinel.value);
});

onUnmounted(() => {
  observer?.disconnect();
});

const label = computed(() => {
  if (props.loading) return "Loading…";
  if (props.remaining != null) return `Load ${props.remaining} more`;
  return "Load more";
});
</script>

<template>
  <div class="r-load-more">
    <div v-if="autoTrigger" ref="sentinel" class="r-load-more__sentinel" />
    <RBtn
      :disabled="disabled || loading"
      variant="outlined"
      prepend-icon="mdi-chevron-down"
      @click="trigger"
    >
      <template v-if="loading" #prepend>
        <RSpinner :size="16" />
      </template>
      {{ label }}
    </RBtn>
  </div>
</template>

<style scoped>
.r-load-more {
  position: relative;
  display: flex;
  justify-content: center;
  padding: var(--r-space-6) 0;
}

.r-load-more__sentinel {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
</style>
