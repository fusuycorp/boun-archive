import { describe, it, expect } from "bun:test";
import { 
  OFFICIAL_SEMESTERS, 
  OFFICIAL_DEPARTMENTS, 
  buildOfficialScheduleUrl, 
  OFFICIAL_SCHEDULE_BASE 
} from "../src/lib/data/officialSchedule";

describe("Official Academic Schedule Registry & URL Suite", () => {
  it("contains all 82 official academic terms ranging from 2026/2027-1 to 1999/2000-1", () => {
    expect(OFFICIAL_SEMESTERS.length).toBe(82);
    expect(OFFICIAL_SEMESTERS[0].value).toBe("2026/2027-1");
    expect(OFFICIAL_SEMESTERS[0].label).toContain("2026/2027");
    expect(OFFICIAL_SEMESTERS[OFFICIAL_SEMESTERS.length - 1].value).toBe("1999/2000-1");
  });

  it("contains all 69 official departments and programs from OBIKAS", () => {
    expect(OFFICIAL_DEPARTMENTS.length).toBe(69);

    for (const dept of OFFICIAL_DEPARTMENTS) {
      expect(typeof dept.kisaadi).toBe("string");
      expect(dept.kisaadi.length).toBeGreaterThan(0);
      expect(typeof dept.bolum).toBe("string");
      expect(dept.bolum.length).toBeGreaterThan(0);
      expect(typeof dept.name).toBe("string");
      expect(dept.name.length).toBeGreaterThan(0);
    }
  });

  it("contains core departments such as CMPE, MATH, EE, and ME", () => {
    const codes = new Set(OFFICIAL_DEPARTMENTS.map(d => d.kisaadi));
    expect(codes.has("CMPE")).toBe(true);
    expect(codes.has("MATH")).toBe(true);
    expect(codes.has("EE")).toBe(true);
    expect(codes.has("ME")).toBe(true);
    expect(codes.has("IE")).toBe(true);
    expect(codes.has("EC")).toBe(true);
  });

  it("builds correct official schedule query URLs", () => {
    const url = buildOfficialScheduleUrl("2026/2027-1", "CMPE", "COMPUTER+ENGINEERING");
    expect(url).toBe(
      `${OFFICIAL_SCHEDULE_BASE}?donem=2026%2F2027-1&kisaadi=CMPE&bolum=COMPUTER+ENGINEERING`
    );
  });

  it("handles complex program names with special URL characters safely", () => {
    const cseDept = OFFICIAL_DEPARTMENTS.find(d => d.name.includes("COMPUTATIONAL SCIENCE"));
    expect(cseDept).toBeDefined();
    if (cseDept) {
      const url = buildOfficialScheduleUrl("2024/2025-1", cseDept.kisaadi, cseDept.bolum);
      expect(url.startsWith(OFFICIAL_SCHEDULE_BASE)).toBe(true);
      expect(url).toContain("kisaadi=CSE");
      expect(url).toContain("bolum=COMPUTATIONAL+SCIENCE+%26+ENGINEERING");
    }
  });
});
