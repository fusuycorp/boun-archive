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

const PLACEHOLDER_MARKERS = new Set(["N/A", "TBA", "UNKNOWN", "UNASSIGNED", "NONE", "NULL"]);
const VIRTUAL_KEYWORDS = ["ONLINE", "UZAKTAN", "VIRTUAL", "WEB", "ZOOM"];

const EXPLICIT_BUILDING_CAMPUS_RULES: ReadonlyArray<{ campus: string; keywords: readonly string[] }> = [
  { campus: "Kuzey", keywords: ["NEW HALL", "KARE", "EDUCATION", "EĞİTİM", "KUZEY", "COMPUTER", "ETA", "YERLICI", "BİM"] },
  { campus: "Güney", keywords: ["FREELY", "JOHN", "ANDERSON", "WASHBURN", "ENGINEERING", "NATUK", "HAMLIN", "GÜNEY", "SOUTH"] },
  { campus: "Hisar", keywords: ["HISAR", "HİSAR"] },
  { campus: "Uçaksavar", keywords: ["UÇAKSAVAR", "GARANTI", "ŞAHENK"] },
  { campus: "Kandilli", keywords: ["KANDİLLİ", "KANDILLI"] },
  { campus: "Kilyos", keywords: ["KİLYOS", "KILYOS", "SARITEPE"] }
];

const PREFIX_CAMPUS_RULES: ReadonlyArray<{
  campus: string;
  labelPrefix: string;
  prefixes: readonly string[];
  excluded?: readonly string[];
}> = [
  { campus: "Kandilli", labelPrefix: "Kandilli Building", prefixes: ["BME", "KOERI", "KAND"] },
  { campus: "Kilyos", labelPrefix: "Kilyos Building", prefixes: ["KLY", "KİL", "KIL"] },
  { campus: "Güney", labelPrefix: "Hamlin Hall", prefixes: ["HH", "HAML", "HÜL", "HUL"] },
  { campus: "Hisar", labelPrefix: "Hisar Building", prefixes: ["HK", "HB", "HC", "HA", "HD", "HİS", "HIS"] },
  { campus: "Kuzey", labelPrefix: "Kuzey Building", prefixes: ["EF", "NH", "BM", "ETA", "VY", "K"], excluded: ["BME", "KAND", "KOERI", "KLY", "KİL", "KIL"] },
  { campus: "Güney", labelPrefix: "Güney Building", prefixes: ["M", "T", "JF", "İB", "IB", "NB"], excluded: ["MBG"] }
];

function inferCampusFromBuildingName(buildingClean: string): string {
  const bUpper = buildingClean.toUpperCase();
  const matched = EXPLICIT_BUILDING_CAMPUS_RULES.find((rule) =>
    rule.keywords.some((kw) => bUpper.includes(kw))
  );
  return matched ? matched.campus : "Other";
}

function inferCampusByPrefix(upper: string, clean: string): LocationInfo | null {
  for (const rule of PREFIX_CAMPUS_RULES) {
    if (rule.excluded?.some((ex) => upper.startsWith(ex))) continue;
    if (rule.prefixes.some((p) => upper.startsWith(p))) {
      return { building: `${rule.labelPrefix} (${clean})`, campus: rule.campus };
    }
  }
  return null;
}

export function resolveRoomLocation(roomName?: string | null, explicitBuilding?: string | null): LocationInfo {
  const bClean = explicitBuilding?.trim() || "";
  const clean = roomName?.trim() || "";
  const upper = clean.toUpperCase();

  if (!clean || PLACEHOLDER_MARKERS.has(upper)) {
    return {
      building: bClean || "Unassigned",
      campus: bClean ? inferCampusFromBuildingName(bClean) : "Other"
    };
  }
  if (VIRTUAL_KEYWORDS.some((kw) => upper.includes(kw))) {
    return { building: "Online / Remote", campus: "Virtual" };
  }

  const match = clean.match(/^([A-Za-zÇĞİÖŞÜçğıöşü]+)/);
  const reg = match ? ROOM_LOCATION_REGISTRY[match[1].toUpperCase()] : undefined;
  if (reg) {
    return { building: bClean || reg.building, campus: reg.campus };
  }
  if (bClean) {
    return { building: bClean, campus: inferCampusFromBuildingName(bClean) };
  }

  return inferCampusByPrefix(upper, clean) ?? {
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
