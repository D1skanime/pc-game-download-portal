<script setup lang="ts">
// PlatformTile — platform card used by the Home dashboard row (variant="row",
// 150px fixed) and the /platforms grid (variant="grid"). Feature composite
// around RPlatformIcon; not a design-system primitive.
import { RPlatformIcon } from "@v2/lib";
import { computed } from "vue";

defineOptions({ inheritAttrs: false });

type Variant = "row" | "grid";

interface Props {
  /** Platform slug used to locate /assets/platforms/<slug>.{svg,ico} */
  slug: string;
  /** Filesystem slug (tried first — matches v1's fallback chain). */
  fsSlug?: string;
  displayName: string;
  romCount?: number | null;
  /** Override destination; otherwise derived from `id`. */
  to?: string | object;
  id?: number | string;
  variant?: Variant;
}

const props = withDefaults(defineProps<Props>(), {
  fsSlug: undefined,
  romCount: null,
  to: undefined,
  id: undefined,
  variant: "row",
});

const href = computed(() => props.to ?? `/platform/${props.id ?? ""}`);
</script>

<template>
  <router-link
    :to="href"
    v-bind="$attrs"
    class="plat-tile"
    :class="[`plat-tile--${variant}`]"
  >
    <div class="plat-tile__icon">
      <RPlatformIcon
        :slug="slug"
        :fs-slug="fsSlug"
        :alt="displayName"
        :size="72"
      />
    </div>
    <div class="plat-tile__name">
      {{ displayName }}
    </div>
    <div v-if="romCount != null" class="plat-tile__count">
      {{ romCount }} {{ romCount === 1 ? "game" : "games" }}
    </div>
  </router-link>
</template>

<style scoped>
.plat-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 16px 18px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: var(--r-radius-card);
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  cursor: pointer;
  transition:
    background var(--r-motion-fast),
    border-color var(--r-motion-fast),
    transform var(--r-motion-fast);
}

:global(.r-v2.r-v2-light) .plat-tile {
  background: rgba(17, 17, 23, 0.035);
  border-color: rgba(17, 17, 23, 0.07);
  color: rgba(17, 17, 23, 0.75);
}

.plat-tile:hover {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 255, 255, 0.18);
  transform: translateY(-2px);
}

:global(.r-v2.r-v2-light) .plat-tile:hover {
  background: rgba(17, 17, 23, 0.07);
  border-color: rgba(17, 17, 23, 0.15);
}

.plat-tile--row {
  width: 150px;
  flex-shrink: 0;
}

.plat-tile__icon {
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
}

.plat-tile__icon :deep(.r-platform-icon__img) {
  opacity: 0.9;
  transition: opacity var(--r-motion-fast);
}

.plat-tile:hover .plat-tile__icon :deep(.r-platform-icon__img) {
  opacity: 1;
}

.plat-tile__name {
  font-size: 12px;
  font-weight: var(--r-font-weight-semibold);
  text-align: center;
  line-height: 1.35;
}

.plat-tile__count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
}

:global(.r-v2.r-v2-light) .plat-tile__count {
  color: rgba(17, 17, 23, 0.45);
}

@media (max-width: 768px) {
  .plat-tile--row {
    width: 110px;
  }
  .plat-tile {
    padding: 12px 8px 10px;
    gap: 6px;
  }
  .plat-tile__icon {
    width: 52px;
    height: 52px;
  }
  .plat-tile__name {
    font-size: 10px;
  }
  .plat-tile__count {
    font-size: 9px;
  }
}
</style>
