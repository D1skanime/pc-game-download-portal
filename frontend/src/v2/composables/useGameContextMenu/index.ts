// useGameContextMenu
//
// Provide/inject handle for the app-wide ROM context menu. AppLayout mounts
// GameContextMenu once and provides the opener; cards + tiles inject the
// opener and call it from their "more" button or right-click.
import { inject } from "vue";
import type { SimpleRom } from "@/stores/roms";

export type OpenGameContextMenu = (rom: SimpleRom, event: MouseEvent) => void;

export const GAME_CONTEXT_MENU_KEY = "r-v2-open-game-context-menu" as const;

// Safe no-op fallback so calls outside AppLayout (Storybook, mounted test
// components) don't throw.
export function useOpenGameContextMenu(): OpenGameContextMenu {
  return inject<OpenGameContextMenu>(GAME_CONTEXT_MENU_KEY, () => undefined);
}
