<script setup lang="ts">
// PairDispatcher preserves the public /pair route while v2 owns the page.
// Keeping the small route component avoids a router special case and leaves
// the pairing client contract unchanged.
import PairShell from "@/v2/views/PairShell.vue";
</script>

<template>
  <PairShell />
</template>
