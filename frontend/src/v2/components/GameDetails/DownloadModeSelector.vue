<script setup lang="ts">
import { RCheckbox } from "@v2/lib";
import { useI18n } from "vue-i18n";

defineProps<{ modelValue: "standard" }>();
defineEmits<{ (event: "update:modelValue", value: "standard"): void }>();
const { t } = useI18n();
</script>
<template>
  <RCheckbox
    :model-value="true"
    disabled
    :label="t('rom.download-browser-mode')"
  />
</template>
