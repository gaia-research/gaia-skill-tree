/**
 * Gaia Registry API — TypeScript type definitions
 * Derived from docs/api/v1/openapi.json (OpenAPI 3.1)
 */

// ─── Health ────────────────────────────────────────────────────────────────────

export interface Health {
  ok: boolean;
  version: string;
  registryGeneratedAt: string;
  namedSkillsCount: number;
}

// ─── Skills ────────────────────────────────────────────────────────────────────

export type TrustGrade = "S" | "A" | "B" | "C" | "D" | "F";
export type SkillType = "basic" | "extra" | "unique" | "ultimate";
export type EvidenceClass = "A" | "B" | "C";
export type SkillStatus = "named" | "generic" | "pending";

export interface SkillLinks {
  self: string;
  contributor?: string;
  list?: string;
}

export interface SkillSummary {
  id: string;
  name: string;
  level: string;
  trustMagnitude: number;
  overallTrustGrade: TrustGrade;
  contributor: string;
  type: SkillType;
  _links: {
    self: string;
  };
}

export interface PaginationLinks {
  self: string;
  next?: string;
  prev?: string;
}

export interface SkillListPage {
  skills: SkillSummary[];
  page: number;
  totalPages: number;
  totalSkills: number;
  _links: PaginationLinks;
}

export interface EvidenceEntry {
  type: string;
  class: EvidenceClass;
  source: string;
  evaluator?: string;
  date?: string;
  notes?: string;
  grade: TrustGrade;
  trustNumber?: number;
}

export interface ApexGateStatus {
  aGradedOriginsGte5?: boolean;
  sourceTenureDaysGte180AorS?: boolean;
  directNestedSuiteGte1?: boolean;
  depth2OnlyReachableGte1?: boolean;
  overallGradeS?: boolean;
  apexPromotionPrSigned?: boolean;
  crossOrgVerifier?: boolean | null;
  systemWideCap?: boolean | null;
}

export interface SkillDetail extends SkillSummary {
  status?: SkillStatus;
  title?: string;
  genericSkillRef?: string;
  description?: string;
  tags?: string[];
  origin?: boolean | null;
  evidence?: EvidenceEntry[];
  apexGateStatus?: ApexGateStatus;
  _links: SkillLinks;
}

// ─── Contributors ──────────────────────────────────────────────────────────────

export interface ContributorSummary {
  handle: string;
  namedSkills: number;
  topSkill?: {
    id: string;
    level: string;
    trustMagnitude: number;
  };
  prestigeScore: number;
  _links: {
    self: string;
  };
}

export interface ContributorList {
  contributors: ContributorSummary[];
}

export interface ContributorDetail {
  handle: string;
  namedSkills: SkillSummary[];
}

// ─── Leaderboard ───────────────────────────────────────────────────────────────

export interface GradeDistribution {
  total: number;
  S: number;
  A: number;
  B: number;
  C: number;
  ungraded: number;
  floor?: number;
  up?: number;
}

export interface LeaderboardRow {
  id: string;
  trustMagnitude: number;
  grade: TrustGrade | "ungraded";
  level: string;
}

export interface Leaderboard {
  distribution: GradeDistribution;
  rows: LeaderboardRow[];
}

// ─── Evidence Types ────────────────────────────────────────────────────────────

export interface EvidenceType {
  id: string;
  description: string;
  magnitude?: string;
  weight: number;
  cap?: number | string | null;
  gradeCeiling?: string;
  freshness?: string;
  selfProducible?: boolean;
  allowedLayers?: Array<"named" | "generic">;
  notes?: string;
}

export interface EvidenceTypeCatalogue {
  types: EvidenceType[];
}

// ─── Search Index ──────────────────────────────────────────────────────────────

export interface SearchIndexEntry {
  id: string;
  name: string;
  contributor: string;
  level?: string;
  grade?: string;
  trustMagnitude?: number;
  tokens: string[];
}

export type SearchIndex = SearchIndexEntry[];

// ─── Trending ──────────────────────────────────────────────────────────────────

export type TrendingWindow = "7d" | "30d";

export interface TrendingEntry {
  id: string;
  name: string;
  contributor: string;
  delta: number;
  trustMagnitude: number;
  grade?: string;
}

export interface Trending {
  window: TrendingWindow;
  entries: TrendingEntry[];
}

// ─── Heroes ────────────────────────────────────────────────────────────────────

export interface Hero {
  handle: string;
  title?: string;
  skills: number;
  prestigeScore: number;
}

export interface Heroes {
  heroes: Hero[];
}

// ─── Client Options ────────────────────────────────────────────────────────────

export interface GaiaClientOptions {
  /** Base URL of the Gaia site. Default: https://gaiaskilltree.com */
  baseUrl?: string;
  /** Custom fetch implementation (for testing or Node <18 polyfills) */
  fetch?: typeof globalThis.fetch;
}
