<script setup lang="ts">
// GameCard — portrait game cover with hover overlay.
//
// Feature composite (not a lib primitive): depends on SimpleRom,
// useGameActions (via GameActionBtn), useBackgroundArt, and the store
// layer. Lives under `src/v2/components/Gallery/` instead of `lib/` for
// that reason — the library is reserved for truly generic primitives
// that a Storybook reader can drop into a page without wiring stores or
// a router.
//
// Shape adapted from the artist mockup:
//   * 158×213 card art, 8px radius
//   * Rating badge top-right (appear on hover)
//   * Platform icon (TR, always visible): semi-transparent circle with the
//     platform's icon — toggle via `showPlatformIcon`.
//   * Hover overlay: play (center) · action row (BL: download, collection,
//     favorite, more) — action buttons are the shared GameActionBtn atom
//     so the card and the GameDetails header stay visually + behaviourally
//     in sync.
//   * Label below the card, 11.5px, truncated
//   * Optional `hero` variant: 300×169 (16:9) + larger multi-line label
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import type { SimpleRom } from "@/stores/roms";
import StatusBadge from "@/v2/components/Gallery/GameCard/StatusBadge.vue";
import GameActionBtn from "@/v2/components/GameActions/GameActionBtn.vue";
import { useBackgroundArt } from "@/v2/composables/useBackgroundArt";
import {
  pendingMorphName,
  useViewTransition,
} from "@/v2/composables/useViewTransition";
import RPlatformIcon from "@/v2/lib/media/RPlatformIcon/RPlatformIcon.vue";
import RBtn from "@/v2/lib/primitives/RBtn/RBtn.vue";

defineOptions({ inheritAttrs: false });

interface Props {
  rom: SimpleRom;
  to?: string;
  hero?: boolean;
  focused?: boolean;
  webp?: boolean;
  showPlatformIcon?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  to: undefined,
  showPlatformIcon: true,
});

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
// Same handler fires on hover AND focus so keyboard/gamepad users get
// the background cross-fade to the focused cover — mirrors what mouse
// users see when they rest a pointer on the card.
function onHighlight() {
  if (coverUrl.value) setBgArt(coverUrl.value);
  else if (fallbackUrl.value) setBgArt(fallbackUrl.value);
}

const ratingLabel = computed(() => {
  const r = props.rom.rom_user?.rating;
  return r && r > 0 ? r.toString() : null;
});

// Shared-element morph: when the user clicks through to GameDetails, tag
// the card art so the browser pairs it with the destination cover and
// animates between them. Modifier keys / middle-click fall through to
// the regular router-link behaviour so opening in a new tab still works.
const router = useRouter();
const artEl = ref<HTMLElement | null>(null);
const { morphTransition } = useViewTransition();

// Stop propagation so the card's morph + router push doesn't fire when
// the user actually wanted to jump to the platform gallery.
function onPlatformClick(e: MouseEvent) {
  e.preventDefault();
  e.stopPropagation();
  router.push(`/platform/${props.rom.platform_id}`);
}

function onCardClick(e: MouseEvent) {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) {
    return;
  }
  if (!artEl.value) return;
  e.preventDefault();
  morphTransition(
    { el: artEl.value, name: `rom-cover-${props.rom.id}` },
    async () => {
      await router.push(href.value);
    },
  );
}

// Reverse-morph tag: when GameDetails is leaving (BackBtn / navbar /
// browser back), `pendingMorphName` is set and we paint the matching
// view-transition-name on the destination card so the browser can pair
// it with the GameDetails cover.
const morphStyle = computed(() => {
  const name = `rom-cover-${props.rom.id}`;
  return pendingMorphName.value === name
    ? { viewTransitionName: name }
    : undefined;
});
</script>

