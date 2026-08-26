<script setup lang="ts">
import { RAlert, RBtn, RCard, RList, RListItem, RSkeletonBlock } from "@v2/lib";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { ROUTES } from "@/plugins/router";
import storageApi from "@/services/api/storage";
import storePlatforms from "@/stores/platforms";
import PlatformSelect from "@/v2/components/shared/PlatformSelect.vue";
import { useCan } from "@/v2/composables/useCan";

const { t } = useI18n();
const router = useRouter();
const platformsStore = storePlatforms();
const canAdmin = useCan("app.admin");
const roots = ref<Awaited<ReturnType<typeof storageApi.getRoots>>["data"]>([]);
const selectedPlatformId = ref<number | null>(null);
const loading = ref(true);
const failed = ref(false);

const selectedPlatform = computed(() =>
  platformsStore.allPlatforms.find(
    (platform) => platform.id === selectedPlatformId.value,
  ),
);

async function load() {
  loading.value = true;
  failed.value = false;
  try {
    if (platformsStore.allPlatforms.length === 0)
      await platformsStore.fetchPlatforms();
    roots.value = (await storageApi.getRoots()).data;
  } catch {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

function openMapping() {
  if (!selectedPlatform.value) return;
  router.push({
    name: ROUTES.PLATFORM_STORAGE_MAPPING,
    params: { platformId: selectedPlatform.value.id },
  });
}

onMounted(() => void load());
</script>

<template>
  <section class="r-storage-roots">
    <div class="r-storage-roots__head">
      <div>
        <h2>{{ t("storage.administration", "Storage administration") }}</h2>
        <p>
          {{
            t(
              "storage.roots-hint",
              "Choose a platform to safely review or change its storage mapping.",
            )
          }}
        </p>
      </div>
    </div>

    <RAlert v-if="!canAdmin" type="info">
      {{
        t(
          "storage.admin-only",
          "Storage administration is available to administrators.",
        )
      }}
    </RAlert>
    <template v-else-if="loading"><RSkeletonBlock height="160" /></template>
    <RAlert v-else-if="failed" type="error">
      <template #title>{{
        t("storage.roots-unavailable", "Storage roots are unavailable")
      }}</template>
      {{ t("storage.roots-retry", "Check the storage service and try again.") }}
      <template #append
        ><RBtn variant="outlined" @click="load">{{
          t("storage.check-again", "Check again")
        }}</RBtn></template
      >
    </RAlert>
    <template v-else>
      <RCard class="r-storage-roots__card">
        <RList>
          <RListItem
            v-for="root in roots"
            :key="root.id"
            :title="root.name"
            :subtitle="
              root.active
                ? root.health.reachable
                  ? t('storage.root-ready', 'Active and reachable')
                  : t('storage.root-unreachable', 'Active but unreachable')
                : t('storage.root-inactive', 'Inactive')
            "
            :prepend-icon="
              root.health.reachable
                ? 'mdi-folder-outline'
                : 'mdi-folder-alert-outline'
            "
          />
        </RList>
      </RCard>
      <div class="r-storage-roots__action">
        <PlatformSelect
          v-model="selectedPlatformId"
          :items="platformsStore.allPlatforms"
          :label="t('storage.platform', 'Platform')"
          :disabled="platformsStore.allPlatforms.length === 0"
        />
        <RBtn
          variant="flat"
          color="primary"
          :disabled="!selectedPlatform"
          @click="openMapping"
          >{{ t("storage.open", "Open storage mapping") }}</RBtn
        >
      </div>
    </template>
  </section>
</template>

<style scoped>
.r-storage-roots {
  display: grid;
  gap: 16px;
}
.r-storage-roots__head h2,
.r-storage-roots__head p {
  margin: 0;
}
.r-storage-roots__head p {
  margin-top: 4px;
  color: var(--r-color-fg-muted);
}
.r-storage-roots__card {
  padding: 8px;
}
.r-storage-roots__action {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}
html[data-bp~="xs"] .r-storage-roots__action {
  grid-template-columns: 1fr;
  align-items: stretch;
}
</style>
