<script setup lang="ts">
import { RBtn, REmptyState } from "@v2/lib";
import { onBeforeUnmount, ref } from "vue";
import { useI18n } from "vue-i18n";
import { onBeforeRouteUpdate, useRoute } from "vue-router";
import type { DetailedRomSchema, PcComponentSchema } from "@/__generated__";
import { ROUTES } from "@/plugins/router";
import PcDlcDetail from "@/v2/components/GameDetails/PcDlcDetail.vue";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import romApi from "@/v2/data/adapters/legacy/services/api/rom";
import storeRoms from "@/v2/data/adapters/legacy/stores/roms";

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
const snackbar = useSnackbar();
const state = ref<PageState>("loading");
const parentRom = ref<DetailedRomSchema | null>(null);
const component = ref<PcComponentSchema | null>(null);
let generation = 0;
onBeforeUnmount(() => {
  generation++;
});

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

async function loadDlc(params: Record<string, unknown>, forceFresh = false) {
  const current = ++generation;
  const retainView = forceFresh && state.value === "ready";
  if (!retainView) {
    state.value = "loading";
    parentRom.value = null;
    component.value = null;
  }

  const romId = parseSafeRouteId(params.rom);
  const componentId = parseSafeRouteId(params.component);
  if (romId === null || componentId === null) {
    state.value = "unavailable";
    return;
  }

  try {
    const parent =
      !forceFresh && romsStore.currentRom?.id === romId
        ? romsStore.currentRom
        : (await romApi.getRom({ romId })).data;
    if (current !== generation) return;
    if (parent.id !== romId) {
      state.value = "unavailable";
      return;
    }

    const selectedComponent = resolveComponent(parent, componentId);
    if (!selectedComponent) {
      state.value = "unavailable";
      return;
    }

    if (forceFresh) romsStore.setCurrentRom(parent);
    parentRom.value = parent;
    component.value = selectedComponent;
    state.value = "ready";
  } catch (error) {
    if (current !== generation) return;
    console.error(error);
    if (!retainView) state.value = "unavailable";
    else snackbar.error(t("common.error"));
  }
}

async function refreshDlc() {
  await loadDlc(route.params, true);
}

void loadDlc(route.params);

onBeforeRouteUpdate(async (to) => {
  // Tab queries retain the current canonical DLC instead of reusing an older parent snapshot.
  if (
    state.value === "ready" &&
    parentRom.value?.id === parseSafeRouteId(to.params.rom) &&
    component.value?.id === parseSafeRouteId(to.params.component)
  )
    return;
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
