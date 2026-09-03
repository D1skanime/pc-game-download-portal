<script setup lang="ts">
import { RBtn, REmptyState, RTag } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { PcComponentSchema } from "@/__generated__";
import { formatBytes } from "@/utils";

defineOptions({ inheritAttrs: false });

const props = defineProps<{ romId: number; component: PcComponentSchema }>();

const { t } = useI18n();
const manifestMembers = computed(() => props.component.manifest_members);

function manifestDownloadUrl(memberId: number) {
  return `/api/roms/${props.romId}/pc-components/${props.component.id}/manifest-members/${memberId}/content`;
}

function ownedMediaDownloadUrl(mediaId: number) {
  return `/api/roms/${props.romId}/pc-components/${props.component.id}/media/${mediaId}/content`;
}
</script>

<template>
  <section class="pc-dlc-files" aria-labelledby="pc-dlc-files-heading">
    <h2 id="pc-dlc-files-heading" class="pc-dlc-files__heading">
      {{ t("rom.pc-dlc-local-files") }}
    </h2>

    <REmptyState
      v-if="manifestMembers.length === 0"
      :title="t('rom.pc-dlc-empty-files-title')"
      :description="t('rom.pc-dlc-empty-files-body')"
    />

    <ul v-else data-testid="pc-dlc-manifest" class="pc-dlc-files__list">
      <li
        v-for="member in manifestMembers"
        :key="member.id"
        class="pc-dlc-files__member"
      >
        <dl class="pc-dlc-files__evidence">
          <div class="pc-dlc-files__field">
            <dt>{{ t("rom.file") }}</dt>
            <dd class="pc-dlc-files__path" :title="member.relative_path">
              {{ member.relative_path }}
            </dd>
          </div>
          <RBtn
            :href="manifestDownloadUrl(member.id)"
            icon="mdi-download"
            :aria-label="t('rom.download')"
          />
          <div class="pc-dlc-files__field">
            <dt>{{ t("common.size") }}</dt>
            <dd>{{ formatBytes(member.size_bytes) }}</dd>
          </div>
          <div class="pc-dlc-files__field">
            <dt>SHA-256</dt>
            <dd class="pc-dlc-files__checksum" :title="member.sha256">
              <RTag label="SHA-256" :text="member.sha256" mono />
            </dd>
          </div>
        </dl>
      </li>
    </ul>

    <ul
      v-if="component.owned_media?.length"
      data-testid="pc-dlc-owned-media-downloads"
      class="pc-dlc-files__list"
    >
      <li
        v-for="media in component.owned_media"
        :key="media.id"
        class="pc-dlc-files__member"
      >
        <RBtn
          :href="ownedMediaDownloadUrl(media.id)"
          prepend-icon="mdi-download"
        >
          {{ t("rom.download") }}
        </RBtn>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.pc-dlc-files {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.pc-dlc-files__heading {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-2xl);
  font-weight: var(--r-font-weight-semibold);
  line-height: var(--r-line-height-tight);
}

.pc-dlc-files__list {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.pc-dlc-files__member {
  padding: var(--r-space-4);
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}

.pc-dlc-files__evidence {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(18rem, 1fr);
  gap: var(--r-space-4);
  margin: 0;
}

.pc-dlc-files__field {
  min-width: 0;
}

.pc-dlc-files__field dt {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-sm);
  font-weight: var(--r-font-weight-semibold);
}

.pc-dlc-files__field dd {
  margin: var(--r-space-1) 0 0;
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-md);
}

.pc-dlc-files__path,
.pc-dlc-files__checksum {
  overflow-wrap: anywhere;
}

html[data-bp~="sm-and-down"] .pc-dlc-files__evidence {
  grid-template-columns: minmax(0, 1fr);
}
</style>
