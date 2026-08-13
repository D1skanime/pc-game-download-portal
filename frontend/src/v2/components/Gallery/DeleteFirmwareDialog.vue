<script setup lang="ts">
import { RBtn, RDialog } from "@v2/lib";
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import type { FirmwareSchema } from "@/__generated__";
import { formatBytes } from "@/utils";

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  modelValue: boolean;
  firmware: FirmwareSchema[];
  /** Performs the actual delete. Resolves on success (dialog closes)
   *  or rejects on failure (dialog stays open). */
  onConfirm: (firmware: FirmwareSchema[]) => Promise<void>;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
}>();

const { t } = useI18n();

const deleting = ref(false);

function closeDialog() {
  if (deleting.value) return;
  emit("update:modelValue", false);
}

async function confirm() {
  if (deleting.value) return;
  deleting.value = true;
  try {
    await props.onConfirm(props.firmware);
    emit("update:modelValue", false);
  } catch {
    // Parent surfaces the snackbar; we just stay open so the user can
    // retry or cancel.
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <RDialog
    :model-value="modelValue"
    icon="mdi-delete"
    :width="560"
    @update:model-value="$emit('update:modelValue', $event)"
    @close="closeDialog"
  >
    <template #header>
      <span>
        {{ t("platform.removing-firmware", firmware.length) }}
      </span>
    </template>

    <template #content>
      <ul class="r-v2-del-fw__list">
        <li v-for="f in firmware" :key="f.id" class="r-v2-del-fw__row">
          <div class="r-v2-del-fw__row-body">
            <span class="r-v2-del-fw__row-name">{{ f.file_name }}</span>
            <span class="r-v2-del-fw__row-meta">
              {{ formatBytes(f.file_size_bytes) }} ·
              <span class="r-v2-del-fw__row-hash">{{ f.md5_hash }}</span>
            </span>
          </div>
        </li>
      </ul>
    </template>

    <template #footer>
      <RBtn variant="text" :disabled="deleting" @click="closeDialog">
        {{ t("common.cancel") }}
      </RBtn>
      <RBtn
        variant="flat"
        color="danger"
        prepend-icon="mdi-delete"
        :loading="deleting"
        @click="confirm"
      >
        {{ t("common.confirm") }}
      </RBtn>
    </template>
  </RDialog>
</template>

<style scoped>
.r-v2-del-fw__list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  background: var(--r-color-bg-elevated);
  overflow: hidden;
}

.r-v2-del-fw__row {
  display: block;
  padding: 10px 12px;
  border-bottom: 1px solid var(--r-color-border);
  transition: background var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-del-fw__row:last-child {
  border-bottom: 0;
}

.r-v2-del-fw__row-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.r-v2-del-fw__row-name {
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.r-v2-del-fw__row-meta {
  font-size: 11px;
  color: var(--r-color-fg-muted);
}
.r-v2-del-fw__row-hash {
  font-family: var(--r-font-family-mono, monospace);
}
</style>
