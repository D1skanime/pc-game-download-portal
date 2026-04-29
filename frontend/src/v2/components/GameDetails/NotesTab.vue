<script setup lang="ts">
// NotesTab — per-ROM notes. Displays the current user's notes + public
// notes from other users, with add/edit/delete inline. Edit/delete is
// only offered for the logged-in user's own notes; other users' notes
// render read-only.
import { RIcon } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import type { UserNoteSchema } from "@/__generated__";
import romApi from "@/services/api/rom";
import storeAuth from "@/stores/auth";
import type { DetailedRom } from "@/stores/roms";
import storeRoms from "@/stores/roms";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const props = defineProps<{ rom: DetailedRom }>();

const snackbar = useSnackbar();
const authStore = storeAuth();
const romsStore = storeRoms();
const { user } = storeToRefs(authStore);

const expanded = ref<Record<number, boolean>>({});
function toggle(id: number) {
  expanded.value[id] = !expanded.value[id];
}

const allNotes = computed<UserNoteSchema[]>(
  () => props.rom.all_user_notes ?? [],
);

const visibleNotes = computed<UserNoteSchema[]>(() => {
  const uid = user.value?.id;
  const own = uid ? allNotes.value.filter((n) => n.user_id === uid) : [];
  const others = uid
    ? allNotes.value.filter((n) => n.user_id !== uid && n.is_public)
    : allNotes.value.filter((n) => n.is_public);
  return [...own, ...others].sort(
    (a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );
});

function isOwn(note: UserNoteSchema) {
  return user.value?.id != null && note.user_id === user.value.id;
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

// ── Add / edit form state ─────────────────────────────────────────
const adding = ref(false);
const editingId = ref<number | null>(null);
const formTitle = ref("");
const formContent = ref("");
const formPublic = ref(false);
const saving = ref(false);

function startAdd() {
  editingId.value = null;
  formTitle.value = "";
  formContent.value = "";
  formPublic.value = false;
  adding.value = true;
}

function startEdit(note: UserNoteSchema) {
  editingId.value = note.id;
  formTitle.value = note.title;
  formContent.value = note.content ?? "";
  formPublic.value = note.is_public;
  adding.value = true;
}

function cancelForm() {
  adding.value = false;
  editingId.value = null;
}

async function refreshRom() {
  const { data } = await romApi.getRom({ romId: props.rom.id });
  romsStore.setCurrentRom(data);
}

async function save() {
  if (!formTitle.value.trim()) return;
  saving.value = true;
  try {
    const payload = {
      title: formTitle.value.trim(),
      content: formContent.value,
      is_public: formPublic.value,
    };
    if (editingId.value != null) {
      await romApi.updateRomNote({
        romId: props.rom.id,
        noteId: editingId.value,
        noteData: payload,
      });
    } else {
      await romApi.createRomNote({
        romId: props.rom.id,
        noteData: payload,
      });
    }
    await refreshRom();
    cancelForm();
  } catch (err) {
    console.error("Note save failed:", err);
    snackbar.error("Could not save note", { icon: "mdi-close-circle" });
  } finally {
    saving.value = false;
  }
}

async function remove(note: UserNoteSchema) {
  if (!isOwn(note)) return;
  if (!window.confirm(`Delete the note "${note.title}"?`)) return;
  try {
    await romApi.deleteRomNote({ romId: props.rom.id, noteId: note.id });
    await refreshRom();
  } catch (err) {
    console.error("Note delete failed:", err);
    snackbar.error("Could not delete note", { icon: "mdi-close-circle" });
  }
}
</script>

<template>
  <section class="r-v2-det-notes">
    <div v-if="!visibleNotes.length && !adding" class="r-v2-det-notes__empty">
      No notes yet.
    </div>

    <article
      v-for="note in visibleNotes"
      :key="note.id"
      class="r-v2-det-notes__card"
    >
      <header
        class="r-v2-det-notes__head"
        role="button"
        tabindex="0"
        @click="toggle(note.id)"
        @keydown.enter.prevent="toggle(note.id)"
        @keydown.space.prevent="toggle(note.id)"
      >
        <div>
          <div class="r-v2-det-notes__title">
            {{ note.title }}
          </div>
          <div class="r-v2-det-notes__meta">
            {{
              isOwn(note)
                ? formatDate(note.updated_at)
                : `${note.username} · ${formatDate(note.updated_at)}`
            }}
          </div>
        </div>
        <div class="r-v2-det-notes__badges">
          <span
            class="r-v2-det-notes__badge"
            :class="{ 'r-v2-det-notes__badge--public': note.is_public }"
          >
            {{ note.is_public ? "Public" : "Private" }}
          </span>
          <RIcon
            icon="mdi-chevron-down"
            size="18"
            class="r-v2-det-notes__chevron"
            :class="{ 'r-v2-det-notes__chevron--open': expanded[note.id] }"
          />
        </div>
      </header>
      <div v-if="expanded[note.id]" class="r-v2-det-notes__body">
        <p>{{ note.content || "(empty)" }}</p>
        <div v-if="isOwn(note)" class="r-v2-det-notes__row-actions">
          <button
            type="button"
            class="r-v2-det-notes__btn"
            @click="startEdit(note)"
          >
            Edit
          </button>
          <button
            type="button"
            class="r-v2-det-notes__btn r-v2-det-notes__btn--danger"
            @click="remove(note)"
          >
            Delete
          </button>
        </div>
      </div>
    </article>

    <button
      v-if="!adding"
      type="button"
      class="r-v2-det-notes__add"
      @click="startAdd"
    >
      + {{ editingId != null ? "Edit note" : "Add note" }}
    </button>

    <div v-else class="r-v2-det-notes__card r-v2-det-notes__form">
      <input
        v-model="formTitle"
        class="r-v2-det-notes__input"
        placeholder="Title"
        :disabled="saving"
      />
      <textarea
        v-model="formContent"
        class="r-v2-det-notes__input r-v2-det-notes__textarea"
        placeholder="Write your note…"
        aria-label="Note content"
        :disabled="saving"
      />
      <label class="r-v2-det-notes__public" for="note-public-toggle">
        <input
          id="note-public-toggle"
          v-model="formPublic"
          type="checkbox"
          :disabled="saving"
        />
        Make public
      </label>
      <div class="r-v2-det-notes__form-actions">
        <button
          type="button"
          class="r-v2-det-notes__btn"
          :disabled="saving"
          @click="cancelForm"
        >
          Cancel
        </button>
        <button
          type="button"
          class="r-v2-det-notes__btn r-v2-det-notes__btn--save"
          :disabled="saving || !formTitle.trim()"
          @click="save"
        >
          {{ saving ? "Saving…" : "Save" }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.r-v2-det-notes {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 720px;
}

.r-v2-det-notes__empty {
  padding: 24px 0;
  color: var(--r-color-fg-faint);
  font-size: 13px;
  font-style: italic;
}

.r-v2-det-notes__card {
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  overflow: hidden;
}

.r-v2-det-notes__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  transition: background var(--r-motion-fast);
}
.r-v2-det-notes__head:hover {
  background: var(--r-color-bg-elevated);
}

.r-v2-det-notes__title {
  font-size: 13.5px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg);
}
.r-v2-det-notes__meta {
  font-size: 11px;
  color: var(--r-color-fg-muted);
  margin-top: 2px;
}

.r-v2-det-notes__badges {
  display: flex;
  align-items: center;
  gap: 10px;
}

.r-v2-det-notes__badge {
  font-size: 10px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: var(--r-radius-lg);
  background: var(--r-color-surface);
  color: var(--r-color-fg-muted);
  border: 1px solid var(--r-color-border);
}
.r-v2-det-notes__badge--public {
  background: color-mix(
    in srgb,
    var(--r-color-status-base-success) 14%,
    transparent
  );
  color: color-mix(in srgb, var(--r-color-success) 90%, transparent);
  border-color: color-mix(
    in srgb,
    var(--r-color-status-base-success) 30%,
    transparent
  );
}

.r-v2-det-notes__chevron {
  color: var(--r-color-fg-muted);
  transition: transform var(--r-motion-fast);
}
.r-v2-det-notes__chevron--open {
  transform: rotate(180deg);
}

.r-v2-det-notes__body {
  padding: 0 16px 14px;
  border-top: 1px solid var(--r-color-border);
  color: var(--r-color-fg-secondary);
  font-size: 13px;
  line-height: 1.55;
}
.r-v2-det-notes__body p {
  margin: 12px 0;
  white-space: pre-wrap;
}

.r-v2-det-notes__row-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.r-v2-det-notes__btn {
  appearance: none;
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border-strong);
  border-radius: var(--r-radius-pill);
  color: var(--r-color-fg-secondary);
  padding: 6px 14px;
  font-size: 12px;
  font-weight: var(--r-font-weight-medium);
  font-family: inherit;
  cursor: pointer;
  transition:
    background var(--r-motion-fast),
    border-color var(--r-motion-fast);
}
.r-v2-det-notes__btn:hover:not(:disabled) {
  background: var(--r-color-surface-hover);
}
.r-v2-det-notes__btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.r-v2-det-notes__btn--danger {
  color: var(--r-color-danger);
  border-color: color-mix(
    in srgb,
    var(--r-color-status-base-danger) 30%,
    transparent
  );
}
.r-v2-det-notes__btn--danger:hover:not(:disabled) {
  background: color-mix(
    in srgb,
    var(--r-color-status-base-danger) 12%,
    transparent
  );
}
.r-v2-det-notes__btn--save {
  background: var(--r-color-fg);
  color: var(--r-color-bg);
  border-color: var(--r-color-fg);
}
.r-v2-det-notes__btn--save:hover:not(:disabled) {
  opacity: 0.85;
}

.r-v2-det-notes__add {
  appearance: none;
  background: var(--r-color-bg-elevated);
  border: 1px dashed var(--r-color-border-strong);
  border-radius: var(--r-radius-lg);
  color: var(--r-color-fg-secondary);
  padding: 12px 16px;
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  cursor: pointer;
  font-family: inherit;
  text-align: center;
}
.r-v2-det-notes__add:hover {
  background: var(--r-color-surface);
  color: var(--r-color-fg);
}

.r-v2-det-notes__form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
}

.r-v2-det-notes__input {
  appearance: none;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border-strong);
  border-radius: 8px;
  color: var(--r-color-fg);
  padding: 8px 12px;
  font-size: 13px;
  font-family: inherit;
}
.r-v2-det-notes__input:focus {
  outline: none;
  border-color: var(--r-color-fg-faint);
}
.r-v2-det-notes__textarea {
  min-height: 120px;
  line-height: 1.55;
  resize: vertical;
}

.r-v2-det-notes__public {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--r-color-fg-secondary);
  cursor: pointer;
}

.r-v2-det-notes__form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
