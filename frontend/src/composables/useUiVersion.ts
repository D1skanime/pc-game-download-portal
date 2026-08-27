import { ref } from "vue";

const uiVersion = ref<"v1" | "v2">("v2");

export function useUiVersion() {
  return uiVersion;
}
