/**
 * Campus and Building Topology Registry for Boğaziçi University
 * 
 * Invariants:
 * - JF (John Freely Hall) is in Güney
 * - EF (Education Faculty) is in Kuzey
 * - HH (Hamlin Hall) is in Güney
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
  ET: { building: "ETA Building", campus: "Kuzey" },
  KP: { building: "Kuzey Park", campus: "Kuzey" },
  KPARK: { building: "Kuzey Park", campus: "Kuzey" },
  PARK: { building: "Kuzey Park", campus: "Kuzey" },
  PARK1: { building: "Kuzey Park", campus: "Kuzey" },
  PARK2: { building: "Kuzey Park", campus: "Kuzey" },
  VY: { building: "Vedat Yerlici", campus: "Kuzey" },
  VYKM: { building: "Vedat Yerlici Center", campus: "Kuzey" },
  VB: { building: "Vedat Yerlici", campus: "Kuzey" },
  KYD: { building: "Kuzey YADYOK", campus: "Kuzey" },
  SL: { building: "Student Labs", campus: "Kuzey" },
  BİM: { building: "Bilgi İşlem Merkezi", campus: "Kuzey" },
  BIM: { building: "Bilgi İşlem Merkezi", campus: "Kuzey" },
  KGYM: { building: "Kuzey Spor Salonu", campus: "Kuzey" },

  // Güney Kampüs (South)
  JF: { building: "John Freely Hall", campus: "Güney" },
  HH: { building: "Hamlin Hall", campus: "Güney" },
  HAMLİN: { building: "Hamlin Hall", campus: "Güney" },
  HAMLIN: { building: "Hamlin Hall", campus: "Güney" },
  TB: { building: "Basic Sciences (Anderson)", campus: "Güney" },
  TBA: { building: "Anderson Hall", campus: "Güney" },
  TBD: { building: "Basic Sciences Block D", campus: "Güney" },
  AND: { building: "Anderson Hall", campus: "Güney" },
  IB: { building: "Washburn Hall (İİBF)", campus: "Güney" },
  İB: { building: "Washburn Hall (İİBF)", campus: "Güney" },
  İBRAHİM: { building: "İbrahim Bodur Oditoryumu", campus: "Güney" },
  IBRAHIM: { building: "İbrahim Bodur Oditoryumu", campus: "Güney" },
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
  ÖFB: { building: "Öğrenci Faaliyetleri Binası", campus: "Güney" },
  OFB: { building: "Öğrenci Faaliyetleri Binası", campus: "Güney" },
  ÖZGER: { building: "Özger Arnas Salonu", campus: "Güney" },
  OZGER: { building: "Özger Arnas Salonu", campus: "Güney" },
  HÜLYA: { building: "Hülya Sanat Atölyesi", campus: "Güney" },
  HULYA: { building: "Hülya Sanat Atölyesi", campus: "Güney" },
  REVİR: { building: "Güney Revir", campus: "Güney" },
  REVIR: { building: "Güney Revir", campus: "Güney" },
  GÜNEY: { building: "Güney Kampüs", campus: "Güney" },
  GUNEY: { building: "Güney Kampüs", campus: "Güney" },

  // Hisar Kampüs
  HKB: { building: "Hisar Campus Block B", campus: "Hisar" },
  HKC: { building: "Hisar Campus Block C", campus: "Hisar" },
  HKA: { building: "Hisar Campus Block A", campus: "Hisar" },
  HKD: { building: "Hisar Campus Block D", campus: "Hisar" },
  HB: { building: "Hisar Block B", campus: "Hisar" },
  HC: { building: "Hisar Block C", campus: "Hisar" },
  HA: { building: "Hisar Block A", campus: "Hisar" },
  HD: { building: "Hisar Block D", campus: "Hisar" },
  HİSAR: { building: "Hisar Campus", campus: "Hisar" },
  HISAR: { building: "Hisar Campus", campus: "Hisar" },

  // Uçaksavar Kampüs
  GKM: { building: "Garanti Culture Center", campus: "Uçaksavar" },
  AYHAN: { building: "Ayhan Şahenk Salonu", campus: "Uçaksavar" },
  UÇAKSAVAR: { building: "Uçaksavar Athletic Field", campus: "Uçaksavar" },
  UÇAKS: { building: "Uçaksavar Athletic Field", campus: "Uçaksavar" },
  PARKE: { building: "Uçaksavar Spor Salonu", campus: "Uçaksavar" },

  // Kandilli Kampüs
  KANDİLLİ: { building: "Kandilli Observatory", campus: "Kandilli" },
  KANDILLI: { building: "Kandilli Observatory", campus: "Kandilli" },
  KOERI: { building: "Kandilli Observatory", campus: "Kandilli" },
  BME: { building: "Biomedical Institute", campus: "Kandilli" },
  AZ: { building: "Aziz Sancar Binası (BME)", campus: "Kandilli" },

  // Sarıtepe Kampüs (Kilyos)
  KLY: { building: "Sarıtepe Prep Hall", campus: "Kilyos" },
  KİLYOS: { building: "Sarıtepe Campus", campus: "Kilyos" },
  KILYOS: { building: "Sarıtepe Campus", campus: "Kilyos" },
  YYD: { building: "Sarıtepe YADYOK", campus: "Kilyos" }
};

export function resolveRoomLocation(roomName?: string | null, explicitBuilding?: string | null): LocationInfo {
  if (!roomName || !roomName.trim()) {
    return { building: explicitBuilding?.trim() || "Unassigned / Other", campus: "Other" };
  }

  const clean = roomName.trim();
  const upper = clean.toUpperCase();

  if (upper.includes("ONLINE") || upper.includes("UZAKTAN") || upper.includes("VIRTUAL") || upper.includes("WEB") || upper.includes("ZOOM")) {
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
    if (["NEW HALL", "KARE", "EDUCATION", "EĞİTİM", "KUZEY", "COMPUTER", "ETA", "YERLICI", "BİM"].some(w => bUpper.includes(w))) {
      return { building: bClean, campus: "Kuzey" };
    }
    if (["FREELY", "JOHN", "ANDERSON", "WASHBURN", "ENGINEERING", "NATUK", "HAMLIN", "GÜNEY", "SOUTH"].some(w => bUpper.includes(w))) {
      return { building: bClean, campus: "Güney" };
    }
    if (bUpper.includes("HISAR") || bUpper.includes("HİSAR")) return { building: bClean, campus: "Hisar" };
    if (bUpper.includes("UÇAKSAVAR") || bUpper.includes("GARANTI") || bUpper.includes("ŞAHENK")) return { building: bClean, campus: "Uçaksavar" };
    if (bUpper.includes("KANDİLLİ") || bUpper.includes("KANDILLI")) return { building: bClean, campus: "Kandilli" };
    if (bUpper.includes("KİLYOS") || bUpper.includes("KILYOS") || bUpper.includes("SARITEPE")) return { building: bClean, campus: "Kilyos" };
    return { building: bClean, campus: "Other" };
  }

  // Specific campus prefix rules
  if (upper.startsWith("HH") || upper.startsWith("HAML") || upper.startsWith("HÜL") || upper.startsWith("HUL")) {
    return { building: `Hamlin Hall (${clean})`, campus: "Güney" };
  }
  if (upper.startsWith("HK") || upper.startsWith("HB") || upper.startsWith("HC") || upper.startsWith("HA") || upper.startsWith("HD") || upper.startsWith("HİS") || upper.startsWith("HIS")) {
    return { building: `Hisar Building (${clean})`, campus: "Hisar" };
  }
  if (upper.startsWith("K") && !upper.startsWith("KAND") && !upper.startsWith("KİL") && !upper.startsWith("KIL")) {
    return { building: `Kuzey Building (${clean})`, campus: "Kuzey" };
  }
  if (upper.startsWith("M") || upper.startsWith("T") || upper.startsWith("JF") || upper.startsWith("İB") || upper.startsWith("IB") || upper.startsWith("NB")) {
    return { building: `Güney Building (${clean})`, campus: "Güney" };
  }

  return {
    building: match ? `Building ${match[1].toUpperCase()}` : "Unassigned / Other",
    campus: "Other"
  };
}

export function isInterCampusCommute(campusA?: string | null, campusB?: string | null): boolean {
  if (!campusA || !campusB) return false;
  if (campusA === campusB) return false;
  if (campusA === "Virtual" || campusB === "Virtual") return false;
  if (campusA === "Other" || campusB === "Other" || campusA === "Campus" || campusB === "Campus") return false;
  return true;
}
