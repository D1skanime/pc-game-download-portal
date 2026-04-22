<script setup lang="ts">
import { RBtn, RChip, RIcon, RSkeletonBlock } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";
import storeAuth from "@/stores/auth";
import storeCollections from "@/stores/collections";
import storePlatforms from "@/stores/platforms";

const authStore = storeAuth();
const platformsStore = storePlatforms();
const collectionsStore = storeCollections();

const { user } = storeToRefs(authStore);
const { filledPlatforms, fetchingPlatforms, allPlatforms } =
  storeToRefs(platformsStore);
const { allCollections, fetchingCollections } = storeToRefs(collectionsStore);

onMounted(() => {
  if (platformsStore.allPlatforms.length === 0) {
    platformsStore.fetchPlatforms();
  }
  if (collectionsStore.allCollections.length === 0) {
    collectionsStore.fetchCollections();
  }
});

const greeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
});

const totalRoms = computed(() =>
  filledPlatforms.value.reduce((acc, p) => acc + p.rom_count, 0),
);

function platformCover(platformName: string) {
  // v1 serves platform icons from /assets/platforms. Use the lowercase name.
  return `/assets/platforms/${platformName.toLowerCase()}.ico`;
}
</script>

<template>
  <section class="r-v2-home">
    <!-- Greeting / stats strip -->
    <header class="r-v2-home__hero">
      <div class="r-v2-home__greeting">
        <div class="r-v2-home__eyebrow">Library</div>
        <h1 class="r-v2-home__title">
          {{ greeting }}<template v-if="user"> , {{ user.username }} </template>
        </h1>
        <p class="r-v2-home__subtitle">
          Jump back in — your whole catalogue, one click away.
        </p>
      </div>
      <div class="r-v2-home__stats">
        <div class="r-v2-home__stat">
          <div class="r-v2-home__stat-value">
            <template v-if="!fetchingPlatforms">
              {{ allPlatforms.length }}
            </template>
            <RSkeletonBlock v-else :width="56" :height="30" />
          </div>
          <div class="r-v2-home__stat-label">Platforms</div>
        </div>
        <div class="r-v2-home__stat">
          <div class="r-v2-home__stat-value">
            <template v-if="!fetchingPlatforms">
              {{ totalRoms.toLocaleString() }}
            </template>
            <RSkeletonBlock v-else :width="72" :height="30" />
          </div>
          <div class="r-v2-home__stat-label">Games</div>
        </div>
        <div class="r-v2-home__stat">
          <div class="r-v2-home__stat-value">
            <template v-if="!fetchingCollections">
              {{ allCollections.length }}
            </template>
            <RSkeletonBlock v-else :width="56" :height="30" />
          </div>
          <div class="r-v2-home__stat-label">Collections</div>
        </div>
      </div>
    </header>

    <!-- Platforms -->
    <section class="r-v2-home__section">
      <div class="r-v2-home__section-head">
        <h2 class="r-v2-home__section-title">
          <RIcon icon="mdi-controller" class="r-v2-home__section-icon" />
          Platforms
        </h2>
        <RChip v-if="!fetchingPlatforms" size="small" variant="tonal">
          {{ filledPlatforms.length }}
        </RChip>
      </div>

      <div class="r-v2-home__grid">
        <template v-if="fetchingPlatforms && filledPlatforms.length === 0">
          <div v-for="n in 8" :key="n" class="r-v2-home__platform-card">
            <RSkeletonBlock :width="64" :height="64" rounded="md" />
            <RSkeletonBlock :width="120" :height="14" />
            <RSkeletonBlock :width="64" :height="12" />
          </div>
        </template>
        <template v-else>
          <router-link
            v-for="platform in filledPlatforms"
            :key="platform.id"
            :to="`/platform/${platform.id}`"
            class="r-v2-home__platform-card"
          >
            <img
              :src="platformCover(platform.name)"
              :alt="platform.display_name"
              class="r-v2-home__platform-icon"
              loading="lazy"
              @error="
                (e) =>
                  ((e.target as HTMLImageElement).style.visibility = 'hidden')
              "
            />
            <span class="r-v2-home__platform-name">
              {{ platform.display_name }}
            </span>
            <span class="r-v2-home__platform-count">
              {{ platform.rom_count }} games
            </span>
          </router-link>
        </template>
      </div>

      <div
        v-if="!fetchingPlatforms && filledPlatforms.length === 0"
        class="r-v2-home__empty"
      >
        No platforms found. Run a scan to populate your library.
        <RBtn class="mt-3" to="/scan" prepend-icon="mdi-magnify-scan">
          Open scanner
        </RBtn>
      </div>
    </section>

    <!-- Collections -->
    <section class="r-v2-home__section">
      <div class="r-v2-home__section-head">
        <h2 class="r-v2-home__section-title">
          <RIcon
            icon="mdi-bookmark-box-multiple"
            class="r-v2-home__section-icon"
          />
          Collections
        </h2>
        <RChip v-if="!fetchingCollections" size="small" variant="tonal">
          {{ allCollections.length }}
        </RChip>
      </div>

      <div class="r-v2-home__collections">
        <template v-if="fetchingCollections && allCollections.length === 0">
          <RSkeletonBlock
            v-for="n in 4"
            :key="n"
            :width="220"
            :height="76"
            rounded="md"
          />
        </template>
        <template v-else>
          <router-link
            v-for="collection in allCollections"
            :key="collection.id"
            :to="`/collection/${collection.id}`"
            class="r-v2-home__collection-card"
          >
            <div class="r-v2-home__collection-cover">
              <RIcon
                :icon="
                  collection.is_favorite ? 'mdi-star' : 'mdi-bookmark-multiple'
                "
                size="32"
                :color="collection.is_favorite ? 'romm-gold' : 'primary'"
              />
            </div>
            <div class="r-v2-home__collection-body">
              <div class="r-v2-home__collection-name">
                {{ collection.name }}
              </div>
              <div class="r-v2-home__collection-count">
                {{ collection.rom_count }} games
              </div>
            </div>
          </router-link>
        </template>
      </div>

      <div
        v-if="!fetchingCollections && allCollections.length === 0"
        class="r-v2-home__empty"
      >
        You don't have any collections yet. Create one from any ROM's action
        bar.
      </div>
    </section>
  </section>
