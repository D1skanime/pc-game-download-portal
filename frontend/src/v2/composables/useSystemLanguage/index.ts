import { computed, onScopeDispose, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useUISettings } from "@/composables/useUISettings";
import configApi from "@/services/api/config";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import storeAuth from "@/v2/data/adapters/legacy/stores/auth";
import storeConfig from "@/v2/data/adapters/legacy/stores/config";
import storeLanguage from "@/v2/data/adapters/legacy/stores/language";

export function useSystemLanguage() {
  const { locale, t } = useI18n();
  const language = storeLanguage();
  const settings = useUISettings();
  const auth = storeAuth();
  const config = storeConfig();
  const snackbar = useSnackbar();
  const saving = ref(false);
  let active = true;
  let desired: string | undefined;
  let acknowledged = language.selectedLanguage.value;
  onScopeDispose(() => {
    active = false;
    desired = undefined;
  });

  async function apply(next: string) {
    const selected = language.languages.find((item) => item.value === next);
    if (!selected) return;
    language.selectedLanguage = selected;
    locale.value = next;
    const identity = auth.user?.id;
    let saved = false;
    try {
      saved = await settings.setLocale(next);
    } catch {
      /* Report personal persistence independently. */
    }
    if (active && auth.user?.id === identity && !saved) {
      snackbar.error(`${t("settings.language")}: ${t("settings.failed")}`);
    }
  }

  async function drain() {
    if (saving.value) return;
    saving.value = true;
    const userId = auth.user?.id;
    const current = () => active && auth.user?.id === userId;
    try {
      while (desired && current()) {
        const next = desired;
        desired = undefined;
        const systemSelection = auth.scopes.includes("platforms.write");
        if (systemSelection) {
          try {
            const before = await config.fetchConfig({ rethrow: true });
            if (!current()) break;
            if (
              !auth.scopes.includes("platforms.write") ||
              !before.CONFIG_FILE_WRITABLE
            )
              throw new Error(t("settings.config-file-not-writable-title"));
            const expected = [...before.SCAN_LANGUAGE_PRIORITY];
            const base = next.replace(/_/g, "-").split("-")[0].toLowerCase();
            const priority = [...new Set([base, "en", ...expected])];
            const response = await configApi.updateScanLanguage({
              language_priority: priority,
              expected_language_priority: expected,
            });
            const committed = await config.fetchConfig({ rethrow: true });
            if (!current()) break;
            if (
              JSON.stringify(committed.SCAN_LANGUAGE_PRIORITY) !==
              JSON.stringify(response.data.language_priority)
            )
              throw new Error(t("settings.scan-settings-load-error-title"));
            acknowledged = next;
          } catch (error) {
            if (current()) {
              desired = undefined;
              snackbar.error(
                t("settings.scan-settings-save-error", {
                  detail:
                    error instanceof Error
                      ? error.message
                      : t("common.try-again"),
                }),
              );
              if (acknowledged !== language.selectedLanguage.value)
                await apply(acknowledged);
              try {
                await config.fetchConfig({ rethrow: true });
              } catch {
                /* Retry reads fresh authority. */
              }
            }
            break;
          }
        }
        if (!current()) break;
        if (desired) continue;
        await apply(next);
      }
    } finally {
      saving.value = false;
    }
  }

  const currentValue = computed({
    get: () => language.selectedLanguage.value,
    set: (value: string) => {
      if (!language.languages.some((item) => item.value === value)) return;
      desired = value;
      void drain();
    },
  });
  return { currentValue, saving };
}
