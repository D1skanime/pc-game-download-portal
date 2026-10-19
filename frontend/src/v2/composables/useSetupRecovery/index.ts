import { computed, ref } from "vue";
import type { SetupRecoverySnapshot } from "@/__generated__";
import setupApi, {
  type SetupFolderAssignment,
  type SetupFolderDraft,
} from "@/services/api/setup";
import type { AdminUserDraft } from "@/v2/components/Auth/SetupStepAdmin.vue";
import { refetchCSRFToken } from "@/v2/data/adapters/legacy/services/api";
import identityApi from "@/v2/data/adapters/legacy/services/api/identity";
import userApi from "@/v2/data/adapters/legacy/services/api/user";
import storeAuth from "@/v2/data/adapters/legacy/stores/auth";
import storeHeartbeat from "@/v2/data/adapters/legacy/stores/heartbeat";

export function useSetupRecovery() {
  const auth = storeAuth();
  const heartbeat = storeHeartbeat();
  const snapshot = ref<SetupRecoverySnapshot | null>(null);
  const busy = ref(false);
  const cause = ref<string | null>(null);
  const loginRequired = ref(false);
  let finishing: Promise<void> | undefined;

  async function refresh() {
    cause.value = null;
    await heartbeat.fetchHeartbeat();
    const enrolled = !heartbeat.value.SYSTEM.SHOW_SETUP_WIZARD;
    if (!auth.user) {
      loginRequired.value = enrolled;
      return null;
    }
    const { data } = await setupApi.getStatus();
    snapshot.value = data;
    loginRequired.value = false;
    cause.value = data.cause_code;
    return data;
  }
  function mergeDraft(draft: SetupFolderDraft): SetupFolderDraft {
    const merged = { ...draft };
    for (const saved of snapshot.value?.saved_assignments ?? [])
      merged[saved.folder_name] = saved.platform_slug;
    return merged;
  }
  async function retryCheck() {
    if (busy.value) return;
    busy.value = true;
    try {
      await refresh();
    } catch {
      cause.value = "status-unavailable";
    } finally {
      busy.value = false;
    }
  }
  async function finish(
    admin: AdminUserDraft,
    assignments: SetupFolderAssignment[],
  ) {
    if (finishing) return finishing;
    busy.value = true;
    cause.value = null;
    const run = async () => {
      try {
        await refresh();
        if (loginRequired.value) return;
        if (!auth.user) {
          try {
            await userApi.createUser({
              username: admin.username,
              email: admin.email,
              password: admin.password,
              role: "admin",
            });
          } catch {
            await refresh();
            if (loginRequired.value) {
              admin.password = "";
              admin.repeatPassword = "";
              return;
            }
            throw new Error("account-unconfirmed");
          }
          try {
            await identityApi.login(admin.username, admin.password);
            await refetchCSRFToken();
            await auth.fetchCurrentUser();
          } finally {
            admin.password = "";
            admin.repeatPassword = "";
          }
          if (!auth.user) {
            loginRequired.value = true;
            return;
          }
        }
        await refetchCSRFToken();
        const current = await refresh();
        if (!current || current.setup_complete) return;
        const saved = new Map(
          current.saved_assignments.map((item) => [
            item.folder_name,
            item.platform_slug,
          ]),
        );
        const missing = assignments.filter(
          (item) => saved.get(item.folder_name) !== item.platform_slug,
        );
        if (missing.length) {
          try {
            await setupApi.assignFolders(missing);
          } catch {
            const reconciled = await refresh();
            if (!reconciled?.setup_complete)
              cause.value = reconciled?.cause_code ?? "save-unconfirmed";
            return;
          }
        }
        await refresh();
      } catch {
        cause.value = "status-unavailable";
      }
    };
    finishing = run().finally(() => {
      busy.value = false;
      finishing = undefined;
    });
    return finishing;
  }
  return {
    snapshot,
    busy,
    cause,
    loginRequired,
    complete: computed(() => snapshot.value?.setup_complete === true),
    enrolled: computed(
      () => Boolean(auth.user) || snapshot.value?.enrolled === true,
    ),
    refresh,
    retryCheck,
    mergeDraft,
    finish,
  };
}
