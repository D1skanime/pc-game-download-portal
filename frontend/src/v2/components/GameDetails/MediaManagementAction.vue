<script setup lang="ts">
import { RBtn, RIcon } from "@v2/lib";
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    icon: string;
    caption: string;
    label: string;
    tone?: "brand" | "info" | "danger";
    selected?: boolean;
    pressed?: boolean;
    disabled?: boolean;
    loading?: boolean;
  }>(),
  { tone: "brand", selected: undefined, pressed: undefined },
);
const emit = defineEmits<{ click: [] }>();
const accent = computed(() =>
  props.tone === "brand"
    ? "var(--r-color-brand-primary)"
    : `var(--r-color-${props.tone})`,
);
</script>
<template>
  <RBtn
    size="small"
    class="za-shot__action"
    :class="{
      'za-shot__action--selected': selected,
      'za-shot__action--danger': tone === 'danger',
    }"
    :style="{ '--za-action-accent': accent }"
    :variant="tone === 'danger' ? 'outlined' : 'translucent'"
    :border="tone !== 'danger'"
    :color="accent"
    :aria-pressed="pressed ?? selected"
    :aria-label="label"
    :tooltip="label"
    :disabled="disabled"
    :loading="loading"
    @click="emit('click')"
  >
    <span class="za-shot__action-content">
      <span class="za-shot__identity">
        <RIcon :icon="icon" size="18" />
        <RIcon
          v-if="selected"
          class="za-shot__check"
          icon="mdi-check"
          size="10"
          aria-hidden="true"
        />
      </span>
      <span>{{ caption }}</span>
    </span>
  </RBtn>
</template>
<style scoped src="./mediaManagementCard.css" />
