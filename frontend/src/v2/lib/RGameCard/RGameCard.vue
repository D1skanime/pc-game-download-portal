<script setup lang="ts">
// RGameCard — portrait game cover with hover overlay.
//
// Shape adapted from the artist mockup:
//   * 158×213 card art, 8px radius
//   * Platform badge bottom-left, rating badge top-right (both appear on hover)
//   * Hover overlay: info (TL) · play (center) · action row (BL: download,
//     bookmark, favorite, more)
//   * Label below the card, 11.5px, truncated
//   * Optional `hero` variant: 300×169 (16:9) + larger multi-line label
//
// All state is owned by the parent — this component is presentational.
// Emits actions so Home/Gallery can wire favourite/download/bookmark.
import { computed, ref } from "vue";
import type { SimpleRom } from "@/stores/roms";
import MoreMenu from "@/v2/components/GameActions/MoreMenu.vue";
import { useBackgroundArt } from "@/v2/composables/useBackgroundArt";
import RIcon from "@/v2/lib/RIcon/RIcon.vue";

defineOptions({ inheritAttrs: false });

interface Props {
  rom: SimpleRom;
  to?: string;
  hero?: boolean;
  focused?: boolean;
  isFavorite?: boolean;
  isBookmarked?: boolean;
  webp?: boolean;
  showPlatformBadge?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  to: undefined,
  showPlatformBadge: true,
});

type CardAction = "play" | "download" | "bookmark" | "favorite" | "info";

const emit = defineEmits<{
  (e: CardAction, rom: SimpleRom): void;
}>();

const EXTENSION_REGEX = /\.(png|jpg|jpeg)$/i;

const imgError = ref(false);
const imgLoaded = ref(false);

const coverUrl = computed(() => {
  const path = props.rom.path_cover_large ?? props.rom.path_cover_small ?? null;
  if (!path) return null;
  return props.webp ? path.replace(EXTENSION_REGEX, ".webp") : path;
});

const fallbackUrl = computed(() => props.rom.url_cover ?? null);
const showFallback = computed(() => imgError.value && !!fallbackUrl.value);

const title = computed(() => props.rom.name || props.rom.fs_name_no_ext);
const platformShort = computed(
  () => props.rom.platform_custom_name || props.rom.platform_display_name,
);

const href = computed(() => props.to ?? `/rom/${props.rom.id}`);

const setBgArt = useBackgroundArt();
function onMouseEnter() {
  if (coverUrl.value) setBgArt(coverUrl.value);
  else if (fallbackUrl.value) setBgArt(fallbackUrl.value);
}

function handle(eventName: CardAction, e: MouseEvent) {
  e.preventDefault();
  e.stopPropagation();
  emit(eventName, props.rom);
}

const ratingLabel = computed(() => {
  const r = props.rom.rom_user?.rating;
  return r && r > 0 ? r.toString() : null;
});
</script>

<template>
  <router-link
    :to="href"
    class="r-gc"
    :class="{ 'r-gc--hero': hero, 'r-gc--focused': focused }"
    :aria-label="title"
    @mouseenter="onMouseEnter"
  >
    <div class="r-gc__art" :class="{ 'r-v2-shimmer': !imgLoaded && !imgError }">
      <img
        v-if="(coverUrl || fallbackUrl) && !(imgError && !fallbackUrl)"
        :src="
          showFallback ? (fallbackUrl ?? undefined) : (coverUrl ?? undefined)
        "
        :alt="title"
        loading="lazy"
        @load="imgLoaded = true"
        @error="imgError = true"
      />
      <div v-else class="r-gc__placeholder">
        {{ title }}
      </div>

      <div v-if="showPlatformBadge" class="r-gc__badge">
        {{ platformShort }}
      </div>

      <div v-if="ratingLabel" class="r-gc__rating">★ {{ ratingLabel }}</div>

      <!-- Hover overlay -->
      <div class="r-gc__overlay">
        <div class="r-gc__overlay-top">
          <button
            type="button"
            class="r-gc__info-btn"
            aria-label="More info"
            @click="(e) => handle('info', e)"
          >
            <RIcon icon="mdi-information-outline" size="18" />
          </button>
        </div>

        <div class="r-gc__overlay-center">
          <button
            type="button"
            class="r-gc__play-btn"
            aria-label="Play"
            @click="(e) => handle('play', e)"
          >
            <RIcon icon="mdi-play" size="24" />
          </button>
        </div>

        <div class="r-gc__overlay-bottom">
          <button
            type="button"
            class="r-gc__action-btn"
            aria-label="Download"
            @click="(e) => handle('download', e)"
          >
            <RIcon icon="mdi-download-outline" size="18" />
          </button>
          <button
            type="button"
            class="r-gc__action-btn"
            :class="{ 'r-gc__action-btn--on-accent': isBookmarked }"
            aria-label="Add to collection"
            @click="(e) => handle('bookmark', e)"
          >
            <RIcon
              :icon="isBookmarked ? 'mdi-bookmark' : 'mdi-bookmark-outline'"
              size="18"
            />
          </button>
          <button
            type="button"
            class="r-gc__action-btn"
            :class="{ 'r-gc__action-btn--on-fav': isFavorite }"
            aria-label="Favorite"
            @click="(e) => handle('favorite', e)"
          >
            <RIcon
              :icon="isFavorite ? 'mdi-heart' : 'mdi-heart-outline'"
              size="18"
            />
          </button>
          <MoreMenu :rom="rom">
            <template #activator="{ props: activatorProps }">
              <button
                v-bind="activatorProps"
                type="button"
                class="r-gc__action-btn"
                aria-label="More actions"
                @click.prevent.stop
              >
                <RIcon icon="mdi-dots-horizontal" size="18" />
              </button>
            </template>
          </MoreMenu>
        </div>
      </div>
    </div>
    <div class="r-gc__label">
      {{ title }}
    </div>
  </router-link>
