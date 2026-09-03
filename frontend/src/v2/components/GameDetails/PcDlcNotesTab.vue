<script setup lang="ts">
import { RBtn, REmptyState, RTextField } from "@v2/lib";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type {
  PcComponentNoteCreateRequest,
  PcComponentNoteSchema,
  PcComponentSchema,
} from "@/__generated__";
import { romApi as api } from "@/services/api/rom";
import storeAuth from "@/stores/auth";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const props = defineProps<{ romId: number; component: PcComponentSchema }>();
const { t } = useI18n();
const authStore = storeAuth();
const confirm = useConfirm();
const snackbar = useSnackbar();
const notes = ref<PcComponentNoteSchema[]>([]);
const loading = ref(true);
const saving = ref(false);
const title = ref("");
const content = ref("");
const tags = ref("");
const isPublic = ref(false);
const endpoint = `/roms/${props.romId}/pc-components/${props.component.id}/notes`;
const canCreate = computed(() => title.value.trim().length > 0);
const componentVersion = computed(() => props.component.updated_at ?? null);

function canEdit(note: PcComponentNoteSchema) {
  return note.user_id === authStore.user?.id;
}

async function load() {
  loading.value = true;
  try {
    notes.value = (await api.get<PcComponentNoteSchema[]>(endpoint)).data;
  } catch (error) {
    console.error(error);
    snackbar.error(t("common.error"));
  } finally {
    loading.value = false;
  }
}

async function create() {
  if (!canCreate.value || !componentVersion.value) return;
  saving.value = true;
  const payload: PcComponentNoteCreateRequest = {
    title: title.value.trim(),
    content: content.value,
    is_public: isPublic.value,
    tags: tags.value
      ? tags.value
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean)
      : [],
    expected_version: componentVersion.value,
  };
  try {
    const note = (await api.post<PcComponentNoteSchema>(endpoint, payload))
      .data;
    notes.value = [note, ...notes.value];
    title.value = "";
    content.value = "";
    tags.value = "";
    isPublic.value = false;
    snackbar.success(t("common.save"));
  } catch (error) {
    console.error(error);
    snackbar.error(t("common.error"));
  } finally {
    saving.value = false;
  }
}

async function remove(noteId: number) {
  if (!componentVersion.value) return;
  if (!(await confirm({ title: t("common.delete"), tone: "danger" }))) return;
  try {
    await api.delete(`${endpoint}/${noteId}`, {
      params: { expected_version: componentVersion.value },
    });
    notes.value = notes.value.filter((note) => note.id !== noteId);
    snackbar.success(t("common.delete"));
  } catch (error) {
    console.error(error);
    snackbar.error(t("common.error"));
  }
}

onMounted(load);
</script>

<template>
  <section class="pc-dlc-notes" aria-labelledby="pc-dlc-notes-heading">
    <h2 id="pc-dlc-notes-heading" class="pc-dlc-notes__heading">
      {{ t("rom.tab-notes") }}
    </h2>
    <RTextField v-model="title" :label="t('common.title')" />
    <RTextField v-model="content" :label="t('common.description')" multiline />
    <RTextField v-model="tags" :label="t('rom.tags')" />
    <RBtn
      :variant="isPublic ? 'flat' : 'outlined'"
      @click="isPublic = !isPublic"
    >
      {{ t("common.public") }}
    </RBtn>
    <RBtn
      :disabled="!canCreate || !componentVersion"
      :loading="saving"
      @click="create"
      >{{ t("common.save") }}</RBtn
    >
    <p v-if="loading">{{ t("common.loading") }}</p>
    <REmptyState v-else-if="notes.length === 0" :title="t('rom.notes-empty')" />
    <article
      v-for="note in notes"
      v-else
      :key="note.id"
      class="pc-dlc-notes__note"
    >
      <h3>{{ note.title }}</h3>
      <p>{{ note.content }}</p>
      <RBtn
        v-if="canEdit(note)"
        icon="mdi-delete-outline"
        :aria-label="t('common.delete')"
        @click="remove(note.id)"
      />
    </article>
  </section>
</template>

<style scoped>
.pc-dlc-notes {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}
.pc-dlc-notes__heading,
.pc-dlc-notes__note h3 {
  margin: 0;
  color: var(--r-color-fg);
}
.pc-dlc-notes__note {
  padding: var(--r-space-4);
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}
</style>
