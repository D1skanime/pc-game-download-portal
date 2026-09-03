<script setup lang="ts">
import { RBtn, REmptyState } from "@v2/lib";
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { onBeforeRouteUpdate, useRoute } from "vue-router";
import type { DetailedRomSchema, PcComponentSchema } from "@/__generated__";
import { ROUTES } from "@/plugins/router";
import romApi from "@/services/api/rom";
import storeRoms from "@/stores/roms";
import PcDlcDetail from "@/v2/components/GameDetails/PcDlcDetail.vue";

type PageState = "loading" | "ready" | "unavailable";

const DECIMAL_ROUTE_PARAM = /^(?:0|[1-9]\d*)$/;

function parseSafeRouteId(value: unknown): number | null {
  if (typeof value !== "string" || !DECIMAL_ROUTE_PARAM.test(value)) {
    return null;
  }

  const id = Number(value);
  return Number.isSafeInteger(id) ? id : null;
}

const route = useRoute();
const romsStore = storeRoms();
const { t } = useI18n();
const state = ref<PageState>("loading");
const parentRom = ref<DetailedRomSchema | null>(null);
const component = ref<PcComponentSchema | null>(null);

function resolveComponent(
  parent: DetailedRomSchema,
  componentId: number,
): PcComponentSchema | null {
  return (
    parent.components?.find(
      (candidate) => candidate.id === componentId && candidate.kind === "dlc",
    ) ?? null
  );
}

async function loadDlc(params: Record<string, unknown>) {
  state.value = "loading";
  parentRom.value = null;
  component.value = null;

  const romId = parseSafeRouteId(params.rom);
  const componentId = parseSafeRouteId(params.component);
  if (romId === null || componentId === null) {
    state.value = "unavailable";
    return;
  }

  try {
    const parent =
      romsStore.currentRom?.id === romId
        ? romsStore.currentRom
        : (await romApi.getRom({ romId })).data;
    if (parent.id !== romId) {
      state.value = "unavailable";
      return;
    }

    const selectedComponent = resolveComponent(parent, componentId);
    if (!selectedComponent) {
      state.value = "unavailable";
      return;
    }

    parentRom.value = parent;
    component.value = selectedComponent;
    state.value = "ready";
  } catch (error) {
    console.error(error);
    state.value = "unavailable";
  }
}

async function refreshDlc() {
  await loadDlc(route.params);
}

void loadDlc(route.params);

onBeforeRouteUpdate(async (to) => {
  await loadDlc(to.params);
});
</script>

<template>
  <section v-if="state === 'loading'" data-testid="pc-dlc-loading">
    <p>{{ t("rom.loading-rom") }}</p>
  </section>

  <PcDlcDetail
    v-else-if="state === 'ready' && parentRom && component"
    :parent="parentRom"
    :component="component"
    @refresh="refreshDlc"
  />

  <REmptyState v-else>
    <RBtn :to="{ name: ROUTES.HOME }">
      {{ t("common.library") }}
    </RBtn>
  </REmptyState>
</template>
