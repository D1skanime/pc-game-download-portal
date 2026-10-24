<script setup lang="ts">
import { RBtn, RIcon } from "@v2/lib";

defineOptions({ inheritAttrs: false });
defineProps<{
  label: string;
  hint: string;
  available?: boolean;
  loading?: boolean;
  disabled?: boolean;
}>();
const emit = defineEmits<{ upload: [] }>();
</script>
<template>
  <RBtn
    v-if="available"
    v-bind="$attrs"
    class="za-media-upload__button pa-1"
    variant="text"
    :loading="loading"
    :disabled="disabled"
    :aria-label="label"
    @click="emit('upload')"
  >
    <template #prepend
      ><RIcon icon="mdi-cloud-upload-outline" size="30" color="primary"
    /></template>
    {{ label }}
  </RBtn>
  <p class="ma-0 za-media-upload__hint flex-1-1">{{ hint }}</p>
</template>
<style scoped src="./mediaManagementUpload.css" />
