import { describe, expect, it } from "vitest";
import {
  pickStoragePlatform,
  type StorageProofPlatform,
} from "./operationalProof";

function platform(id: number): StorageProofPlatform {
  return { id };
}

describe("pickStoragePlatform", () => {
  it("skips placeholder filesystem platforms and picks the first real platform", () => {
    const placeholder = platform(-1);
    const real = platform(42);

    expect(pickStoragePlatform([placeholder, real])).toEqual(real);
  });

  it("returns undefined when no real platform id is available", () => {
    expect(pickStoragePlatform([platform(-1), platform(0)])).toBeUndefined();
  });
});
