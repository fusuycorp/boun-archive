/**
 * Campus and Building Topology Registry for Boğaziçi University
 * 
 * Invariant: JF (John Freely Hall) is in Güney, EF (Education Faculty) is in Kuzey.
 */

export interface LocationInfo {
  building: string;
  campus: string;
}

export const ROOM_LOCATION_REGISTRY: Record<string, LocationInfo> = {
  // Kuzey Kampüs (North)
  EF: { building: "Education Faculty", campus: "Kuzey" },
  NH: { building: "New Hall", campus: "Kuzey" },
  KB: { building: "Kare Blok", campus: "Kuzey" },
  KBPCLAB: { building: "Kare Blok PC Lab", campus: "Kuzey" },
  KBZ: { building: "Kare Blok Basement", campus: "Kuzey" },
  BM: { building: "Computer Engineering", campus: "Kuzey" },
  ETA: { building: "ETA Building", campus: "Kuzey" },
  ETAB: { building: "ETA Building Block B", campus: "Kuzey" },
  ETB: { building: "ETA Building Block B", campus: "Kuzey" },
  KP: { building: "Kuzey Park", campus: "Kuzey" },
  KPARK: { building: "Kuzey Park", campus: "Kuzey" },
  VY: { building: "Vedat Yerlici", campus: "Kuzey" },
  VYKM: { building: "Vedat Yerlici Center", campus: "Kuzey" },
  KYD: { building: "Kuzey YADYOK", campus: "Kuzey" },
  SL: { building: "Student Labs", campus: "Kuzey" },

  // Güney Kampüs (South)
  JF: { building: "John Freely Hall", campus: "Güney" },
  TB: { building: "Basic Sciences (Anderson)", campus: "Güney" },
  TBA: { building: "Anderson Hall", campus: "Güney" },
  TBD: { building: "Basic Sciences Block D", campus: "Güney" },
  AND: { building: "Anderson Hall", campus: "Güney" },
  IB: { building: "Washburn Hall (İİBF)", campus: "Güney" },
  İB: { building: "Washburn Hall (İİBF)", campus: "Güney" },
  M: { building: "Engineering Building", campus: "Güney" },
  NB: { building: "Natuk Birkan", campus: "Güney" },
  NBB: { building: "Natuk Birkan Block B", campus: "Güney" },
  NBZ: { building: "Natuk Birkan Basement", campus: "Güney" },
  ALH: { building: "Albert Long Hall", campus: "Güney" },
  DODGE: { building: "Dodge Hall Gym", campus: "Güney" },
  DOGE: { building: "Dodge Hall Gym", campus: "Güney" },
  SOC: { building: "Sociology Seminar Rooms", campus: "Güney" },
  ATA: { building: "Atatürk Institute", campus: "Güney" },
  GYD: { building: "Güney YADYOK", campus: "Güney" },
  SC: { building: "Science Hall", campus: "Güney" },
  FED: { building: "Arts & Sciences", campus: "Güney" },

  // Hisar Kampüs
  HKB: { building: "Hisar Campus Block B", campus: "Hisar" },
  HKC: { building: "Hisar Campus Block C", campus: "Hisar" },
  HKA: { building: "Hisar Campus Block A", campus: "Hisar" },
  HKD: { building: "Hisar Campus Block D", campus: "Hisar" },
  HB: { building: "Hisar Block B", campus: "Hisar" },
  HC: { building: "Hisar Block C", campus: "Hisar" },
  HA: { building: "Hisar Block A", campus: "Hisar" },
  HD: { building: "Hisar Block D", campus: "Hisar" },
  HH: { building: "Hisar Hall", campus: "Hisar" },
  HİSAR: { building: "Hisar Campus", campus: "Hisar" },

  // Uçaksavar Kampüs
  GKM: { building: "Garanti Culture Center", campus: "Uçaksavar" },
  UÇAKSAVAR: { building: "Uçaksavar Athletic Field", campus: "Uçaksavar" },
  UÇAKS: { building: "Uçaksavar Athletic Field", campus: "Uçaksavar" },

  // Kandilli Kampüs
  KANDİLLİ: { building: "Kandilli Observatory", campus: "Kandilli" },
  KOERI: { building: "Kandilli Observatory", campus: "Kandilli" },
  BME: { building: "Biomedical Institute", campus: "Kandilli" },

  // Sarıtepe Kampüs (Kilyos)
  KLY: { building: "Sarıtepe Prep Hall", campus: "Kilyos" },
  KİLYOS: { building: "Sarıtepe Campus", campus: "Kilyos" },
  YYD: { building: "Sarıtepe YADYOK", campus: "Kilyos" }
};

