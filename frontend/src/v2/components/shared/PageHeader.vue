<script setup lang="ts">
// PageHeader — the top-of-page h1 + optional trailing count.
// Used by every index view (PlatformsIndex, CollectionsIndex, Search,
// Settings — future). Pass `count` for the plain "24" dim-grey span;
// use the `#count` slot when you want a chip or richer content instead.
// Default slot sits at the end of the header (filters, actions, etc.).
//
// No divider here — when used as a gallery hero (Search), the gallery
// shell paints the divider between hero and toolbar so the three
// gallery views (Platform / Collection / Search) share one separator
// regardless of which header sits above it.

defineOptions({ inheritAttrs: false });

withDefaults(
  defineProps<{
    title: string;
    count?: number | string | null;
  }>(),
  { count: null },
);
</script>

<template>
  <header v-bind="$attrs" class="page-header">
    <div class="page-header__title-wrap">
      <h1 class="page-header__title">
        {{ title }}
      </h1>
      <slot name="count">
        <span v-if="count != null" class="page-header__count">{{ count }}</span>
      </slot>
    </div>
    <slot />
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: baseline;
  gap: var(--r-space-3);
  /* Breathing below the title is `padding-bottom` (not margin) so it
     counts in `getBoundingClientRect().height` — the gallery shell
     auto-measures the hero slot to position the toolbar's divider, and
     a margin-bottom would collapse out of that measurement. Visually
     identical for non-gallery consumers (PlatformsIndex etc). */
  padding-bottom: 24px;
}

.page-header__title-wrap {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-header__title {
  font-size: var(--r-font-size-3xl);
  font-weight: var(--r-font-weight-extrabold);
  letter-spacing: -0.025em;
  color: var(--r-color-fg);
  margin: 0;
  line-height: var(--r-line-height-tight);
}

.page-header__count {
  font-size: var(--r-font-size-md);
  color: var(--r-color-fg-muted);
}
</style>