</template>

<style scoped>
.r-v2-home {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-10);
  max-width: 1400px;
  margin: 0 auto;
}

/* Hero */
.r-v2-home__hero {
  display: flex;
  flex-wrap: wrap;
  gap: var(--r-space-6);
  align-items: flex-end;
  justify-content: space-between;
}

.r-v2-home__eyebrow {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-sm);
  font-weight: var(--r-font-weight-medium);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: var(--r-space-2);
}

.r-v2-home__title {
  font-size: var(--r-font-size-4xl);
  font-weight: var(--r-font-weight-bold);
  line-height: var(--r-line-height-tight);
  margin: 0;
}

.r-v2-home__subtitle {
  color: var(--r-color-fg-muted);
  margin: var(--r-space-2) 0 0 0;
}

.r-v2-home__stats {
  display: flex;
  gap: var(--r-space-8);
  padding: var(--r-space-4) var(--r-space-6);
  background-color: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  box-shadow: var(--r-elev-2);
}

.r-v2-home__stat-value {
  font-size: var(--r-font-size-3xl);
  font-weight: var(--r-font-weight-bold);
  line-height: 1;
  min-height: 30px;
}

.r-v2-home__stat-label {
  margin-top: var(--r-space-1);
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* Sections */
.r-v2-home__section {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.r-v2-home__section-head {
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
}

.r-v2-home__section-title {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
  font-size: var(--r-font-size-xl);
  font-weight: var(--r-font-weight-semibold);
  margin: 0;
}

.r-v2-home__section-icon {
  color: var(--r-color-brand-primary);
}

.r-v2-home__empty {
  padding: var(--r-space-6);
  color: var(--r-color-fg-muted);
  background: var(--r-color-bg-elevated);
  border: 1px dashed var(--r-color-border);
  border-radius: var(--r-radius-md);
  text-align: center;
}

/* Platforms grid */
.r-v2-home__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--r-space-3);
}

.r-v2-home__platform-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--r-space-2);
  padding: var(--r-space-4);
  background-color: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  color: var(--r-color-fg);
  text-decoration: none;
  text-align: center;
  transition:
    transform var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out),
    box-shadow var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-v2-home__platform-card:hover {
  transform: translateY(-2px);
  border-color: var(--r-color-brand-primary);
  box-shadow: var(--r-elev-3);
}

.r-v2-home__platform-icon {
  width: 64px;
  height: 64px;
  object-fit: contain;
  image-rendering: pixelated;
}

.r-v2-home__platform-name {
  font-weight: var(--r-font-weight-medium);
  font-size: var(--r-font-size-sm);
}

.r-v2-home__platform-count {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
}

/* Collections */
.r-v2-home__collections {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--r-space-3);
}

.r-v2-home__collection-card {
  display: flex;
  gap: var(--r-space-3);
  padding: var(--r-space-3);
  background-color: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  color: var(--r-color-fg);
  text-decoration: none;
  align-items: center;
  transition:
    transform var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-v2-home__collection-card:hover {
  transform: translateY(-2px);
  border-color: var(--r-color-brand-primary);
}

.r-v2-home__collection-cover {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  background: linear-gradient(
    135deg,
    var(--r-color-surface),
    var(--r-color-bg)
  );
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}

.r-v2-home__collection-name {
  font-weight: var(--r-font-weight-medium);
}

.r-v2-home__collection-count {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
  margin-top: 2px;
}
</style>
