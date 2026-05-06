<script setup lang="ts">
import { VChip } from "vuetify/components/VChip";

defineOptions({ inheritAttrs: false });

interface Props {
  variant?: "flat" | "text" | "elevated" | "tonal" | "outlined" | "plain";
  color?: string;
  size?: "x-small" | "small" | "default" | "large" | "x-large";
  label?: boolean;
  closable?: boolean;
  prependIcon?: string;
  appendIcon?: string;
  disabled?: boolean;
  rounded?: string | number | boolean;
}

withDefaults(defineProps<Props>(), {
  variant: "tonal",
  color: undefined,
  size: "default",
  prependIcon: undefined,
  appendIcon: undefined,
  rounded: "full",
});
</script>

<template>
  <VChip
    v-bind="$attrs"
    class="r-chip"
    :variant="variant"
    :color="color"
    :size="size"
    :label="label"
    :closable="closable"
    :prepend-icon="prependIcon"
    :append-icon="appendIcon"
    :disabled="disabled"
    :rounded="rounded"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VChip>
</template>

<style scoped>
.r-chip {
  font-weight: var(--r-font-weight-medium);
  letter-spacing: 0;
  padding: 0px 16px;
}

/* Clickable chips share the RBtn rest-→-hover illumination: a touch
   muted at rest, fully bright on hover. Vuetify adds .v-chip--clickable
   when the `clickable` prop is set, so non-interactive chips (regions,
   languages, tags…) keep their full opacity. */
.r-chip {
  opacity: 0.85;
  transition: opacity var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-chip:hover {
  opacity: 1;
}

/* Optical alignment for prepend/append icons — same fix as RBtn.
   v-chip never applies text-transform: uppercase, so its mixed-case
   labels always sit in the x-height band (below the line-box centre)
   while the icon — sized at ~85% of the text via
   `.v-chip .v-icon { --v-icon-size-multiplier: 0.857 }` — stays at
   the line-box geometric centre. A 3px downward nudge lines the icon
   up with the x-height optical centre. */
.r-chip :deep(.v-chip__prepend),
.r-chip :deep(.v-chip__append) {
  margin-block-start: 3px;
}
</style>
