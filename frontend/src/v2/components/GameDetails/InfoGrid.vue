<script setup lang="ts">
// InfoGrid — two-column labeled-chip grid used in the Overview tab.
// Each section has an uppercase eyebrow label and a row of small chips
// (genres, developer, franchise, collections). Sections with no items
// are omitted so the grid doesn't show empty columns.

defineOptions({ inheritAttrs: false });

export type InfoGridSection = {
  label: string;
  items: string[];
};

const props = defineProps<{ sections: InfoGridSection[] }>();

const visible = () => props.sections.filter((s) => s.items.length > 0);
</script>

<template>
  <div v-if="visible().length" class="r-v2-det-infogrid">
    <div
      v-for="section in visible()"
      :key="section.label"
      class="r-v2-det-infogrid__item"
    >
      <div class="r-v2-det-infogrid__label">
        {{ section.label }}
      </div>
      <div class="r-v2-det-infogrid__chips">
        <span
          v-for="item in section.items"
          :key="item"
          class="r-v2-det-infogrid__chip"
        >
          {{ item }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Auto-fill grid spanning the whole details body — sections reflow to a
   new row when the column would shrink below 240px. Mirrors the
   responsive pattern used by ProviderGrid in the Metadata tab so both
   surfaces feel like siblings. */
.r-v2-det-infogrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 18px 24px;
  margin: 18px 0 22px;
  width: 100%;
}

.r-v2-det-infogrid__label {
  font-size: 10.5px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
  margin-bottom: 6px;
}

.r-v2-det-infogrid__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.r-v2-det-infogrid__chip {
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border-strong);
  border-radius: var(--r-radius-chip);
  padding: 3px 9px;
  font-size: 11.5px;
  color: var(--r-color-fg-secondary);
}
</style>
