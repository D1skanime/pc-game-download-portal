<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { VBtn } from "vuetify/components/VBtn";

defineOptions({ inheritAttrs: false });

// RBtn — thin wrapper around v-btn with RomM v2 defaults:
//   - variant="flat" (our primary visual style)
//   - color="primary"
//   - rounded="md"
//   - font-weight medium, no uppercase (Vuetify's default)
//   - debounced spinner: when `loading` flips true, the spinner only
//     appears after `loadingDebounce` ms (default 200). Actions that
//     resolve quicker than that flash never paint a spinner. Going from
//     loading → not-loading is immediate.
// Every Vuetify prop remains available via $attrs.
interface Props {
  variant?: "flat" | "text" | "elevated" | "tonal" | "outlined" | "plain";
  color?: string;
  rounded?: string | number | boolean;
  loading?: boolean;
  /** ms before the spinner appears after `loading` becomes true. */
  loadingDebounce?: number;
  disabled?: boolean;
  block?: boolean;
  size?: "x-small" | "small" | "default" | "large" | "x-large";
  density?: "default" | "comfortable" | "compact";
  icon?: string | boolean;
  ripple?: boolean;
  prependIcon?: string;
  appendIcon?: string;
  type?: "button" | "submit" | "reset";
}

const props = withDefaults(defineProps<Props>(), {
  variant: "flat",
  color: "primary",
  rounded: "md",
  loading: false,
  loadingDebounce: 200,
  size: "default",
  density: "default",
  type: "button",
  prependIcon: undefined,
  appendIcon: undefined,
  icon: undefined,
  ripple: undefined,
});

const debouncedLoading = ref(false);
let pendingTimer: ReturnType<typeof setTimeout> | null = null;

function clearTimer() {
  if (pendingTimer) {
    clearTimeout(pendingTimer);
    pendingTimer = null;
  }
}

watch(
  () => props.loading,
  (next) => {
    clearTimer();
    if (!next) {
      debouncedLoading.value = false;
      return;
    }
    if (props.loadingDebounce <= 0) {
      debouncedLoading.value = true;
      return;
    }
    pendingTimer = setTimeout(() => {
      debouncedLoading.value = true;
      pendingTimer = null;
    }, props.loadingDebounce);
  },
  { immediate: true },
);

onBeforeUnmount(clearTimer);
</script>

<template>
  <VBtn
    v-bind="$attrs"
    class="r-btn"
    :variant="variant"
    :color="color"
    :rounded="rounded"
    :loading="debouncedLoading"
    :disabled="disabled"
    :block="block"
    :size="size"
    :density="density"
    :icon="icon"
    :ripple="ripple"
    :prepend-icon="prependIcon"
    :append-icon="appendIcon"
    :type="type"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VBtn>
</template>

<style scoped>
.r-btn {
  font-weight: var(--r-font-weight-medium);
  letter-spacing: 0;
  text-transform: none;
}
</style>
