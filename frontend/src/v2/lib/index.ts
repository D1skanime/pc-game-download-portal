// RomM v2 Component Library — barrel export.
//
// Only design-system *primitives* live here. Specializations (BackBtn,
// PlatformTile, InfoPanel, …) belong under src/v2/components/<feature>/
// and are imported directly, not through this barrel.
//
// Rule: every export below must be general enough that two or more
// features depend on it, and must ship a Storybook story.

// Form + text primitives
export * from "./RCheckbox";
export * from "./RSelect";
export * from "./RTextField";

// Layout + surface primitives
export * from "./RAlert";
export * from "./RCard";
export * from "./RDivider";
export * from "./RList";
export * from "./RListItem";
export * from "./RToolbar";

// Buttons + interactive primitives
export * from "./RBtn";
export * from "./RRating";
export * from "./RSliderBtnGroup";
export * from "./RTooltip";

// Menus
export * from "./RMenu";
export * from "./RMenuDivider";
export * from "./RMenuHeader";
export * from "./RMenuItem";
export * from "./RMenuPanel";

// Display atoms
export * from "./RAvatar";
export * from "./RBadge";
export * from "./RChip";
export * from "./RIcon";
export * from "./RImg";
export * from "./RPlatformIcon";
export * from "./RProgressCircular";
export * from "./RSkeletonBlock";
export * from "./RSpinner";

// Data
export * from "./RTable";

// Overlays
export * from "./RDialog";

// Domain-specific primitive
export * from "./RGameCard";
