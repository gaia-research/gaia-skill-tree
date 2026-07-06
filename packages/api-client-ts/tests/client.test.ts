import { describe, it, expect, vi, beforeEach } from "vitest";
import { GaiaClient, GaiaApiError } from "../src/client.js";
import type {
  Health,
  SkillListPage,
  SkillDetail,
  ContributorList,
  ContributorDetail,
  Leaderboard,
  EvidenceTypeCatalogue,
  SearchIndex,
  Trending,
  Heroes,
} from "../src/types.js";

// ─── Fixtures ──────────────────────────────────────────────────────────────────

const HEALTH_FIXTURE: Health = {
  ok: true,
  version: "5.6.0",
  registryGeneratedAt: "2026-06-26",
  namedSkillsCount: 139,
};

const SKILLS_PAGE_FIXTURE: SkillListPage = {
  skills: [
    {
      id: "garrytan/gstack",
      name: "Gstack",
      level: "5★",
      trustMagnitude: 589.32,
      overallTrustGrade: "S",
      contributor: "garrytan",
      type: "ultimate",
      _links: { self: "/api/v1/skills/garrytan/gstack.json" },
    },
  ],
  page: 1,
  totalPages: 3,
  totalSkills: 139,
  _links: {
    self: "/api/v1/skills/index.json",
    next: "/api/v1/skills/page-2.json",
  },
};

const SKILL_DETAIL_FIXTURE: SkillDetail = {
  id: "garrytan/gstack",
  name: "Gstack",
  level: "5★",
  trustMagnitude: 589.32,
  overallTrustGrade: "S",
  contributor: "garrytan",
  type: "ultimate",
  status: "named",
  title: "Gstack — Garry Tan's Full-Stack Agent Suite",
  description: "A comprehensive agent orchestration framework.",
  tags: ["agent", "orchestration"],
  evidence: [
    {
      type: "repo",
      class: "A",
      source: "https://github.com/garrytan/gstack",
      grade: "B",
      trustNumber: 70.0,
    },
  ],
  _links: {
    self: "/api/v1/skills/garrytan/gstack.json",
    contributor: "/api/v1/contributors/garrytan.json",
    list: "/api/v1/skills/index.json",
  },
};

const CONTRIBUTORS_FIXTURE: ContributorList = {
  contributors: [
    {
      handle: "garrytan",
      namedSkills: 47,
      topSkill: { id: "garrytan/gstack", level: "5★", trustMagnitude: 589.32 },
      prestigeScore: 2996.5,
      _links: { self: "/api/v1/contributors/garrytan.json" },
    },
  ],
};

const CONTRIBUTOR_DETAIL_FIXTURE: ContributorDetail = {
  handle: "garrytan",
  namedSkills: [
    {
      id: "garrytan/gstack",
      name: "Gstack",
      level: "5★",
      trustMagnitude: 589.32,
      overallTrustGrade: "S",
      contributor: "garrytan",
      type: "ultimate",
      _links: { self: "/api/v1/skills/garrytan/gstack.json" },
    },
  ],
};

const LEADERBOARD_FIXTURE: Leaderboard = {
  distribution: { total: 249, S: 4, A: 42, B: 56, C: 77, ungraded: 70 },
  rows: [
    { id: "garrytan/gstack", trustMagnitude: 589.32, grade: "S", level: "5★" },
  ],
};

const EVIDENCE_TYPES_FIXTURE: EvidenceTypeCatalogue = {
  types: [
    {
      id: "github-stars-own",
      description: "Stars on the contributor's own repo",
      weight: 1.0,
      gradeCeiling: "S",
      selfProducible: true,
    },
  ],
};

const SEARCH_INDEX_FIXTURE: SearchIndex = [
  {
    id: "garrytan/gstack",
    name: "Gstack",
    contributor: "garrytan",
    level: "5★",
    grade: "S",
    trustMagnitude: 589.32,
    tokens: ["gstack", "garry", "tan", "agent"],
  },
];

const TRENDING_FIXTURE: Trending = {
  window: "7d",
  entries: [
    {
      id: "garrytan/gstack",
      name: "Gstack",
      contributor: "garrytan",
      delta: 12.5,
      trustMagnitude: 589.32,
      grade: "S",
    },
  ],
};

const HEROES_FIXTURE: Heroes = {
  heroes: [
    { handle: "garrytan", skills: 47, prestigeScore: 2996.5 },
  ],
};

// ─── Test helpers ──────────────────────────────────────────────────────────────

function mockFetch(data: unknown, status = 200): typeof globalThis.fetch {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Not Found",
    json: () => Promise.resolve(data),
  });
}

