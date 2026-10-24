<script setup lang="ts">
import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";

const props = defineProps<{
  url: string;
  label: string;
  newlyUploaded?: boolean;
}>();
const emit = defineEmits<{ preview: [] }>();
const { t } = useI18n();
const failed = ref(false);
watch(
  () => props.url,
  () => {
    failed.value = false;
  },
);
</script>
<template>
  <article class="za-shot" :class="{ 'za-shot--new': newlyUploaded }">
    <button
      type="button"
      class="za-shot__preview"
      data-preview
      :aria-label="label"
      @click="emit('preview')"
    >
      <span v-if="failed" class="za-shot__fallback">{{
        t("rom.screenshots-preview-unavailable")
      }}</span>
      <img
        v-else
        :src="url"
        :alt="label"
        loading="lazy"
        @error="failed = true"
      />
    </button>
    <div class="za-shot__body d-flex flex-column"><slot /></div>
  </article>
</template>
<style scoped src="./mediaManagementCard.css" />
