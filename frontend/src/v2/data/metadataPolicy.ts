import type {
  MetadataFieldTarget,
  MetadataPolicy,
  OwnershipState,
} from "./contracts";

export type PolicyDecision =
  "write" | "unchanged" | "protected" | "fallback-read-only";

export interface MetadataValue {
  field: string;
  locale: string;
  region?: string;
  provider?: string;
  value: string;
  ownership: OwnershipState;
}

export interface MetadataCandidate {
  field: string;
  locale: string;
  region?: string;
  provider: string;
  value: string;
  ownership?: OwnershipState;
}

export interface MetadataPolicyDecision {
  field: string;
  locale: string;
  provider?: string;
  region?: string;
  value?: string;
  decision: PolicyDecision;
  reason: string;
}

export interface MetadataPolicyInput {
  policy: MetadataPolicy;
  current: MetadataValue[];
  candidates: MetadataCandidate[];
  providerOrder?: string[];
  fallbackLocales?: string[];
  region?: string;
}

function isProtected(ownership: OwnershipState | undefined): boolean {
  return ownership === "manual" || ownership === "unknown";
}

function providerRank(provider: string, providerOrder: string[]): number {
  const rank = providerOrder.indexOf(provider);
  return rank === -1 ? providerOrder.length : rank;
}

function candidateMatchesTarget(
  candidate: MetadataCandidate,
  target: MetadataFieldTarget,
): boolean {
  return (
    candidate.field === target.field &&
    candidate.locale === target.locale &&
    (target.provider === undefined || candidate.provider === target.provider)
  );
}

function currentMatchesTarget(
  value: MetadataValue,
  target: MetadataFieldTarget,
  region?: string,
): boolean {
  return (
    value.field === target.field &&
    value.locale === target.locale &&
    (region === undefined ||
      value.region === undefined ||
      value.region === region)
  );
}

function decisionForTarget(
  target: MetadataFieldTarget,
  input: MetadataPolicyInput,
): MetadataPolicyDecision {
  const current = input.current.find((value) =>
    currentMatchesTarget(value, target, input.region),
  );
  const candidates = input.candidates
    .filter((candidate) => candidateMatchesTarget(candidate, target))
    .sort(
      (left, right) =>
        providerRank(left.provider, input.providerOrder ?? []) -
        providerRank(right.provider, input.providerOrder ?? []),
    );
  const candidate = candidates[0];

  const base = {
    field: target.field,
    locale: target.locale,
    provider: candidate?.provider ?? target.provider,
    region: candidate?.region ?? current?.region ?? input.region,
  };

  if (input.policy.mode === "none") {
    return { ...base, decision: "unchanged", reason: "policy-disabled" };
  }

  if (current && isProtected(current.ownership)) {
    return {
      ...base,
      value: current.value,
      decision: "protected",
      reason: "existing-value-is-manual-or-unknown",
    };
  }

  if (candidate) {
    if (current && input.policy.mode === "missing-only") {
      return {
        ...base,
        value: current.value,
        decision: "unchanged",
        reason: "missing-only-keeps-existing-provider-value",
      };
    }

    if (current?.value === candidate.value) {
      return {
        ...base,
        value: current.value,
        decision: "unchanged",
        reason: "candidate-matches-existing-value",
      };
    }

    return {
      ...base,
      value: candidate.value,
      decision: "write",
      reason: "best-provider-candidate-for-field-locale-and-region",
    };
  }

  const fallback = input.candidates.find(
    (value) =>
      value.field === target.field &&
      input.fallbackLocales?.includes(value.locale) &&
      (target.provider === undefined || value.provider === target.provider),
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

export function evaluateMetadataPolicy(
  input: MetadataPolicyInput,
): MetadataPolicyDecision[] {
  return input.policy.fields.map((target) => decisionForTarget(target, input));
}
