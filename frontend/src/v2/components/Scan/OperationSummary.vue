<script setup lang="ts">
import { RAlert } from "@v2/lib";
import { computed } from "vue";
import type { OperationRequest, OperationResult } from "@/v2/data/contracts";

const props = defineProps<{
  request: OperationRequest;
  result?: OperationResult | null;
}>();

const providerText = computed(
  () =>
    [
      ...props.request.providerPolicy.providers,
      ...props.request.providerPolicy.fallbackProviders,
    ].join(", ") || "none",
);

const impactText = computed(() => {
  const result = props.result;
  if (!result?.impact) return "Impact preview pending";
  return [
    result.impact.scope,
    result.impact.metadataMode + " metadata",
    result.impact.mediaMode + " media",
  ].join(", ");
});

const summaryText = computed(() =>
  [
    "Scope: " + props.request.scope.kind,
    "Providers: " + providerText.value,
    "Locale: " + props.request.metadataLocale,
    "Region: " + (props.request.providerPolicy.region ?? "default"),
    "Impact: " + impactText.value,
  ].join(" | "),
);
</script>

<template>
  <RAlert type="info" variant="outlined" :text="summaryText" />
</template>
