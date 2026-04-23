<script setup lang="ts">
// CollectionTile — collection card (Home row + /collections grid). Feature
// composite that wraps CollectionMosaic + name + count. `kind` overlays
// "Smart" or "Virtual" badge. `variant` controls sizing ("row" = 150px
// fixed, "grid" = fills cell).
import { computed } from "vue";
import CollectionMosaic from "@/v2/components/Collections/CollectionMosaic.vue";

defineOptions({ inheritAttrs: false });

type Variant = "row" | "grid";
type Kind = "regular" | "virtual" | "smart";

interface Props {
  name: string;
  romCount?: number;
  covers?: (string | null | undefined)[];
  to: string | object;
  variant?: Variant;
  kind?: Kind;
}

const props = withDefaults(defineProps<Props>(), {
  romCount: 0,
  covers: () => [],
  variant: "row",
  kind: "regular",
});

const kindLabel = computed(() =>
  props.kind === "smart" ? "Smart" : props.kind === "virtual" ? "Virtual" : "",
);
</script>

<template>
  <router-link
    :to="to"
    v-bind="$attrs"
    class="coll-tile"
    :class="[`coll-tile--${variant}`]"
  >
    <div class="coll-tile__cover">
      <CollectionMosaic :covers="covers" />
      <span v-if="kindLabel" class="coll-tile__kind">{{ kindLabel }}</span>
    </div>
    <div class="coll-tile__name">
      {{ name }}
    </div>
    <div class="coll-tile__count">
      {{ romCount }} {{ romCount === 1 ? "game" : "games" }}
    </div>
  </router-link>
</template>

<style scoped>
.coll-tile {
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--r-color-fg);
  text-decoration: none;
  cursor: pointer;
}

.coll-tile--row {
  width: 150px;
  flex-shrink: 0;
}

.coll-tile__cover {
  position: relative;
  box-shadow: var(--r-elev-1);
  border-radius: var(--r-radius-lg);
  overflow: hidden;
  transition:
    transform var(--r-motion-fast),
    box-shadow var(--r-motion-fast);
}

.coll-tile:hover .coll-tile__cover {
  transform: translateY(-2px);
  box-shadow: var(--r-elev-2);
}

.coll-tile__kind {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 8px;
  border-radius: var(--r-radius-chip);
  font-size: 10px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  background: rgba(167, 139, 250, 0.85);
  color: #fff;
}

.coll-tile__name {
  font-size: 12.5px;
  font-weight: var(--r-font-weight-semibold);
  color: rgba(255, 255, 255, 0.85);
  padding: 0 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:global(.r-v2.r-v2-light) .coll-tile__name {
  color: rgba(17, 17, 23, 0.85);
}

.coll-tile__count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  padding: 0 2px;
}

:global(.r-v2.r-v2-light) .coll-tile__count {
  color: rgba(17, 17, 23, 0.45);
}

@media (max-width: 768px) {
  .coll-tile--row {
    width: 120px;
  }
}
</style>
