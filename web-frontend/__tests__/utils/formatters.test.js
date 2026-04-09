import { describe, expect, it } from "vitest";
import {
  formatAddress,
  formatBasisPoints,
  formatCurrency,
  formatDate,
  formatDuration,
  formatLargeNumber,
  formatPercentage,
  formatRiskScore,
  formatSharpeRatio,
} from "../../src/utils/formatters";

describe("formatCurrency", () => {
  it("formats a positive number as USD", () => {
    expect(formatCurrency(1234.56)).toBe("$1,234.56");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("returns $0.00 for null/undefined", () => {
    expect(formatCurrency(null)).toBe("$0.00");
    expect(formatCurrency(undefined)).toBe("$0.00");
  });

  it("returns $0.00 for NaN", () => {
    expect(formatCurrency(NaN)).toBe("$0.00");
  });

  it("formats negative numbers", () => {
    expect(formatCurrency(-500)).toBe("-$500.00");
  });

  it("respects custom decimals", () => {
    expect(formatCurrency(1234.5678, "USD", 4)).toBe("$1,234.5678");
  });
});

describe("formatPercentage", () => {
  it("formats a number as percentage", () => {
    expect(formatPercentage(14.2)).toBe("14.20%");
  });

  it("returns 0.00% for null", () => {
    expect(formatPercentage(null)).toBe("0.00%");
  });

  it("shows + sign when showSign=true and value is positive", () => {
    expect(formatPercentage(5.5, 2, true)).toBe("+5.50%");
  });

  it("does not show + sign for negative values", () => {
    expect(formatPercentage(-3.2, 2, true)).toBe("-3.20%");
  });

  it("respects custom decimals", () => {
    expect(formatPercentage(12.3456, 1)).toBe("12.3%");
  });
});

describe("formatLargeNumber", () => {
  it("formats billions", () => {
    expect(formatLargeNumber(1500000000)).toBe("1.5B");
  });

  it("formats millions", () => {
    expect(formatLargeNumber(2500000)).toBe("2.5M");
  });

  it("formats thousands", () => {
    expect(formatLargeNumber(3500)).toBe("3.5K");
  });

  it("formats small numbers without suffix", () => {
    expect(formatLargeNumber(500)).toBe("500.0");
  });

  it("returns 0 for null", () => {
    expect(formatLargeNumber(null)).toBe("0");
  });
});

describe("formatDate", () => {
  it("formats a valid date string (short format)", () => {
    const result = formatDate("2026-04-09");
    expect(result).toBeTruthy();
    expect(result).toContain("2026");
  });

  it("returns empty string for null", () => {
    expect(formatDate(null)).toBe("");
  });

  it("returns empty string for invalid date", () => {
    expect(formatDate("not-a-date")).toBe("");
  });

  it("formats long format", () => {
    const result = formatDate("2026-01-15", "long");
    expect(result).toContain("January");
    expect(result).toContain("2026");
  });
});

describe("formatAddress", () => {
  it("shortens a long wallet address", () => {
    const addr = "0x1234567890abcdef1234567890abcdef12345678";
    expect(formatAddress(addr)).toBe("0x1234...5678");
  });

  it("returns empty string for null", () => {
    expect(formatAddress(null)).toBe("");
  });

  it("returns the address unchanged if shorter than min length", () => {
    expect(formatAddress("0x12")).toBe("0x12");
  });
});

describe("formatRiskScore", () => {
  it("returns Low for score < 30", () => {
    expect(formatRiskScore(20).category).toBe("Low");
    expect(formatRiskScore(20).color).toBe("success");
  });

  it("returns Moderate for score between 30–59", () => {
    expect(formatRiskScore(50).category).toBe("Moderate");
    expect(formatRiskScore(50).color).toBe("warning");
  });

  it("returns High for score >= 60", () => {
    expect(formatRiskScore(80).category).toBe("High");
    expect(formatRiskScore(80).color).toBe("error");
  });

  it("returns Unknown for null", () => {
    expect(formatRiskScore(null).category).toBe("Unknown");
  });
});

describe("formatSharpeRatio", () => {
  it("returns Excellent for sharpe > 2", () => {
    expect(formatSharpeRatio(2.5).interpretation).toBe("Excellent");
  });

  it("returns Good for sharpe between 1 and 2", () => {
    expect(formatSharpeRatio(1.5).interpretation).toBe("Good");
  });

  it("returns Fair for sharpe between 0 and 1", () => {
    expect(formatSharpeRatio(0.5).interpretation).toBe("Fair");
  });

  it("returns Poor for negative sharpe", () => {
    expect(formatSharpeRatio(-0.5).interpretation).toBe("Poor");
  });
});

describe("formatBasisPoints", () => {
  it("converts decimal to basis points", () => {
    expect(formatBasisPoints(0.0025)).toBe("25 bps");
  });

  it("returns 0 bps for null", () => {
    expect(formatBasisPoints(null)).toBe("0 bps");
  });
});

describe("formatDuration", () => {
  it("formats seconds", () => {
    expect(formatDuration(45)).toBe("45s");
  });

  it("formats minutes and seconds", () => {
    expect(formatDuration(125)).toBe("2m 5s");
  });

  it("formats hours", () => {
    expect(formatDuration(3661)).toBe("1h 1m 1s");
  });

  it("returns 0s for 0", () => {
    expect(formatDuration(0)).toBe("0s");
  });
});