export function resolveRoomLocation(roomName?: string | null, explicitBuilding?: string | null): LocationInfo {
  if (!roomName || !roomName.trim()) {
    return { building: explicitBuilding?.trim() || "General / Campus", campus: "Campus" };
  }

  const clean = roomName.trim();
  const upper = clean.toUpperCase();

  if (upper.includes("ONLINE") || upper.includes("UZAKTAN") || upper.includes("VIRTUAL") || upper.includes("WEB")) {
    return { building: "Online / Remote", campus: "Virtual" };
  }

  const match = clean.match(/^([A-Za-zÇĞİÖŞÜçğıöşü]+)/);
  if (match) {
    const prefix = match[1].toUpperCase();
    if (ROOM_LOCATION_REGISTRY[prefix]) {
      const reg = ROOM_LOCATION_REGISTRY[prefix];
      return {
        building: explicitBuilding?.trim() || reg.building,
        campus: reg.campus
      };
    }
  }

  if (explicitBuilding && explicitBuilding.trim()) {
    const bClean = explicitBuilding.trim();
    const bUpper = bClean.toUpperCase();
    if (["NEW HALL", "KARE", "EDUCATION", "EĞİTİM", "KUZEY", "COMPUTER", "ETA", "YERLICI"].some(w => bUpper.includes(w))) {
      return { building: bClean, campus: "Kuzey" };
    }
    if (["FREELY", "JOHN", "ANDERSON", "WASHBURN", "ENGINEERING", "NATUK", "GÜNEY", "SOUTH"].some(w => bUpper.includes(w))) {
      return { building: bClean, campus: "Güney" };
    }
    if (bUpper.includes("HISAR")) return { building: bClean, campus: "Hisar" };
    if (bUpper.includes("UÇAKSAVAR") || bUpper.includes("GARANTI")) return { building: bClean, campus: "Uçaksavar" };
    if (bUpper.includes("KANDİLLİ") || bUpper.includes("KANDILLI")) return { building: bClean, campus: "Kandilli" };
    if (bUpper.includes("KİLYOS") || bUpper.includes("SARITEPE")) return { building: bClean, campus: "Kilyos" };
    return { building: bClean, campus: "Campus" };
  }

  if (upper.startsWith("H")) return { building: `Hisar Building (${clean})`, campus: "Hisar" };
  if (upper.startsWith("K") && !upper.startsWith("KAND") && !upper.startsWith("KİL")) {
    return { building: `Kuzey Building (${clean})`, campus: "Kuzey" };
  }
  if (upper.startsWith("M") || upper.startsWith("T")) {
    return { building: `Güney Building (${clean})`, campus: "Güney" };
  }

  return {
    building: match ? `Building ${match[1].toUpperCase()}` : "General / Campus",
    campus: "Campus"
  };
}

export function isInterCampusCommute(campusA?: string | null, campusB?: string | null): boolean {
  if (!campusA || !campusB) return false;
  if (campusA === campusB) return false;
  if (campusA === "Virtual" || campusB === "Virtual") return false;
  if (campusA === "Campus" || campusB === "Campus") return false;
  return true;
}
