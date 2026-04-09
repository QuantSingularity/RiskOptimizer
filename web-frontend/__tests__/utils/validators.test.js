import { describe, expect, it } from "vitest";
import {
  isNonNegativeNumber,
  isPositiveNumber,
  isValidAddress,
  isValidConfidenceLevel,
  isValidEmail,
  isValidPercentage,
  validateAllocation,
  validateDateRange,
  validateLength,
  validateRequired,
  validateRiskTolerance,
} from "../../src/utils/validators";

describe("isValidAddress", () => {
  it("accepts a valid Ethereum address", () => {
    expect(isValidAddress("0xAbCd1234567890abcdef1234567890abCDEF1234")).toBe(
      true,
    );
  });

  it("rejects address without 0x prefix", () => {
    expect(isValidAddress("AbCd1234567890abcdef1234567890abCDEF1234")).toBe(
      false,
    );
  });

  it("rejects address that is too short", () => {
    expect(isValidAddress("0x12345")).toBe(false);
  });

  it("rejects null/undefined", () => {
    expect(isValidAddress(null)).toBe(false);
    expect(isValidAddress(undefined)).toBe(false);
  });
});

describe("isValidEmail", () => {
  it("accepts valid email", () => {
    expect(isValidEmail("user@example.com")).toBe(true);
  });

  it("rejects email without @", () => {
    expect(isValidEmail("userexample.com")).toBe(false);
  });

  it("rejects null", () => {
    expect(isValidEmail(null)).toBe(false);
  });
});

describe("isValidPercentage", () => {
  it("accepts 0", () => expect(isValidPercentage(0)).toBe(true));
  it("accepts 100", () => expect(isValidPercentage(100)).toBe(true));
  it("accepts 50.5", () => expect(isValidPercentage(50.5)).toBe(true));
  it("rejects -1", () => expect(isValidPercentage(-1)).toBe(false));
  it("rejects 101", () => expect(isValidPercentage(101)).toBe(false));
  it("rejects NaN", () => expect(isValidPercentage(NaN)).toBe(false));
  it("rejects string", () => expect(isValidPercentage("50")).toBe(false));
});

describe("isPositiveNumber", () => {
  it("accepts positive numbers", () => expect(isPositiveNumber(1)).toBe(true));
  it("rejects zero", () => expect(isPositiveNumber(0)).toBe(false));
  it("rejects negative", () => expect(isPositiveNumber(-5)).toBe(false));
  it("rejects NaN", () => expect(isPositiveNumber(NaN)).toBe(false));
});

describe("isNonNegativeNumber", () => {
  it("accepts zero", () => expect(isNonNegativeNumber(0)).toBe(true));
  it("accepts positive", () => expect(isNonNegativeNumber(5)).toBe(true));
  it("rejects negative", () => expect(isNonNegativeNumber(-1)).toBe(false));
});

describe("validateAllocation", () => {
  it("accepts allocations that sum to 100", () => {
    const allocs = [
      { asset: "A", percentage: 60 },
      { asset: "B", percentage: 40 },
    ];
    expect(validateAllocation(allocs).isValid).toBe(true);
  });

  it("rejects allocations that do not sum to 100", () => {
    const allocs = [
      { asset: "A", percentage: 60 },
      { asset: "B", percentage: 30 },
    ];
    const result = validateAllocation(allocs);
    expect(result.isValid).toBe(false);
    expect(result.error).toMatch(/90/);
  });

  it("rejects empty array", () => {
    expect(validateAllocation([]).isValid).toBe(false);
  });

  it("rejects non-array", () => {
    expect(validateAllocation(null).isValid).toBe(false);
  });
});

describe("validateDateRange", () => {
  it("accepts valid date range", () => {
    expect(validateDateRange("2026-01-01", "2026-12-31").isValid).toBe(true);
  });

  it("rejects start date after end date", () => {
    const result = validateDateRange("2026-12-31", "2026-01-01");
    expect(result.isValid).toBe(false);
    expect(result.error).toMatch(/before/i);
  });

  it("rejects invalid start date", () => {
    expect(validateDateRange("not-a-date", "2026-01-01").isValid).toBe(false);
  });

  it("rejects invalid end date", () => {
    expect(validateDateRange("2026-01-01", "bad-date").isValid).toBe(false);
  });
});

describe("validateRequired", () => {
  it("passes for non-empty value", () => {
    expect(validateRequired("hello").isValid).toBe(true);
  });

  it("fails for empty string", () => {
    expect(validateRequired("").isValid).toBe(false);
  });

  it("fails for null", () => {
    expect(validateRequired(null).isValid).toBe(false);
  });

  it("includes field name in error", () => {
    const result = validateRequired("", "Email");
    expect(result.error).toContain("Email");
  });
});

describe("validateLength", () => {
  it("passes when within range", () => {
    expect(validateLength("hello", 3, 10).isValid).toBe(true);
  });

  it("fails when too short", () => {
    expect(validateLength("hi", 5, 10).isValid).toBe(false);
  });

  it("fails when too long", () => {
    expect(validateLength("hello world", 0, 5).isValid).toBe(false);
  });

  it("fails for non-string", () => {
    expect(validateLength(123, 0, 5).isValid).toBe(false);
  });
});

describe("isValidConfidenceLevel", () => {
  it("accepts 0.90, 0.95, 0.99", () => {
    expect(isValidConfidenceLevel(0.9)).toBe(true);
    expect(isValidConfidenceLevel(0.95)).toBe(true);
    expect(isValidConfidenceLevel(0.99)).toBe(true);
  });

  it("rejects arbitrary values", () => {
    expect(isValidConfidenceLevel(0.85)).toBe(false);
    expect(isValidConfidenceLevel(1)).toBe(false);
  });
});

describe("validateRiskTolerance", () => {
  it("passes for values 0–100", () => {
    expect(validateRiskTolerance(0).isValid).toBe(true);
    expect(validateRiskTolerance(50).isValid).toBe(true);
    expect(validateRiskTolerance(100).isValid).toBe(true);
  });

  it("fails for values > 100", () => {
    expect(validateRiskTolerance(101).isValid).toBe(false);
  });

  it("fails for negative values", () => {
    expect(validateRiskTolerance(-1).isValid).toBe(false);
  });
});
