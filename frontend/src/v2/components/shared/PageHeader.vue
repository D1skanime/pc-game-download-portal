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
  margin-bottom: 24px;
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
  color: #fff;
  margin: 0;
  line-height: var(--r-line-height-tight);
}

:global(.r-v2.r-v2-light) .page-header__title {
  color: var(--r-color-fg);
}

.page-header__count {
  font-size: var(--r-font-size-md);
  color: rgba(255, 255, 255, 0.4);
}
</style>
