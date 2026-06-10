export interface Skill {
  id: string;
  name: string;
  type: "basic" | "extra" | "unique" | "ultimate";
  level: "0★" | "1★" | "2★" | "3★" | "4★" | "5★" | "6★";
  description: string;
  prerequisites: string[];
  derivatives: string[];
  conditions: string;
  evidence: EvidenceEntry[];
  knownAgents: string[];
  status: "provisional" | "validated" | "disputed" | "deprecated";
  createdAt: string;
  updatedAt: string;
  version: string;
  demerits?: DemeritId[];
}

export type DemeritId =
  | "niche-integration"
  | "experimental-feature"
  | "heavyweight-dependency";

export interface EvidenceEntry {
  class: "A" | "B" | "C";
  source: string;
  evaluator: string;
  date: string;
  notes?: string;
  source_type?: "manual" | "mcp-registry" | "npm" | "vscode-marketplace" | "huggingface";
}

export interface Edge {
  sourceSkillId: string;
  targetSkillId: string;
  edgeType: "prerequisite" | "corequisite" | "enhances";
  condition: string;
  levelFloor: string;
  evidenceRefs: string[];
}

export interface GaiaGraph {
  $schema?: string;
  version: string;
  generatedAt: string;
  meta: {
    typeLabels: Record<string, string>;
    levelLabels: Record<string, string>;
  };
  skills: Skill[];
  edges: Edge[];
}

export interface UnlockedSkill {
  skillId: string;
  level: string;
  unlockedAt: string;
  unlockedIn: string;
  combinedFrom: string[];
}

export interface PendingCombination {
  detectedSkills: string[];
  candidateResult: string;
  levelFloor: string;
  promptedAt: string;
}

export interface UserSkillTree {
  userId: string;
  updatedAt: string;
  unlockedSkills: UnlockedSkill[];
  pendingCombinations: PendingCombination[];
  stats: {
    totalUnlocked: number;
    deepestLineage: number;
  };
}

export interface GaiaConfig {
  gaiaUser: string;
  gaiaRegistryRef: string;
  localRegistryPath?: string;
  scanPaths: string[];
  autoPromptCombinations: boolean;
  lastScan?: string;
  installedNamedSkills?: InstalledNamedSkill[];
}

export interface FusionCandidate {
  candidateResult: string;
  levelFloor: string;
  detectedSkills: string[];
  missingSkills: string[];
  status: "ready" | "one_away" | "partial";
}

export interface NamedSkill {
  id: string;
  name: string;
  contributor: string;
  origin: boolean;
  role?: "origin" | "variant";
  genericSkillRef: string;
  status: "awakened" | "named";
  level: "2★" | "3★" | "4★" | "5★" | "6★";
  description: string;
  links?: {
    github?: string;
    agentskills?: string;
    docs?: string;
  };
  tags?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface NamedIndex {
  generatedAt: string;
  buckets: Record<string, NamedSkill[]>;
}

export interface EmbeddingEntry {
  id: string;
  vector: number[];
}

export interface EmbeddingsStore {
  model: string;
  dimensions: number;
  generatedAt: string;
  entries: EmbeddingEntry[];
}

export interface InstalledNamedSkill {
  id: string;
  installedAt: string;
  sourceRef: string;
  sha256?: string;
}

export interface InstallManifest {
  installed: InstalledNamedSkill[];
}
