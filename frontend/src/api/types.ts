export type TerminStatus =
  | "draft"
  | "ai_processing"
  | "ai_failed"
  | "pending_approval"
  | "objavljen";

export type SlotStatus = "slobodan" | "rezervisan";

export interface Termin {
  terminId: string;
  profesorId: string;
  profesorIme: string;
  predmet: string;
  datum: string;
  vremeOd: string;
  vremeDo: string;
  trajanjeSlot: number;
  brojSlotova: number;
  status: TerminStatus;
  description?: string | null;
  hasMaterials: boolean;
  hasQA: boolean;
  maxStudenataPoSlotu?: number | null;
  rezimeGeneratedAt?: string | null;
  rezimeStatus?: "generated" | "csv_only" | "failed" | null;
}

export interface SlotStudent {
  studentId: string;
  studentIme: string;
  joinedAt: string;
}

export interface Slot {
  slotIndex: string;
  vremeOd: string;
  vremeDo: string;
  status: SlotStatus;
  studenti?: SlotStudent[];
  brojStudenata?: number;
}

export interface Material {
  materialId: string;
  fileName: string;
  fileType: "pdf" | "pptx" | "image";
  s3Key: string;
  s3Bucket: string;
  sizeBytes: number;
  uploadedAt?: string | null;
  processedAt?: string | null;
  processingError?: string | null;
}

export interface Question {
  questionId: string;
  terminId: string;
  pitanje: string;
  odgovor: string;
  tagovi: string[];
  predmet: string;
  profesorIme: string;
  terminDatum: string;
  approved: boolean;
  source: "ai" | "manual";
}

export type SearchMode = "hybrid" | "tag" | "semantic";
export type MatchType = "tag" | "semantic" | "hybrid";

export interface SearchResult extends Question {
  matchedTags: string[];
  /** 0..1 normalized RRF score (V3) */
  score: number;
  matchType: MatchType;
}

export type AiTutorConfidence = "high" | "medium" | "low";

export interface AiTutorResponse {
  odgovor: string;
  confidence: AiTutorConfidence;
  sources: string[];
  preporukaZakazivanja: boolean;
}

export interface Reservation {
  terminId: string;
  slotIndex: string;
  vremeOd: string;
  vremeDo: string;
  datum: string;
  predmet: string;
  profesorIme: string;
  joinedAt?: string;
  brojStudenata?: number;
}

export interface ProfMojiTermin {
  terminId: string;
  predmet: string;
  datum: string;
  vremeOd: string;
  vremeDo: string;
  status: TerminStatus;
  brojSlotova: number;
  rezervisanih: number;
  hasMaterials: boolean;
  hasQA: boolean;
  maxStudenataPoSlotu?: number | null;
  rezimeGeneratedAt?: string | null;
  rezimeStatus?: "generated" | "csv_only" | "failed" | "regenerating" | null;
}
