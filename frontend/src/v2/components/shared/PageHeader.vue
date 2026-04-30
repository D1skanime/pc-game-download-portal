<script setup lang="ts">
// PageHeader — the top-of-page h1 + optional trailing count.
// Used by every index view (PlatformsIndex, CollectionsIndex, Search,
// Settings — future). Pass `count` for the plain "24" dim-grey span;
// use the `#count` slot when you want a chip or richer content instead.
// Default slot sits at the end of the header (filters, actions, etc.).

defineOptions({ inheritAttrs: false });

withDefaults(
  defineProps<{
    title: string;
    count?: number | string | null;
    /** Render a hairline below the header. Off by default; gallery
     * heroes opt in to match `InfoPanel`'s divider styling. */
    bottomBorder?: boolean;
  }>(),
  { count: null, bottomBorder: false },
);
</script>

<template>
  <header
    v-bind="$attrs"
    class="page-header"
    :class="{ 'page-header--with-border': bottomBorder }"
  >
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
  margin-bottom: 24px;
}

/* Mirrors `InfoPanel`'s divider treatment: hairline + a smaller margin
   below it so successive content (e.g., a gallery toolbar) reads as
   anchored to the header. */
.page-header--with-border {
  padding-bottom: 18px;
  border-bottom: 1px solid var(--r-color-border);
  margin-bottom: 12px;
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
