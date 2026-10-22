import { useLocalStorage } from "@vueuse/core";
import { computed, ref, watch, type ComputedRef } from "vue";
import { useI18n } from "vue-i18n";
import { normalizeLocale } from "@/v2/composables/useProviderResolution";
import { useSystemLanguage } from "@/v2/composables/useSystemLanguage";
import storeHeartbeat, {
  type MetadataOption,
} from "@/v2/data/adapters/legacy/stores/heartbeat";

export interface HashMatcher {
  value: "hasheous" | "playmatch";
  name: string;
  logo: string;
  /** Reason the switch is forced off, surfaced in the hover tooltip.
   *  null when the switch is interactable. */
  blockedReason: string | null;
  switchEnabled: boolean;
}

export function useScanProviders(calculateHashes: ComputedRef<boolean>) {
  const { t, locale } = useI18n();
  const heartbeat = storeHeartbeat();
  const LOCAL_STORAGE_METADATA_SOURCES_KEY = "scan.metadataSources";
  const LOCAL_STORAGE_LAUNCHBOX_REMOTE_ENABLED_KEY =
    "scan.launchboxRemoteEnabled";
  const LOCAL_STORAGE_HASHEOUS_ENABLED_KEY = "scan.hasheousEnabled";
  const LOCAL_STORAGE_PLAYMATCH_ENABLED_KEY = "scan.playmatchEnabled";
  const { currentValue: selectedLanguage } = useSystemLanguage();

  // Hash-matcher providers — proxies that match files by hash and feed
  // IDs into the primary catalogs (IGDB, RetroAchievements). Kept out of
  // the main provider select so users don't read them as standalone
  // sources.
  const HASH_MATCHER_KEYS = ["hasheous", "playmatch"] as const;

  // Catalog options — main metadata sources. Hash matchers (hasheous,
  // playmatch) are filtered out and rendered as switch pills. IGDB's
  // heartbeat label flips to "IGDB + Playmatch" when Playmatch is
  // admin-enabled — strip the suffix since Playmatch has its own tile.
  const metadataOptions = computed(() =>
    heartbeat
      .getMetadataOptionsByPriority()
      .filter(
        (option) =>
          !(HASH_MATCHER_KEYS as readonly string[]).includes(option.value),
      )
      .map((option) => {
        const requiresHashes = option.value === "ra";
        const hashingDisabled = !calculateHashes.value;
        let disabled = option.disabled;
        if (hashingDisabled && requiresHashes) {
          disabled = t("scan.requires-hashes", { source: option.name });
        }
        const name = option.value === "igdb" ? "IGDB" : option.name;
        return { ...option, name, disabled };
      }),
  );

  const hashMatchers = computed<HashMatcher[]>(() => {
    const sources = heartbeat.value.METADATA_SOURCES;
    const igdbSelected = effectiveMetadataSources.value.some(
      (s) => s.value === "igdb",
    );
    const noHashes = !calculateHashes.value;

    const hasheousAdmin = Boolean(sources?.HASHEOUS_API_ENABLED);
    const playmatchAdmin = Boolean(sources?.PLAYMATCH_API_ENABLED);

    return [
      {
        value: "hasheous",
        name: "Hasheous",
        logo: "/assets/scrappers/hasheous.png",
        blockedReason: !hasheousAdmin
          ? t("scan.disabled-by-admin")
          : noHashes
            ? t("scan.requires-hashes", { source: "Hasheous" })
            : null,
        switchEnabled: hasheousAdmin && !noHashes,
      },
      {
        value: "playmatch",
        name: "Playmatch",
        logo: "/assets/scrappers/playmatch.png",
        // Playmatch is hash-based — same gate as Hasheous — plus the
        // backend requires IGDB in `apis` for its server-side join, so
        // we surface that as a secondary gate.
        blockedReason: !playmatchAdmin
          ? t("scan.disabled-by-admin")
          : noHashes
            ? t("scan.requires-hashes", { source: "Playmatch" })
            : !igdbSelected
              ? t("scan.playmatch-requires-igdb")
              : null,
        switchEnabled: playmatchAdmin && !noHashes && igdbSelected,
      },
    ];
  });

  const storedMetadataSources = useLocalStorage(
    LOCAL_STORAGE_METADATA_SOURCES_KEY,
    [] as string[],
  );
  const launchboxRemoteEnabled = useLocalStorage(
    LOCAL_STORAGE_LAUNCHBOX_REMOTE_ENABLED_KEY,
    true,
  );
  const hasheousEnabled = useLocalStorage(
    LOCAL_STORAGE_HASHEOUS_ENABLED_KEY,
    true,
  );
  const playmatchEnabled = useLocalStorage(
    LOCAL_STORAGE_PLAYMATCH_ENABLED_KEY,
    true,
  );
  const metadataLocale = computed({
    get: () => normalizeLocale(locale.value.trim() || "en"),
    set: (value: string) => {
      selectedLanguage.value = value;
    },
  });

  const metadataSources = ref<MetadataOption[]>(
    metadataOptions.value.filter(
      (m) => storedMetadataSources.value.includes(m.value) && !m.disabled,
    ) || heartbeat.getEnabledMetadataOptions(),
  );

  const isLaunchboxSelected = computed(() =>
    effectiveMetadataSources.value.some((s) => s.value === "launchbox"),
  );

  watch(metadataOptions, (newOptions) => {
    metadataSources.value = metadataSources.value.filter((s) =>
      newOptions.some((opt) => opt.value === s.value && !opt.disabled),
    );
  });

  function setHashMatcher(value: HashMatcher["value"], next: boolean) {
    if (value === "hasheous") hasheousEnabled.value = next;
    else playmatchEnabled.value = next;
  }

  function isHashMatcherOn(matcher: HashMatcher): boolean {
    if (!matcher.switchEnabled) return false;
    return matcher.value === "hasheous"
      ? hasheousEnabled.value
      : playmatchEnabled.value;
  }

  // Provider categorisation — mirrors the split used by the setup
  // wizard's metadata step. General catalogs ship a full game record
  // (title, artwork, descriptions); specific sources add a single
  // domain dimension (achievements, completion times, custom art).
  // Each group renders its own RSelect; both share `metadataSources`
  // as the model. RSelect's `show-all-option` is subset-safe — toggling
  // All in one group doesn't touch the other.
  const GENERAL_PROVIDER_KEYS = new Set([
    "igdb",
    "steam",
    "ss",
    "moby",
    "launchbox",
    "flashpoint",
    "gamelist",
    "libretro",
  ]);
  const SPECIFIC_PROVIDER_KEYS = new Set(["ra", "sgdb", "hltb"]);

  const generalProviders = computed<MetadataOption[]>(() =>
    metadataOptions.value.filter((o) => GENERAL_PROVIDER_KEYS.has(o.value)),
  );
  const specificProviders = computed<MetadataOption[]>(() =>
    metadataOptions.value.filter((o) => SPECIFIC_PROVIDER_KEYS.has(o.value)),
  );

  // Each group's RSelect uses empty-model-as-"All", but the scan backend
  // reads an empty `apis` list as "no sources", not "all". So when a group
  // is in All-mode we materialise its full enabled provider list — both to
  // drive the UI gates (IGDB present? any source picked?) and to build the
  // `apis` payload the backend actually understands.
  const enabledGeneralProviders = computed(() =>
    generalProviders.value.filter((o) => !o.disabled),
  );
  const enabledSpecificProviders = computed(() =>
    specificProviders.value.filter((o) => !o.disabled),
  );

  function hasGroupSelection(keys: Set<string>): boolean {
    return metadataSources.value.some((s) => keys.has(s.value));
  }

  // All-mode mirrors of each RSelect. Initialised the same way the
  // primitive does (no own selection ⇒ All) and kept in sync afterwards
  // via each select's `@update:all-selected`.
  const generalAllSelected = ref(!hasGroupSelection(GENERAL_PROVIDER_KEYS));
  const specificAllSelected = ref(!hasGroupSelection(SPECIFIC_PROVIDER_KEYS));

  // Concrete providers the scan will actually use: each group contributes
  // its explicit selection, or every enabled provider when in All-mode.
  const effectiveMetadataSources = computed<MetadataOption[]>(() => {
    const general = generalAllSelected.value
      ? enabledGeneralProviders.value
      : metadataSources.value.filter((s) => GENERAL_PROVIDER_KEYS.has(s.value));
    const specific = specificAllSelected.value
      ? enabledSpecificProviders.value
      : metadataSources.value.filter((s) =>
          SPECIFIC_PROVIDER_KEYS.has(s.value),
        );
    return [...general, ...specific];
  });

  return {
    storedMetadataSources,
    launchboxRemoteEnabled,
    metadataLocale,
    metadataSources,
    isLaunchboxSelected,
    hashMatchers,
    setHashMatcher,
    isHashMatcherOn,
    generalProviders,
    specificProviders,
    generalAllSelected,
    specificAllSelected,
    effectiveMetadataSources,
  };
}
