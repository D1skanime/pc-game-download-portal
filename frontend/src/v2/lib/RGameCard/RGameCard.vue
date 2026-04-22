<script setup lang="ts">
import { RCover, RPlatformIcon } from "@v2/lib";
import { computed } from "vue";
import type { SimpleRom } from "@/stores/roms";

defineOptions({ inheritAttrs: false });

interface Props {
  rom: SimpleRom;
  to?: string | object;
  selected?: boolean;
  showPlatform?: boolean;
  showTitle?: boolean;
  webp?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  to: undefined,
  showPlatform: true,
  showTitle: true,
  webp: false,
});

const displayTitle = computed(() => props.rom.name || props.rom.fs_name_no_ext);

const coverSrc = computed(() => props.rom.path_cover_large);
const coverFallback = computed(() => props.rom.url_cover);

const platformLabel = computed(
  () => props.rom.platform_custom_name || props.rom.platform_display_name,
);

const href = computed(() => props.to ?? `/rom/${props.rom.id}`);
</script>

<template>
  <router-link
    v-if="typeof href === 'string'"
    :to="href"
    class="r-game-card"
    :class="{ 'r-game-card--selected': selected }"
    :aria-label="displayTitle"
  >
    <div class="r-game-card__cover-wrap">
      <RCover
        :src="coverSrc"
        :fallback-src="coverFallback"
        :alt="displayTitle"
        :placeholder="displayTitle"
        :webp="webp"
      />
      <span
        v-if="rom.regions?.length || rom.languages?.length"
        class="r-game-card__badges"
      >
        <span
          v-for="r in rom.regions"
          :key="`r-${r}`"
          class="r-game-card__badge"
        >
          {{ r }}
        </span>
      </span>
    </div>
    <div v-if="showTitle || showPlatform" class="r-game-card__meta">
      <RPlatformIcon
        v-if="showPlatform"
        :name="rom.platform_slug"
        :alt="platformLabel"
        :size="18"
      />
      <span v-if="showTitle" class="r-game-card__title" :title="displayTitle">
        {{ displayTitle }}
      </span>
    </div>
  </router-link>
</template>

<style scoped>
.r-game-card {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  color: var(--r-color-fg);
  text-decoration: none;
  border-radius: var(--r-radius-md);
  outline: none;
  transition: transform var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-game-card:hover {
  transform: translateY(-3px);
}

.r-game-card--selected .r-game-card__cover-wrap {
  outline: 2px solid var(--r-color-brand-primary);
  outline-offset: 3px;
}

.r-game-card__cover-wrap {
  position: relative;
  border-radius: var(--r-radius-md);
}

.r-game-card__cover-wrap :deep(.r-cover) {
  box-shadow: var(--r-elev-2);
  transition: box-shadow var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-game-card:hover .r-game-card__cover-wrap :deep(.r-cover) {
  box-shadow: var(--r-elev-4);
}

.r-game-card__badges {
  position: absolute;
  top: var(--r-space-2);
  left: var(--r-space-2);
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.r-game-card__badge {
  background: rgba(13, 17, 23, 0.75);
  backdrop-filter: blur(4px);
  color: #fff;
  font-size: 10px;
  font-weight: var(--r-font-weight-semibold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: var(--r-radius-sm);
}

.r-game-card__meta {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
  padding: 0 var(--r-space-1);
  min-width: 0;
}

.r-game-card__title {
  font-size: var(--r-font-size-sm);
  font-weight: var(--r-font-weight-medium);
  line-height: var(--r-line-height-tight);
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  min-width: 0;
  flex: 1;
}
</style>
