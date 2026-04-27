<script setup lang="ts">
import { VTextField } from "vuetify/components/VTextField";

defineOptions({ inheritAttrs: false });

// RTextField — wraps v-text-field. Default variant is "outlined" (modern,
// neutral density). Pass `variant="underlined"` for the auth forms.
//
// rules are typed loosely (`unknown[]`) because Vuetify's own rule type is
// structural and works for any function returning boolean|string.
interface Props {
  modelValue?: string | number | null;
  label?: string;
  type?: string;
  variant?:
    | "filled"
    | "outlined"
    | "plain"
    | "underlined"
    | "solo"
    | "solo-inverted"
    | "solo-filled";
  density?: "default" | "comfortable" | "compact";
  prependInnerIcon?: string;
  appendInnerIcon?: string;
  autocomplete?: string;
  name?: string;
  rules?: unknown[];
  hint?: string;
  hideDetails?: boolean | "auto";
  required?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  loading?: boolean;
  clearable?: boolean;
  error?: boolean;
  errorMessages?: string | string[];
}

withDefaults(defineProps<Props>(), {
  modelValue: undefined,
  label: undefined,
  type: "text",
  variant: "outlined",
  density: "default",
  prependInnerIcon: undefined,
  appendInnerIcon: undefined,
  autocomplete: undefined,
  name: undefined,
  rules: undefined,
  hint: undefined,
  hideDetails: false,
  errorMessages: undefined,
});

defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();
// click:append-inner / click:prepend-inner are *not* declared here on
// purpose. Vuetify only makes the inner icon tabbable when a click
// listener is attached, so we let the parent's listener flow through
// `$attrs` instead of always forwarding it. That way `prepend-inner-icon`
// stays decorative (no focus ring, no tab stop) unless the parent
// genuinely subscribes — which is what you want for the password-reveal
// eye icon, but not for a plain mdi-account adornment.
</script>

<template>
  <VTextField
    v-bind="$attrs"
    class="r-text-field"
    :model-value="modelValue"
    :label="label"
    :type="type"
    :variant="variant"
    :density="density"
    :prepend-inner-icon="prependInnerIcon"
    :append-inner-icon="appendInnerIcon"
    :autocomplete="autocomplete"
    :name="name"
    :rules="rules as never"
    :hint="hint"
    :hide-details="hideDetails"
    :required="required"
    :disabled="disabled"
    :readonly="readonly"
    :loading="loading"
    :clearable="clearable"
    :error="error"
    :error-messages="errorMessages"
    @update:model-value="(v) => $emit('update:modelValue', v)"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VTextField>
</template>
