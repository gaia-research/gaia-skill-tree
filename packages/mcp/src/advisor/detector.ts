import { AbstractAdvisor, type AdvisorContext } from "./types.js";

const TOOL_SKILL_MAP: Record<string, string[]> = {
  web_search: ["web-search"],
  brave_search: ["web-search"],
  brave_web_search: ["web-search"],
  google_search: ["web-search"],
  tavily_search: ["web-search"],
  search: ["web-search"],
  fetch: ["parse-html"],
  fetch_url: ["parse-html"],
  scrape: ["web-scrape"],
  read_file: ["parse-json"],
  read: ["parse-json"],
  write_file: ["generate-text"],
  bash: ["execute-bash"],
  run_command: ["execute-bash"],
  execute_command: ["execute-bash"],
  terminal: ["execute-bash"],
  shell: ["execute-bash"],
  code_generation: ["code-generation"],
  generate_code: ["code-generation"],
  edit: ["code-generation"],
  embed: ["embed-text"],
  embed_text: ["embed-text"],
  create_embedding: ["embed-text"],
  chunk: ["chunk-document"],
  split_text: ["chunk-document"],
  extract: ["extract-entities"],
  extract_entities: ["extract-entities"],
  ner: ["extract-entities"],
  summarize: ["summarize"],
  summarize_text: ["summarize"],
  classify: ["classify"],
  categorize: ["classify"],
  tokenize: ["tokenize"],
  retrieve: ["retrieve"],
  vector_search: ["retrieve"],
  similarity_search: ["retrieve"],
  parse_json: ["parse-json"],
  parse_html: ["parse-html"],
  html_to_text: ["parse-html"],
  evaluate: ["evaluate-output"],
  score: ["score-relevance"],
  rank: ["rank"],
  rerank: ["rank"],
  plan: ["plan-decompose"],
  decompose: ["plan-decompose"],
  route: ["route-intent"],
  format: ["format-output"],
  diff: ["diff-content"],
  cite: ["cite-sources"],
  reference: ["cite-sources"],
};

export interface SkillDetectionResult {
  fromTools: string[];
  fromSignals: string[];
  allDetected: string[];
  context: AdvisorContext;
}

const PATTERN_MAP: Array<[RegExp, string[]]> = [
  [/embed/i, ["embed-text"]],
  [/chunk/i, ["chunk-document"]],
  [/extract/i, ["extract-entities"]],
  [/summar/i, ["summarize"]],
  [/search/i, ["web-search"]],
  [/scrape|crawl/i, ["web-scrape"]],
  [/parse.*html/i, ["parse-html"]],
  [/parse.*json/i, ["parse-json"]],
  [/generat.*code/i, ["code-generation"]],
  [/execut|bash|shell|terminal/i, ["execute-bash"]],
  [/retriev|vector/i, ["retrieve"]],
  [/classif|categoriz/i, ["classify"]],
  [/format/i, ["format-output"]],
];

function detectSkillsFromToolNames(toolNames: string[]): string[] {
  const detected = new Set<string>();

  for (const tool of toolNames) {
    const normalized = tool.toLowerCase().replace(/[-\s]/g, "_");

    const direct = TOOL_SKILL_MAP[normalized];
    if (direct) {
      for (const skill of direct) detected.add(skill);
      continue;
    }

    for (const [pattern, skills] of PATTERN_MAP) {
      if (pattern.test(tool)) {
        for (const skill of skills) detected.add(skill);
      }
    }
  }

  return [...detected];
}

function detectSkillsFromSignalText(signals: string[]): string[] {
  const detected = new Set<string>();
  const joined = signals.join(" ").toLowerCase();

  for (const [pattern, skills] of PATTERN_MAP) {
    if (pattern.test(joined)) {
      for (const skill of skills) detected.add(skill);
    }
  }

  return [...detected];
}

export class SkillDetector extends AbstractAdvisor<SkillDetectionResult> {
  constructor() {
    super("skill-detector");
  }

  analyze(context: AdvisorContext): SkillDetectionResult {
    const fromTools = detectSkillsFromToolNames(context.connectedTools ?? []);
    const fromSignals = detectSkillsFromSignalText(context.projectSignals ?? []);
    const allDetected = this.dedupe([
      ...this.detectedSkillIds(context),
      ...fromTools,
      ...fromSignals,
    ]);

    return {
      fromTools,
      fromSignals,
      allDetected,
      context: {
        ...context,
        detectedSkillIds: allDetected,
      },
    };
  }
}

export const skillDetector = new SkillDetector();

export function detectSkillsFromTools(toolNames: string[]): string[] {
  return skillDetector.analyze({ connectedTools: toolNames }).fromTools;
}

export function detectSkillsFromSignals(signals: string[]): string[] {
  return skillDetector.analyze({ projectSignals: signals }).fromSignals;
}
