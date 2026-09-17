import { renderDesktopApp, type DesktopBindings } from "./app";
import "./styles.css";

const invoke = async <T>(
  command: string,
  args?: Record<string, string>,
): Promise<T> => {
  const tauri = (
    window as Window & {
      __TAURI__?: {
        core?: {
          invoke: <R>(
            name: string,
            payload?: Record<string, string>,
          ) => Promise<R>;
        };
      };
    }
  ).__TAURI__;
  if (!tauri?.core) throw new Error("Desktop command bridge unavailable");
  return tauri.core.invoke<T>(command, args);
};

const bindings: DesktopBindings = {
  invoke,
  listen: async (_event, _handler) => () => undefined,
};

const root = document.querySelector<HTMLElement>("#app");
if (root) void renderDesktopApp(root, bindings);
