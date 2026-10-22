import { shallowRef } from "vue";
import { normalizeLocale } from "@/v2/composables/useProviderResolution";

interface MatchLanguageCapture {
  readonly generation: number;
  readonly metadataLocale: string;
}

export function useMetadataMatchLanguage() {
  let generation = 0;
  const accepted = shallowRef<MatchLanguageCapture | null>(null);

  function reset() {
    generation += 1;
    accepted.value = null;
  }

  function begin(locale?: string | null): MatchLanguageCapture {
    reset();
    return Object.freeze({
      generation,
      metadataLocale: normalizeLocale(locale?.trim() || "en"),
    });
  }

  function isCurrent(capture: MatchLanguageCapture): boolean {
    return capture.generation === generation;
  }

  function accept(capture: MatchLanguageCapture): boolean {
    if (!isCurrent(capture)) return false;
    accepted.value = capture;
    return true;
  }

  return { accepted, begin, accept, isCurrent, reset };
}
