<script setup lang="ts">
// App-wide ROM context menu.
//
// The "floating at click position" popover doesn't fit Vuetify's v-menu
// activator model, so this component owns its own Teleport + positioning.
// The *content* delegates to GameActionsList — the same list that the
// header's MoreMenu renders — so the two menus stay in sync.
import { RMenuHeader, RMenuPanel } from "@v2/lib";
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import type { SimpleRom } from "@/stores/roms";
import GameActionsList from "@/v2/components/GameActions/GameActionsList.vue";

const props = defineProps<{
  open: boolean;
  rom: SimpleRom | null;
  x: number;
  y: number;
}>();

const emit = defineEmits<{
  (e: "update:open", value: boolean): void;
}>();

const menuEl = ref<HTMLElement | null>(null);
const placement = ref<{ top: number; left: number }>({ top: 0, left: 0 });

const thumbUrl = computed(() => {
  const r = props.rom;
  if (!r) return null;
  return r.path_cover_small ?? r.path_cover_large ?? r.url_cover ?? null;
});

const platformLabel = computed(
  () =>
    props.rom?.platform_custom_name || props.rom?.platform_display_name || "",
);

const title = computed(
  () => props.rom?.name || props.rom?.fs_name_no_ext || "",
);

function close() {
  emit("update:open", false);
}

// Clamp the menu into the viewport so it never overflows.
function recomputePosition() {
  if (!menuEl.value) return;
  const box = menuEl.value.getBoundingClientRect();
  const margin = 8;
  let top = props.y;
  let left = props.x;
  const maxLeft = window.innerWidth - box.width - margin;
  const maxTop = window.innerHeight - box.height - margin;
  if (left > maxLeft) left = Math.max(margin, maxLeft);
  if (top > maxTop) top = Math.max(margin, maxTop);
  placement.value = { top, left };
}

watch(
  () => [props.open, props.x, props.y] as const,
  async ([open]) => {
    if (!open) return;
    placement.value = { top: props.y, left: props.x };
    await nextTick();
    recomputePosition();
  },
);

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && props.open) {
    e.preventDefault();
    close();
  }
}
function onResize() {
  if (props.open) recomputePosition();
}
window.addEventListener("keydown", onKeydown);
window.addEventListener("resize", onResize);
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown);
  window.removeEventListener("resize", onResize);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="r-v2-ctx-scrim"
      aria-hidden="true"
      @click="close"
      @contextmenu.prevent="close"
    />

    <Transition name="r-v2-ctx">
      <div
        v-if="open && rom"
        ref="menuEl"
        role="menu"
        class="r-v2-ctx-wrap"
        :style="{ top: `${placement.top}px`, left: `${placement.left}px` }"
        @click.stop
      >
        <RMenuPanel>
          <RMenuHeader :title="title" :subtitle="platformLabel">
            <template #art>
              <img
                v-if="thumbUrl"
                :src="thumbUrl"
                :alt="title"
                class="r-v2-ctx__thumb"
              />
              <div v-else class="r-v2-ctx__thumb r-v2-ctx__thumb--empty">
                <i class="mdi mdi-play" aria-hidden="true" />
              </div>
            </template>
          </RMenuHeader>

          <GameActionsList :rom="rom" @close="close" />
        </RMenuPanel>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.r-v2-ctx-scrim {
  position: fixed;
  inset: 0;
  z-index: 3500;
  background: transparent;
}

.r-v2-ctx-wrap {
  position: fixed;
  z-index: 3501;
}

.r-v2-ctx__thumb {
  width: 38px;
  height: 51px;
  border-radius: 5px;
  object-fit: cover;
  background: rgba(255, 255, 255, 0.06);
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.3);
}

.r-v2-ctx__thumb--empty .mdi {
  font-size: 20px;
  line-height: 1;
}

/* Enter/leave animation */
.r-v2-ctx-enter-active,
.r-v2-ctx-leave-active {
  transition:
    opacity var(--r-motion-fast) ease,
    transform var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-ctx-enter-from,
.r-v2-ctx-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

@media (prefers-reduced-motion: reduce) {
  .r-v2-ctx-enter-active,
  .r-v2-ctx-leave-active {
    transition: opacity var(--r-motion-fast) ease;
  }
  .r-v2-ctx-enter-from,
  .r-v2-ctx-leave-to {
    transform: none;
  }
}
</style>
