<script setup lang="ts">
import { RCheckbox } from "@v2/lib";
import { useI18n } from "vue-i18n";
import { isEnhancedDownloadSupported } from "@/v2/composables/useBrowserDownloadQueue";

defineProps<{ modelValue: "standard" | "enhanced" }>();
const emit = defineEmits<{
  (event: "update:modelValue", value: "standard" | "enhanced"): void;
}>();
const { t } = useI18n();
const enhancedSupported = isEnhancedDownloadSupported();
</script>
<template>
  <RCheckbox
    :model-value="modelValue === 'standard'"
    :label="t('rom.download-browser-mode')"
    @update:model-value="emit('update:modelValue', 'standard')"
  />
  <p>{{ t("rom.download-standard-description") }}</p>
  <template v-if="enhancedSupported">
    <RCheckbox
      :model-value="modelValue === 'enhanced'"
      :label="t('rom.download-enhanced-mode')"
      @update:model-value="emit('update:modelValue', 'enhanced')"
    />
    <p>{{ t("rom.download-enhanced-description") }}</p>
  </template>
  <p v-else role="status">{{ t("rom.download-enhanced-unavailable") }}</p>
</template>
