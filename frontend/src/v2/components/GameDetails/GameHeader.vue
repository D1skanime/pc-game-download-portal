<script setup lang="ts">
// GameHeader — right-column header for the details view.
// Five rows, top to bottom:
//   1. Title
//   2. Meta (year · platform · players · age-rating · verified)
//   3. Metadata provider chips
//   4. Tag chips (tags + regions + languages)
//   5. GameActions (Play · Download · Favorite · Share · More)
//
// Pure presentation — the action row owns its own state/handlers via the
// GameActions component (which uses the shared useGameActions composable).
import { RIcon } from "@v2/lib";
import type { DetailedRom } from "@/stores/roms";
import GameActions from "@/v2/components/GameActions/GameActions.vue";
import MetadataProviderChips from "@/v2/components/GameDetails/MetadataProviderChips.vue";

defineOptions({ inheritAttrs: false });

defineProps<{
  rom: DetailedRom;
  title: string;
  platformLabel: string;
  releaseYear: number | null;
  playerCount: string | null;
  ageRatings: string[];
  verified: boolean;
  genres: string[];
  franchises: string[];
  regions: string[];
  languages: string[];
  canPlay: boolean;
}>();
</script>

<template>
  <div class="r-v2-det-header">
    <h1 class="r-v2-det-header__title">
      {{ title }}
    </h1>

    <div class="r-v2-det-header__meta">
      <span v-if="releaseYear">{{ releaseYear }}</span>
      <span v-if="releaseYear && platformLabel" class="r-v2-det-header__sep">
        ·
      </span>
      <span>{{ platformLabel }}</span>
      <template v-if="playerCount">
        <span class="r-v2-det-header__sep">·</span>
        <span>{{ playerCount }}</span>
      </template>
      <template v-if="ageRatings.length">
        <span class="r-v2-det-header__sep">·</span>
        <span>{{ ageRatings.join(", ") }}</span>
      </template>
      <template v-if="verified">
        <span class="r-v2-det-header__sep">·</span>
        <span class="r-v2-det-header__verified">
          <RIcon icon="mdi-check-decagram" size="14" />
          Verified
        </span>
      </template>
    </div>

    <MetadataProviderChips :rom="rom" />

    <div
      v-if="
        genres.length || franchises.length || regions.length || languages.length
      "
      class="r-v2-det-header__tags"
    >
      <span v-for="g in genres" :key="`g-${g}`" class="r-v2-det-header__tag">
        {{ g }}
      </span>
      <span
        v-for="f in franchises"
        :key="`f-${f}`"
        class="r-v2-det-header__tag"
      >
        {{ f }}
      </span>
      <span
        v-for="r in regions"
        :key="`r-${r}`"
        class="r-v2-det-header__tag r-v2-det-header__tag--region"
      >
        {{ r }}
      </span>
      <span
        v-for="l in languages"
        :key="`l-${l}`"
        class="r-v2-det-header__tag r-v2-det-header__tag--lang"
      >
        {{ l }}
      </span>
    </div>

    <GameActions :rom="rom" :can-play="canPlay" />
  </div>
</template>

<style scoped>
.r-v2-det-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 24px;
}

.r-v2-det-header__title {
  font-size: var(--r-font-size-4xl);
  font-weight: var(--r-font-weight-extrabold);
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin: 0 0 2px 0;
  text-shadow: 0 2px 20px rgba(0, 0, 0, 0.5);
}

.r-v2-det-header__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 13.5px;
  color: var(--r-color-fg-secondary);
}
.r-v2-det-header__sep {
  opacity: 0.3;
}
.r-v2-det-header__verified {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--r-color-success);
  font-weight: var(--r-font-weight-semibold);
  font-size: 12.5px;
}

.r-v2-det-header__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.r-v2-det-header__tag {
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border-strong);
  border-radius: var(--r-radius-chip);
  padding: 2px 9px;
  font-size: 11.5px;
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg-secondary);
}
.r-v2-det-header__tag--region {
  border-color: rgba(96, 165, 250, 0.4);
  color: rgba(147, 197, 253, 0.9);
}
.r-v2-det-header__tag--lang {
  border-color: rgba(167, 139, 250, 0.4);
  color: rgba(196, 181, 253, 0.9);
}

@media (max-width: 768px) {
  .r-v2-det-header__title {
    font-size: 20px;
  }
}
</style>