<template>
  <router-link
    :to="href"
    class="r-gc"
    :class="{ 'r-gc--hero': hero, 'r-gc--focused': focused }"
    :aria-label="title"
    :data-rom-id="rom.id"
    @click="onCardClick"
    @mouseenter="onHighlight"
    @focus="onHighlight"
  >
    <div
      ref="artEl"
      class="r-gc__art"
      :class="{ 'r-v2-shimmer': !imgLoaded && !imgError }"
      :style="morphStyle"
    >
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

      <div v-if="ratingLabel" class="r-gc__rating">★ {{ ratingLabel }}</div>

      <RBtn
        v-if="showPlatformIcon"
        icon
        size="x-small"
        variant="text"
        :ripple="false"
        class="r-gc__platform-icon"
        :aria-label="`Browse ${platformShort}`"
        @click="onPlatformClick"
      >
        <RPlatformIcon
          :slug="rom.platform_slug"
          :fs-slug="rom.platform_fs_slug"
          :alt="platformShort"
          :size="18"
        />
      </RBtn>

      <StatusBadge :rom="rom" />

      <!-- Hover overlay — action buttons are the shared GameActionBtn. -->
      <div class="r-gc__overlay">
        <div class="r-gc__overlay-center">
          <GameActionBtn
            :rom="rom"
            action="play"
            size="md"
            variant="emphasized"
          />
        </div>

        <div class="r-gc__overlay-bottom">
          <GameActionBtn :rom="rom" action="download" size="sm" />
          <GameActionBtn :rom="rom" action="collection" size="sm" />
          <GameActionBtn :rom="rom" action="favorite" size="sm" />
          <GameActionBtn :rom="rom" action="more" size="sm" />
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
  padding: 8px;
  border-radius: var(--r-radius-art);
}

.r-gc__overlay-center {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}
.r-gc__overlay-bottom {
  display: flex;
  justify-content: space-around;
  align-items: center;
}

/* Top-right always-visible platform icon. Sits on the cover (outside the
   hover overlay) so it stays readable at rest. Click navigates to the
   platform gallery; tooltip shows the full platform name.
   `z-index` keeps the button above `.r-gc__overlay`, which would
   otherwise eat clicks because it covers the full art via `inset: 0`. */
.r-gc__platform-icon {
  position: absolute !important;
  top: 7px;
  right: 7px;
  z-index: 2;
  width: 28px !important;
  height: 28px !important;
  min-width: 28px !important;
  min-height: 28px !important;
  border-radius: 50% !important;
  background: rgba(0, 0, 0, 0.78) !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  color: #fff !important;
  transition:
    background 0.12s ease,
    border-color 0.12s ease,
    transform 0.12s ease;
}
.r-gc__platform-icon:hover {
  background: rgba(0, 0, 0, 0.9) !important;
  border-color: rgba(255, 255, 255, 0.25) !important;
  transform: scale(1.08);
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
  top: 11px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.78);
  border: 1px solid var(--r-color-romm-gold);
  border-radius: var(--r-radius-sm);
  padding: 2px 6px;
  font-size: 9.5px;
  font-weight: var(--r-font-weight-bold);
  color: var(--r-color-romm-gold);
  opacity: 0;
  transition: opacity 0.12s ease;
}

.r-gc:hover .r-gc__art,
.r-gc:focus-visible .r-gc__art,
.r-gc--focused .r-gc__art {
  transform: scale(1.05);
  box-shadow: var(--r-elev-3);
}
.r-gc:hover .r-gc__overlay,
.r-gc:focus-visible .r-gc__overlay,
.r-gc--focused .r-gc__overlay {
  opacity: 1;
}
.r-gc:hover .r-gc__badge,
.r-gc:focus-visible .r-gc__badge,
.r-gc--focused .r-gc__badge,
.r-gc:hover .r-gc__rating,
.r-gc:focus-visible .r-gc__rating,
.r-gc--focused .r-gc__rating {
  opacity: 1;
}
.r-gc:hover :deep(.r-gc-status),
.r-gc:focus-visible :deep(.r-gc-status),
.r-gc--focused :deep(.r-gc-status) {
  opacity: 1;
}

/* Keyboard / gamepad focus — paint the outline in the brand colour and
   stack a drop-shadow + outer bloom on top so the focused card reads
   distinctly from hover. Mirrors the v1 console GameCard pattern. */
.r-gc:focus-visible {
  outline: none;
}
.r-gc:focus-visible .r-gc__art {
  outline-color: var(--r-color-brand-primary);
  box-shadow:
    0 8px 28px rgba(0, 0, 0, 0.4),
    0 0 0 2px var(--r-color-brand-primary),
    0 0 18px rgba(139, 116, 232, 0.6);
}

.r-gc__label {
  margin-top: 7px;
  font-size: 11.5px;
  color: var(--r-color-fg-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.18s;
  padding: 0 1px;
  text-align: center;
}
.r-gc:hover .r-gc__label,
.r-gc:focus-visible .r-gc__label,
.r-gc--focused .r-gc__label {
  color: var(--r-color-fg);
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