</template>

<style scoped>
.r-gc {
  flex-shrink: 0;
  cursor: pointer;
  position: relative;
  outline: none;
  width: var(--r-card-art-w);
  text-decoration: none;
  color: var(--r-color-fg);
}

.r-gc__art {
  width: var(--r-card-art-w);
  height: var(--r-card-art-h);
  border-radius: var(--r-radius-art);
  overflow: hidden;
  position: relative;
  background: #1a1a2e;
  outline: 2.5px solid transparent;
  outline-offset: 3px;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.r-gc__art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.r-gc__placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  text-align: center;
  font-size: 11px;
  font-weight: var(--r-font-weight-semibold);
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.5);
}

/* ── Hover overlay ─────────────────────────────────────────── */
.r-gc__overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.45) 0%,
    rgba(0, 0, 0, 0.1) 35%,
    rgba(0, 0, 0, 0.1) 55%,
    rgba(0, 0, 0, 0.6) 100%
  );
  opacity: 0;
  transition: opacity 0.12s ease;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 8px;
  border-radius: var(--r-radius-art);
}

.r-gc__overlay-top {
  display: flex;
  justify-content: flex-end;
}
.r-gc__overlay-center {
  display: flex;
  justify-content: center;
  align-items: center;
}
.r-gc__overlay-bottom {
  display: flex;
  justify-content: space-around;
  align-items: center;
}

.r-gc__play-btn {
  appearance: none;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  border: 2px solid rgba(255, 255, 255, 0.65);
  display: grid;
  place-items: center;
  cursor: pointer;
  color: #fff;
  transition:
    background 0.15s,
    transform 0.15s;
}
.r-gc__play-btn :deep(.mdi) {
  margin-left: 3px;
}
.r-gc__play-btn:hover {
  background: rgba(255, 255, 255, 0.38);
  transform: scale(1.1);
}

.r-gc__action-btn {
  appearance: none;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition:
    background 0.15s,
    color 0.15s;
}
.r-gc__action-btn:hover {
  background: rgba(255, 255, 255, 0.22);
}
.r-gc__action-btn--on-fav {
  color: var(--r-color-fav);
}
.r-gc__action-btn--on-accent {
  color: var(--r-color-brand-accent);
}

.r-gc__info-btn {
  appearance: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  display: grid;
  place-items: center;
  cursor: pointer;
}

/* Platform badge */
.r-gc__badge {
  position: absolute;
  bottom: 7px;
  left: 7px;
  background: rgba(0, 0, 0, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--r-radius-sm);
  padding: 2px 6px;
  font-size: 9.5px;
  font-weight: var(--r-font-weight-semibold);
  letter-spacing: 0.03em;
  color: rgba(255, 255, 255, 0.85);
  opacity: 0;
  transition: opacity 0.12s ease;
  max-width: calc(100% - 14px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.r-gc__rating {
  position: absolute;
  top: 7px;
  right: 7px;
  background: rgba(0, 0, 0, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--r-radius-sm);
  padding: 2px 6px;
  font-size: 9.5px;
  font-weight: var(--r-font-weight-bold);
  color: var(--r-color-romm-gold);
  opacity: 0;
  transition: opacity 0.12s ease;
}

.r-gc:hover .r-gc__art,
.r-gc--focused .r-gc__art {
  transform: scale(1.05);
  box-shadow: var(--r-elev-3);
}
.r-gc:hover .r-gc__overlay,
.r-gc--focused .r-gc__overlay {
  opacity: 1;
}
.r-gc:hover .r-gc__badge,
.r-gc--focused .r-gc__badge,
.r-gc:hover .r-gc__rating,
.r-gc--focused .r-gc__rating {
  opacity: 1;
}

.r-gc__label {
  margin-top: 7px;
  font-size: 11.5px;
  color: rgba(255, 255, 255, 0.55);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.18s;
  padding: 0 1px;
  text-align: center;
}
.r-gc:hover .r-gc__label,
.r-gc--focused .r-gc__label {
  color: rgba(255, 255, 255, 0.9);
}

/* ── Hero (16:9) variant ──────────────────────────────────── */
.r-gc--hero {
  width: var(--r-hero-w);
}
.r-gc--hero .r-gc__art {
  width: var(--r-hero-w);
  height: var(--r-hero-h);
  border-radius: var(--r-radius-lg);
}
.r-gc--hero .r-gc__overlay {
  border-radius: var(--r-radius-lg);
}
.r-gc--hero .r-gc__label {
  font-size: 13px;
  font-weight: var(--r-font-weight-semibold);
  max-width: var(--r-hero-w);
  white-space: normal;
  text-align: center;
  text-overflow: unset;
}

/* Mobile */
@media (max-width: 768px) {
  .r-gc {
    width: 130px;
  }
  .r-gc__art {
    width: 130px;
    height: 175px;
  }
  .r-gc--hero {
    width: 220px;
  }
  .r-gc--hero .r-gc__art {
    width: 220px;
    height: 124px;
  }
  .r-gc__label {
    font-size: 11px;
  }
  /* Actions always visible on touch (no hover) */
  .r-gc__overlay-bottom {
    opacity: 1;
  }
}
</style>
