import type { MediaPolicy, MediaTarget, OwnershipState } from "./contracts";
import type { PolicyDecision } from "./metadataPolicy";

export type MediaKind = "neutral" | "localized";

export interface MediaValue {
  role: string;
  locale?: string;
  region?: string;
  provider?: string;
  value: string;
  ownership: OwnershipState;
}

export interface MediaCandidate {
  role: string;
  locale?: string;
  region?: string;
  provider: string;
  value: string;
  ownership?: OwnershipState;
}

export interface MediaPolicyDecision {
  role: string;
  kind: MediaKind;
  locale?: string;
  region?: string;
  provider?: string;
  value?: string;
  decision: PolicyDecision;
  reason: string;
}

export interface MediaPolicyInput {
  policy: MediaPolicy;
  current: MediaValue[];
  candidates: MediaCandidate[];
  providerOrder?: string[];
  fallbackLocales?: string[];
}

function isProtected(ownership: OwnershipState | undefined): boolean {
  return ownership === "manual" || ownership === "unknown";
}

function kindOf(target: MediaTarget): MediaKind {
  return target.locale === undefined ? "neutral" : "localized";
}

function matchesSlot(
  value: Pick<MediaValue, "role" | "locale" | "region">,
  target: MediaTarget,
): boolean {
  return (
    value.role === target.role &&
    (target.locale === undefined
      ? value.locale === undefined
      : value.locale === target.locale) &&
    (target.region === undefined || value.region === target.region)
  );
}

function matchesCandidate(
  value: Pick<MediaCandidate, "role" | "locale" | "region" | "provider">,
  target: MediaTarget,
): boolean {
  return (
    matchesSlot(value, target) &&
    (target.provider === undefined || value.provider === target.provider)
  );
}

function providerRank(provider: string, providerOrder: string[]): number {
  const rank = providerOrder.indexOf(provider);
  return rank === -1 ? providerOrder.length : rank;
}

function decisionForTarget(
  target: MediaTarget,
  input: MediaPolicyInput,
): MediaPolicyDecision {
  const kind = kindOf(target);
  const current = input.current.find((value) => matchesSlot(value, target));
  const candidates = input.candidates
    .filter((candidate) => matchesCandidate(candidate, target))
    .sort(
      (left, right) =>
        providerRank(left.provider, input.providerOrder ?? []) -
        providerRank(right.provider, input.providerOrder ?? []),
    );
  const candidate = candidates[0];
  const base = {
    role: target.role,
    kind,
    locale: target.locale,
    region: target.region ?? candidate?.region ?? current?.region,
    provider: candidate?.provider ?? target.provider ?? current?.provider,
  };

  if (input.policy.mode === "none") {
    return { ...base, decision: "unchanged", reason: "policy-disabled" };
  }

  if (current && isProtected(current.ownership)) {
    return {
      ...base,
      value: current.value,
      decision: "protected",
      reason: "existing-media-is-manual-or-unknown",
    };
  }

  if (candidate) {
    if (current && input.policy.mode === "missing-only") {
      return {
        ...base,
        value: current.value,
        decision: "unchanged",
        reason: "missing-only-keeps-existing-media",
      };
    }

    if (current?.value === candidate.value) {
      return {
        ...base,
        value: current.value,
        decision: "unchanged",
        reason: "candidate-matches-existing-media",
      };
    }

    return {
      ...base,
      value: candidate.value,
      region: candidate.region ?? base.region,
      provider: candidate.provider,
      decision: "write",
      reason: "best-provider-candidate-for-media-slot",
    };
  }

  const fallback =
    target.locale === undefined
      ? undefined
      : input.candidates.find(
          (value) =>
            value.role === target.role &&
            value.locale !== undefined &&
            input.fallbackLocales?.includes(value.locale) &&
            (target.provider === undefined ||
              value.provider === target.provider),
        );

  if (fallback) {
    return {
      ...base,
      value: fallback.value,
      decision: "fallback-read-only",
      reason: "fallback-locale-is-display-only",
    };
  }

  return { ...base, decision: "unchanged", reason: "no-matching-candidate" };
}

export function evaluateMediaPolicy(
  input: MediaPolicyInput,
): MediaPolicyDecision[] {
  return input.policy.targets.map((target) => decisionForTarget(target, input));
}
