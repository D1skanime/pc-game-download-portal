<script setup lang="ts">
// AlphaStrip — A-Z-# jump sidebar for letter-grouped grids (Platform and
// Collection gallery). Feature composite — not a design-system primitive.
import { computed } from "vue";

defineOptions({ inheritAttrs: false });

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#".split("");

interface Props {
  available?: Set<string> | string[];
  current?: string;
}

const props = withDefaults(defineProps<Props>(), {
  available: () => new Set<string>(),
  current: "",
});

defineEmits<{
  (e: "pick", letter: string): void;
}>();

const availableSet = computed(() => {
  const a = props.available;
  return a instanceof Set ? a : new Set(a);
});
</script>

<template>
  <aside class="alpha-strip" aria-label="Jump to letter">
    <button
      v-for="l in ALPHABET"
      :key="l"
      type="button"
      class="alpha-strip__btn"
      :class="{
        'alpha-strip__btn--has': availableSet.has(l),
        'alpha-strip__btn--current': current === l,
      }"
      :disabled="!availableSet.has(l)"
      :aria-label="`Jump to ${l}`"
      @click="availableSet.has(l) && $emit('pick', l)"
    >
      {{ l }}
    </button>
  </aside>
</template>

<style scoped>
.alpha-strip {
  width: 24px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 0;
  user-select: none;
}

.alpha-strip__btn {
  appearance: none;
  background: transparent;
  border: 0;
  font-family: inherit;
  font-size: 10px;
  font-weight: var(--r-font-weight-bold);
  color: rgba(255, 255, 255, 0.14);
  cursor: default;
  line-height: 1;
  padding: 2.5px 0;
  width: 100%;
  text-align: center;
  border-radius: 3px;
  transition:
    color 0.1s,
    background 0.1s;
}

.alpha-strip__btn--has {
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
}
.alpha-strip__btn--has:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.alpha-strip__btn--current {
  color: #fff !important;
  background: rgba(255, 255, 255, 0.15);
}

@media (max-width: 768px) {
  .alpha-strip {
    width: 16px;
  }
  .alpha-strip__btn {
    font-size: 7px;
    padding: 1px 0;
  }
}
</style>
