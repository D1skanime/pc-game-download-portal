<script setup lang="ts">
// RMenuHeader — the optional header block used by RomM menus.
//
// Two common patterns covered:
//   * ROM/Game context menu: small cover thumbnail + title + platform
//   * User menu: avatar pill + username + role
//
// The visual is always: left art slot (~38x51 or 30x30 circular), right
// text block with a title + muted subtitle. Slots let callers render any
// avatar/thumbnail shape they want, and any title/subtitle they want.

defineOptions({ inheritAttrs: false });

interface Props {
  title?: string;
  subtitle?: string;
  // `compact` swaps vertical padding for something tighter — use when the
  // art is a small circle (avatar) rather than a portrait thumbnail.
  compact?: boolean;
}

withDefaults(defineProps<Props>(), {
  title: undefined,
  subtitle: undefined,
  compact: false,
});
</script>

<template>
  <div class="r-menu-header" :class="{ 'r-menu-header--compact': compact }">
    <div class="r-menu-header__art">
      <slot name="art" />
    </div>
    <div class="r-menu-header__text">
      <div class="r-menu-header__title">
        <slot name="title">{{ title }}</slot>
      </div>
      <div v-if="$slots.subtitle || subtitle" class="r-menu-header__subtitle">
        <slot name="subtitle">{{ subtitle }}</slot>
      </div>
    </div>
  </div>
</template>

<style scoped>
.r-menu-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px 10px;
  min-width: 0;
}

.r-menu-header--compact {
  padding: 10px 10px 12px;
}

.r-menu-header__art {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.r-menu-header__text {
  min-width: 0;
}

.r-menu-header__title {
  font-size: 12.5px;
  font-weight: var(--r-font-weight-bold);
  color: var(--r-color-fg);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.r-menu-header--compact .r-menu-header__title {
  font-size: 13px;
}

.r-menu-header__subtitle {
  font-size: 11px;
  color: var(--r-color-fg-muted);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.r-menu-header--compact .r-menu-header__subtitle {
  font-size: 10.5px;
  font-weight: var(--r-font-weight-semibold);
  text-transform: capitalize;
}
</style>
