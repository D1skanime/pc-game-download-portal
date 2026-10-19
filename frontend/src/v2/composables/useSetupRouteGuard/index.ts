import setupApi from "@/v2/data/adapters/legacy/services/api/setup";
import type { User } from "@/v2/data/adapters/legacy/stores/users";

interface SetupRouteContext {
  route: string | undefined;
  fullPath: string;
  connected: boolean;
  showWizard: boolean;
  user: Pick<User, "role"> | null;
}
export async function resolveSetupRoute(context: SetupRouteContext) {
  if (!context.connected) return undefined;
  if (context.showWizard)
    return context.route === "setup" ? undefined : { name: "setup" };
  if (!context.user)
    return context.route === "setup"
      ? { name: "login", query: { next: "/setup" } }
      : undefined;
  if (context.user.role !== "admin")
    return context.route === "setup" ? { name: "home" } : undefined;
  try {
    const { data } = await setupApi.getStatus();
    if (!data.setup_complete)
      return context.route === "setup" ? undefined : { name: "setup" };
    // The explicit completion page remains reachable until the user leaves it.
    return undefined;
  } catch {
    // Unreachable status must neither claim completion nor create a redirect loop.
    return undefined;
  }
}
