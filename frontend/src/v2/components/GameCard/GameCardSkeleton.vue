<script setup lang="ts">
// GameCardSkeleton — placeholder rendered for un-fetched gallery slots.
// Geometry mirrors GameCard exactly (art 158×213, 7px gap, ~16px label
// line) so the v-virtual-scroll's measurements stay stable when a window
// fetch resolves and skeletons swap for real cards — without that match
// the virtualiser re-measures total height and the scroll position
// jitters on every fetch.
import { RSkeletonBlock } from "@v2/lib";
</script>

<template>
  <div class="r-gcs">
    <RSkeletonBlock
      class="r-gcs__art"
      width="var(--r-card-art-w)"
      height="var(--r-card-art-h)"
      rounded="md"
    />
    <RSkeletonBlock class="r-gcs__label" width="60%" :height="11" />
  </div>
</template>

<style scoped>
.r-gcs {
  width: var(--r-card-art-w);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.r-gcs__art {
  width: var(--r-card-art-w);
  height: var(--r-card-art-h);
}
.r-gcs__label {
  /* Match GameCard's `.r-gc__label`: margin-top 7px, font-size 11.5px,
     line-height ~16px → reserve ~16px so total card+label height lines
     up to the same number of pixels regardless of which slot kind
     renders. */
  margin-top: 7px !important;
  height: 16px;
}

@media (max-width: 768px) {
  .r-gcs {
    width: 130px;
  }
  .r-gcs__art {
    width: 130px;
    height: 175px;
  }
}
</style>
