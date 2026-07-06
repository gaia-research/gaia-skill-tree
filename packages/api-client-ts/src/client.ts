import type {
  GaiaClientOptions,
  Health,
  SkillListPage,
  SkillDetail,
  ContributorList,
  ContributorDetail,
  Leaderboard,
  EvidenceTypeCatalogue,
  SearchIndex,
  TrendingWindow,
  Trending,
  Heroes,
} from "./types.js";

const DEFAULT_BASE_URL = "https://gaiaskilltree.com";

/**
 * GaiaClient — typed HTTP client for the Gaia Registry API.
 *
 * Zero runtime dependencies. Uses native `fetch` (Node 18+, all modern browsers).
 * All endpoints are static JSON files served via CDN — no auth required.
 *
 * @example
 * ```ts
 * import { GaiaClient } from '@gaia-registry/api-client';
 *
 * const gaia = new GaiaClient();
 * const health = await gaia.getHealth();
 * console.log(health.namedSkillsCount);
 * ```
 */
export class GaiaClient {
  private readonly baseUrl: string;
  private readonly fetchFn: typeof globalThis.fetch;

  constructor(options?: GaiaClientOptions) {
    this.baseUrl = (options?.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.fetchFn = options?.fetch ?? globalThis.fetch;
  }

  // ─── Internal ──────────────────────────────────────────────────────────────

  private async request<T>(path: string): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await this.fetchFn(url);

    if (!response.ok) {
      throw new GaiaApiError(
        `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        url
      );
    }

    return response.json() as Promise<T>;
  }

  // ─── Health ────────────────────────────────────────────────────────────────

  /**
   * Health check — returns API liveness, registry version, and generation timestamp.
   */
  async getHealth(): Promise<Health> {
    return this.request<Health>("/api/v1/health.json");
  }

  // ─── Skills ────────────────────────────────────────────────────────────────

  /**
   * List named skills (paginated). Page 1 is at index.json, page 2+ at page-N.json.
   * @param page Page number (1-indexed, default 1)
   */
  async listSkills(page: number = 1): Promise<SkillListPage> {
    const path =
      page <= 1
        ? "/api/v1/skills/index.json"
        : `/api/v1/skills/page-${page}.json`;
    return this.request<SkillListPage>(path);
  }

  /**
   * Get full detail for a single named skill.
   * @param contributor GitHub handle of the contributor
   * @param skill Skill slug (directory name)
   */
  async getSkill(contributor: string, skill: string): Promise<SkillDetail> {
    return this.request<SkillDetail>(
      `/api/v1/skills/${encodeURIComponent(contributor)}/${encodeURIComponent(skill)}.json`
    );
  }

  // ─── Contributors ──────────────────────────────────────────────────────────

  /**
   * List all contributors sorted by prestige score descending.
   */
  async listContributors(): Promise<ContributorList> {
    return this.request<ContributorList>("/api/v1/contributors/index.json");
  }

  /**
   * Get a contributor's full profile including all their named skills.
   * @param handle GitHub handle
   */
  async getContributor(handle: string): Promise<ContributorDetail> {
    return this.request<ContributorDetail>(
      `/api/v1/contributors/${encodeURIComponent(handle)}.json`
    );
  }

  // ─── Meta ──────────────────────────────────────────────────────────────────

  /**
   * Trust leaderboard — grade distribution and all skills ranked by Trust Magnitude.
   */
  async getLeaderboard(): Promise<Leaderboard> {
    return this.request<Leaderboard>("/api/v1/leaderboard.json");
  }

  /**
   * Evidence type catalogue — all recognised evidence types with formulas and weights.
   */
  async getEvidenceTypes(): Promise<EvidenceTypeCatalogue> {
    return this.request<EvidenceTypeCatalogue>("/api/v1/evidence-types.json");
  }

  /**
   * Search index — flat array of skills with pre-tokenised search terms.
   */
  async getSearchIndex(): Promise<SearchIndex> {
    return this.request<SearchIndex>("/api/v1/search-index.json");
  }

  /**
   * Trending skills over a time window.
   * @param window Time window: '7d' or '30d'
   */
  async getTrending(window: TrendingWindow = "7d"): Promise<Trending> {
    return this.request<Trending>(`/api/v1/trending/${window}.json`);
  }

  /**
   * Heroes — top contributors by prestige.
   */
  async getHeroes(): Promise<Heroes> {
    return this.request<Heroes>("/api/v1/heroes.json");
  }
}

// ─── Error class ───────────────────────────────────────────────────────────────

/**
 * Thrown when the API returns a non-2xx response.
 */
export class GaiaApiError extends Error {
  readonly status: number;
  readonly url: string;

  constructor(message: string, status: number, url: string) {
    super(message);
    this.name = "GaiaApiError";
    this.status = status;
    this.url = url;
  }
}