function createClient(fetchFn: typeof globalThis.fetch): GaiaClient {
  return new GaiaClient({ baseUrl: "https://gaiaskilltree.com", fetch: fetchFn });
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe("GaiaClient", () => {
  describe("constructor", () => {
    it("uses default base URL when none provided", async () => {
      const fetchFn = mockFetch(HEALTH_FIXTURE);
      const client = new GaiaClient({ fetch: fetchFn });
      await client.getHealth();
      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/health.json"
      );
    });

    it("strips trailing slashes from baseUrl", async () => {
      const fetchFn = mockFetch(HEALTH_FIXTURE);
      const client = new GaiaClient({
        baseUrl: "https://example.com///",
        fetch: fetchFn,
      });
      await client.getHealth();
      expect(fetchFn).toHaveBeenCalledWith(
        "https://example.com/api/v1/health.json"
      );
    });
  });

  describe("getHealth()", () => {
    it("fetches /api/v1/health.json and returns typed Health", async () => {
      const fetchFn = mockFetch(HEALTH_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.getHealth();

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/health.json"
      );
      expect(result).toEqual(HEALTH_FIXTURE);
      expect(result.ok).toBe(true);
      expect(result.namedSkillsCount).toBe(139);
    });
  });

  describe("listSkills()", () => {
    it("fetches page 1 at /api/v1/skills/index.json", async () => {
      const fetchFn = mockFetch(SKILLS_PAGE_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.listSkills();

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/skills/index.json"
      );
      expect(result.page).toBe(1);
      expect(result.skills).toHaveLength(1);
    });

    it("fetches page N at /api/v1/skills/page-N.json", async () => {
      const fetchFn = mockFetch({ ...SKILLS_PAGE_FIXTURE, page: 2 });
      const client = createClient(fetchFn);
      const result = await client.listSkills(2);

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/skills/page-2.json"
      );
      expect(result.page).toBe(2);
    });

    it("treats page <= 0 as page 1", async () => {
      const fetchFn = mockFetch(SKILLS_PAGE_FIXTURE);
      const client = createClient(fetchFn);
      await client.listSkills(0);

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/skills/index.json"
      );
    });
  });

  describe("getSkill()", () => {
    it("fetches /api/v1/skills/{contributor}/{skill}.json", async () => {
      const fetchFn = mockFetch(SKILL_DETAIL_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.getSkill("garrytan", "gstack");

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/skills/garrytan/gstack.json"
      );
      expect(result.id).toBe("garrytan/gstack");
      expect(result.evidence).toHaveLength(1);
    });

    it("URL-encodes path segments", async () => {
      const fetchFn = mockFetch(SKILL_DETAIL_FIXTURE);
      const client = createClient(fetchFn);
      await client.getSkill("user/name", "skill name");

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/skills/user%2Fname/skill%20name.json"
      );
    });
  });

  describe("listContributors()", () => {
    it("fetches /api/v1/contributors/index.json", async () => {
      const fetchFn = mockFetch(CONTRIBUTORS_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.listContributors();

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/contributors/index.json"
      );
      expect(result.contributors).toHaveLength(1);
      expect(result.contributors[0].handle).toBe("garrytan");
    });
  });

  describe("getContributor()", () => {
    it("fetches /api/v1/contributors/{handle}.json", async () => {
      const fetchFn = mockFetch(CONTRIBUTOR_DETAIL_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.getContributor("garrytan");

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/contributors/garrytan.json"
      );
      expect(result.handle).toBe("garrytan");
      expect(result.namedSkills).toHaveLength(1);
    });
  });

  describe("getLeaderboard()", () => {
    it("fetches /api/v1/leaderboard.json", async () => {
      const fetchFn = mockFetch(LEADERBOARD_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.getLeaderboard();

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/leaderboard.json"
      );
      expect(result.distribution.total).toBe(249);
      expect(result.rows).toHaveLength(1);
    });
  });

  describe("getEvidenceTypes()", () => {
    it("fetches /api/v1/evidence-types.json", async () => {
      const fetchFn = mockFetch(EVIDENCE_TYPES_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.getEvidenceTypes();

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/evidence-types.json"
      );
      expect(result.types).toHaveLength(1);
      expect(result.types[0].id).toBe("github-stars-own");
    });
  });

  describe("getSearchIndex()", () => {
    it("fetches /api/v1/search-index.json", async () => {
      const fetchFn = mockFetch(SEARCH_INDEX_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.getSearchIndex();

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/search-index.json"
      );
      expect(result).toHaveLength(1);
      expect(result[0].tokens).toContain("agent");
    });
  });

  describe("getTrending()", () => {
    it("fetches /api/v1/trending/7d.json by default", async () => {
      const fetchFn = mockFetch(TRENDING_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.getTrending();

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/trending/7d.json"
      );
      expect(result.window).toBe("7d");
    });

    it("fetches /api/v1/trending/30d.json when specified", async () => {
      const fetchFn = mockFetch({ ...TRENDING_FIXTURE, window: "30d" });
      const client = createClient(fetchFn);
      await client.getTrending("30d");

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/trending/30d.json"
      );
    });
  });

  describe("getHeroes()", () => {
    it("fetches /api/v1/heroes.json", async () => {
      const fetchFn = mockFetch(HEROES_FIXTURE);
      const client = createClient(fetchFn);
      const result = await client.getHeroes();

      expect(fetchFn).toHaveBeenCalledWith(
        "https://gaiaskilltree.com/api/v1/heroes.json"
      );
      expect(result.heroes).toHaveLength(1);
      expect(result.heroes[0].handle).toBe("garrytan");
    });
  });

  describe("error handling", () => {
    it("throws GaiaApiError on 404", async () => {
      const fetchFn = mockFetch(null, 404);
      const client = createClient(fetchFn);

      await expect(
        client.getSkill("nobody", "nonexistent")
      ).rejects.toThrow(GaiaApiError);

      try {
        await client.getSkill("nobody", "nonexistent");
      } catch (err) {
        expect(err).toBeInstanceOf(GaiaApiError);
        const apiErr = err as GaiaApiError;
        expect(apiErr.status).toBe(404);
        expect(apiErr.url).toContain("nobody");
        expect(apiErr.name).toBe("GaiaApiError");
      }
    });

    it("throws GaiaApiError on 500", async () => {
      const fetchFn = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: () => Promise.resolve({}),
      });
      const client = createClient(fetchFn);

      await expect(client.getHealth()).rejects.toThrow(GaiaApiError);
    });

    it("propagates network errors", async () => {
      const fetchFn = vi.fn().mockRejectedValue(new Error("Network timeout"));
      const client = createClient(fetchFn);

      await expect(client.getHealth()).rejects.toThrow("Network timeout");
    });
  });
});
