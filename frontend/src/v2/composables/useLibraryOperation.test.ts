import { describe, expect, it } from "vitest";
import {
  runWithConcurrency,
  withRateLimitBackoff,
} from "./useLibraryOperation";

describe("library operation execution gates", () => {
  it("preserves item order while bounding concurrency", async () => {
    let active = 0;
    let peak = 0;
    const values = await runWithConcurrency(
      [1, 2, 3, 4],
      async (value) => {
        active += 1;
        peak = Math.max(peak, active);
        await Promise.resolve();
        active -= 1;
        return value * 2;
      },
      2,
    );
    expect(values).toEqual([2, 4, 6, 8]);
    expect(peak).toBeLessThanOrEqual(2);
  });

  it("backs off retryable rate-limit failures and then succeeds", async () => {
    let attempts = 0;
    const delays: number[] = [];
    const result = await withRateLimitBackoff(
      async () => {
        attempts += 1;
        if (attempts < 3) throw { retryable: true, retryAfterMs: 7 };
        return "ok";
      },
      {
        maxAttempts: 3,
        baseDelayMs: 2,
        maxDelayMs: 20,
        sleep: async (delay) => {
          delays.push(delay);
        },
      },
    );
    expect(result).toBe("ok");
    expect(attempts).toBe(3);
    expect(delays).toEqual([7, 7]);
  });
});
