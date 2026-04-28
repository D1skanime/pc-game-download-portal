<script setup lang="ts">
// RForm — wrapper around Vuetify's VForm with two QoL extras:
//   * Enter on any field submits when the form validates clean. Spares the
//     consumer from binding @keyup.enter on every input.
//   * After a failed validate(), scrolls the first invalid field into view
//     and focuses it. Calls focus() on the descendant matching
//     `[aria-invalid="true"], .v-field--error input, .v-field--error
//     textarea`. Works with RTextField / RSelect / RCheckbox out of the box.
//
// The standard wrapper contract applies: inheritAttrs: false, $attrs forward
// to VForm, every named slot of VForm (default included) is passed through.
import { ref } from "vue";
import { VForm } from "vuetify/components/VForm";

defineOptions({ inheritAttrs: false });

interface Props {
  /** v-model:value, true when every field passes its rules. */
  modelValue?: boolean;
  /** Disable the Enter-to-submit shortcut. */
  disableEnterSubmit?: boolean;
  /** Disable the scroll-to-first-error helper. */
  disableScrollToError?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: undefined,
  disableEnterSubmit: false,
  disableScrollToError: false,
});

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean | null): void;
  (e: "submit", ev: Event): void;
}>();

type FormInstance = InstanceType<typeof VForm>;

const formRef = ref<FormInstance | null>(null);

async function validate() {
  const result = await formRef.value?.validate();
  if (!result?.valid && !props.disableScrollToError) {
    scrollToFirstError();
  }
  return result;
}

function reset() {
  formRef.value?.reset();
}

function resetValidation() {
  formRef.value?.resetValidation();
}

function formEl(): HTMLElement | null {
  const el = formRef.value?.$el;
  return el instanceof HTMLElement ? el : null;
}

function scrollToFirstError() {
  const root = formEl();
  if (!root) return;
  const target = root.querySelector<HTMLElement>(
    '.v-field--error input, .v-field--error textarea, [aria-invalid="true"]',
  );
  if (!target) return;
  target.scrollIntoView({ block: "center", behavior: "smooth" });
  if (typeof target.focus === "function") target.focus();
}

async function onKeyDown(event: KeyboardEvent) {
  if (props.disableEnterSubmit) return;
  if (event.key !== "Enter") return;
  // Allow textarea newlines and explicit Shift+Enter combos.
  const tag = (event.target as HTMLElement | null)?.tagName ?? "";
  if (tag === "TEXTAREA" || event.shiftKey) return;
  event.preventDefault();
  const result = await validate();
  if (result?.valid) emit("submit", event);
}

defineExpose({ validate, reset, resetValidation });
</script>

<template>
  <VForm
    ref="formRef"
    v-bind="$attrs"
    class="r-form"
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    @submit.prevent="emit('submit', $event)"
    @keydown="onKeyDown"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VForm>
</template>
