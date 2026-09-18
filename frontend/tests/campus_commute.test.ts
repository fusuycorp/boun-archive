import { describe, it, expect } from "bun:test";
import { resolveRoomLocation, isInterCampusCommute } from "../src/lib/campus";

describe("Campus & Building Resolution Suite", () => {
  it("resolves John Freely Hall to South Campus (Güney)", () => {
    const loc = resolveRoomLocation("JF 108");
    expect(loc.building).toBe("John Freely Hall");
    expect(loc.campus).toBe("Güney");

    const loc2 = resolveRoomLocation("JF334");
    expect(loc2.building).toBe("John Freely Hall");
    expect(loc2.campus).toBe("Güney");
  });

  it("resolves Faculty of Education to North Campus (Kuzey)", () => {
    const loc = resolveRoomLocation("EF 206");
    expect(loc.building).toBe("Education Faculty");
    expect(loc.campus).toBe("Kuzey");

    const loc2 = resolveRoomLocation("EF102");
    expect(loc2.building).toBe("Education Faculty");
    expect(loc2.campus).toBe("Kuzey");
  });

  it("resolves North Campus buildings correctly (NH, KB, BM, ETA)", () => {
    expect(resolveRoomLocation("NH 401")).toEqual({ building: "New Hall", campus: "Kuzey" });
    expect(resolveRoomLocation("KB 433")).toEqual({ building: "Kare Blok", campus: "Kuzey" });
    expect(resolveRoomLocation("BM B4")).toEqual({ building: "Computer Engineering", campus: "Kuzey" });
    expect(resolveRoomLocation("ETA A2")).toEqual({ building: "ETA Building", campus: "Kuzey" });
  });

  it("resolves South Campus buildings correctly (TB, IB, M, NB)", () => {
    expect(resolveRoomLocation("TB 240")).toEqual({ building: "Basic Sciences (Anderson)", campus: "Güney" });
    expect(resolveRoomLocation("IB 102")).toEqual({ building: "Washburn Hall (İİBF)", campus: "Güney" });
    expect(resolveRoomLocation("M 1100")).toEqual({ building: "Engineering Building", campus: "Güney" });
    expect(resolveRoomLocation("NB 118")).toEqual({ building: "Natuk Birkan", campus: "Güney" });
  });

  it("resolves Hisar, Uçaksavar, Kandilli, and Kilyos campuses correctly", () => {
    expect(resolveRoomLocation("HKB105").campus).toBe("Hisar");
    expect(resolveRoomLocation("GKM 1").campus).toBe("Uçaksavar");
    expect(resolveRoomLocation("KANDİLLİ 1").campus).toBe("Kandilli");
    expect(resolveRoomLocation("KLY 101").campus).toBe("Kilyos");
  });

  it("detects inter-campus commute conflicts (Dash of Death)", () => {
    expect(isInterCampusCommute("Güney", "Kuzey")).toBe(true);
    expect(isInterCampusCommute("Kuzey", "Güney")).toBe(true);
    expect(isInterCampusCommute("Güney", "Hisar")).toBe(true);
    expect(isInterCampusCommute("Kuzey", "Uçaksavar")).toBe(true);

    // Same campus has no commute risk
    expect(isInterCampusCommute("Güney", "Güney")).toBe(false);
    expect(isInterCampusCommute("Kuzey", "Kuzey")).toBe(false);

    // Virtual / Remote classes have no commute risk
    expect(isInterCampusCommute("Virtual", "Güney")).toBe(false);
    expect(isInterCampusCommute("Kuzey", "Virtual")).toBe(false);
  });
});
