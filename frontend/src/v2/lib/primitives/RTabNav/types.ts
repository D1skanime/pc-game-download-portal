export type RTabNavItem = {
  id: string;
  label: string;
  /** Optional MDI icon name shown before the label. */
  icon?: string;
  badge?: string | number | null;
  show?: boolean;
};
