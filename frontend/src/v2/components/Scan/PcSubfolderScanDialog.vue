<script setup lang="ts">
import { RBtn, RDialog, RIcon } from "@v2/lib";
import { onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import storageApi from "@/services/api/storage";
import type { SimpleRom } from "@/v2/data/adapters/legacy/stores/roms";

const props = defineProps<{
  modelValue: boolean;
  rom: SimpleRom;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: boolean): void;
  (event: "scan", relativePath: string): void;
}>();

const { t } = useI18n();
const loading = ref(false);
const error = ref(false);
const parentPath = ref("");
const currentPath = ref("");
const entries = ref<
  Awaited<ReturnType<typeof storageApi.browseRoot>>["data"]["entries"]
>([]);
let rootId: number | null = null;

function joinPath(...parts: string[]): string {
  return parts
    .map((part) => part.replace(/^\/+|\/+$/g, ""))
    .filter(Boolean)
    .join("/");
}

async function browse(path: string) {
  if (rootId === null) return;
  loading.value = true;
  error.value = false;
  try {
    entries.value = (await storageApi.browseRoot(rootId, path)).data.entries;
    currentPath.value = path;
  } catch {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

async function openDialog() {
  if (!props.modelValue) return;
  loading.value = true;
  error.value = false;
  try {
    const { data: mapping } = await storageApi.getMapping(
      props.rom.platform_id,
    );
    rootId = mapping.storage_root_id;
    parentPath.value = joinPath(mapping.relative_path, props.rom.fs_name);
    await browse(parentPath.value);
  } catch {
    error.value = true;
    loading.value = false;
  }
}

function close() {
  emit("update:modelValue", false);
}

function select(path: string) {
  emit("scan", path);
  close();
}

watch(() => props.modelValue, openDialog);
onMounted(openDialog);
</script>

<template>
  <RDialog
    :model-value="modelValue"
    scroll-content
    full-height-on-mobile
    width="620"
    @update:model-value="emit('update:modelValue', $event)"
    @close="close"
  >
    <template #header>
      {{ props.rom.fs_name }}
    </template>

    <template #content>
      <div class="pc-subfolder-scan">
        <div class="pc-subfolder-scan__path">
          {{ currentPath }}
        </div>

        <div v-if="loading" class="pc-subfolder-scan__state">
          {{ t("scan.scanning") }}
        </div>
        <div v-else-if="error" class="pc-subfolder-scan__state">
          <RBtn variant="outlined" @click="browse(currentPath || parentPath)">
            {{ t("common.retry") }}
          </RBtn>
        </div>
        <div v-else-if="entries.length === 0" class="pc-subfolder-scan__state">
          {{ t("scan.no-new-roms") }}
        </div>
        <div v-else class="pc-subfolder-scan__entries">
          <div
            v-for="entry in entries"
            :key="entry.relative_path"
            class="pc-subfolder-scan__entry"
          >
            <RIcon icon="mdi-folder-outline" size="22" />
            <span class="pc-subfolder-scan__name">{{ entry.name }}</span>
            <RBtn
              v-if="entry.navigable"
              size="small"
              variant="outlined"
              :aria-label="t('scan.scan')"
              @click="select(entry.relative_path)"
            >
              {{ t("scan.scan") }}
            </RBtn>
          </div>
        </div>

        <RBtn variant="text" @click="close">
          {{ t("common.cancel") }}
        </RBtn>
      </div>
    </template>
  </RDialog>
</template>

<style scoped>
.pc-subfolder-scan {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.pc-subfolder-scan__path {
  overflow-wrap: anywhere;
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-sm);
}

.pc-subfolder-scan__entries {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
}

.pc-subfolder-scan__entry {
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
  min-height: var(--r-touch-target);
  padding: var(--r-space-2) var(--r-space-3);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-sm);
}

.pc-subfolder-scan__name {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}

.pc-subfolder-scan__state {
  display: flex;
  justify-content: center;
  padding: var(--r-space-5);
  color: var(--r-color-fg-muted);
}
</style>
