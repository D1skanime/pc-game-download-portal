<script setup lang="ts">
// v2 AboutDialog — emitter-driven. Replaces the v1 AboutDialog in the v2
// GlobalDialogs stack so the "About" entry in UserMenu renders the v2 glass
// panel instead of the legacy card.
import { RDialog, RIcon } from "@v2/lib";
import type { Emitter } from "mitt";
import { computed, inject, onBeforeUnmount, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { Events } from "@/types/emitter";
import ProjectBrand from "@/v2/components/shared/ProjectBrand.vue";
import {
  PROJECT_DOCS_URL,
  PROJECT_GITHUB_URL,
  projectReleaseTagUrl,
} from "@/v2/config/project";
import storeHeartbeat from "@/v2/data/adapters/legacy/stores/heartbeat";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const heartbeatStore = storeHeartbeat();
const emitter = inject<Emitter<Events>>("emitter");
const show = ref(false);

const openHandler = () => {
  show.value = true;
};
emitter?.on("showAboutDialog", openHandler);
onBeforeUnmount(() => emitter?.off("showAboutDialog", openHandler));

function closeDialog() {
  show.value = false;
}

type Link = {
  icon?: string;
  isotipo?: boolean;
  label: string;
  value: string;
  href: string;
};

const links = computed<Link[]>(() => [
  {
    isotipo: true,
    label: t("common.about-version"),
    value: heartbeatStore.value.SYSTEM.VERSION,
    href: projectReleaseTagUrl(heartbeatStore.value.SYSTEM.VERSION),
  },
  {
    icon: "mdi-code-braces",
    label: t("common.about-source-code"),
    value: "GitHub",
    href: PROJECT_GITHUB_URL,
  },
  {
    icon: "mdi-file-document-outline",
    label: t("common.about-documentation"),
    value: "GitHub",
    href: PROJECT_DOCS_URL,
  },
  {
    icon: "mdi-account-group",
    label: t("common.about-community"),
    value: "RomM (upstream) Discord",
    href: "https://discord.com/invite/P5HtHnhUDH",
  },
]);
</script>

<template>
  <RDialog
    v-model="show"
    icon="mdi-help-circle-outline"
    width="520"
    @close="closeDialog"
  >
    <template #header>
      <span>{{ t("common.about-romm") }}</span>
    </template>
    <template #content>
      <div class="r-v2-about">
        <a
          v-for="link in links"
          :key="link.label"
          :href="link.href"
          target="_blank"
          rel="noopener noreferrer"
          class="r-v2-about__tile"
        >
          <div class="r-v2-about__icon">
            <ProjectBrand v-if="link.isotipo" variant="about" />
            <RIcon v-else-if="link.icon" :icon="link.icon" size="18" />
          </div>
          <div class="r-v2-about__meta">
            <span class="r-v2-about__label">{{ link.label }}</span>
            <span class="r-v2-about__value">{{ link.value }}</span>
          </div>
          <RIcon icon="mdi-open-in-new" size="14" class="r-v2-about__chev" />
        </a>
      </div>
    </template>
  </RDialog>
</template>

<style scoped>
.r-v2-about {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.r-v2-about__tile {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--r-radius-md);
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  text-decoration: none;
  color: inherit;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out),
    transform var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-about__tile:hover {
  background: var(--r-color-surface);
  border-color: var(--r-color-border-strong);
  transform: translateY(-1px);
}

.r-v2-about__icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: var(--r-color-surface);
  color: var(--r-color-fg);
  flex-shrink: 0;
}

.r-v2-about__meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.r-v2-about__label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--r-color-fg-muted);
}

.r-v2-about__value {
  font-size: 13px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-brand-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.r-v2-about__chev {
  color: var(--r-color-fg-muted);
}
.r-v2-about__tile:hover .r-v2-about__chev {
  color: var(--r-color-fg);
}

html[data-bp~="xs"] .r-v2-about {
  grid-template-columns: 1fr;
}
</style>
