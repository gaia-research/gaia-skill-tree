import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import * as fs from "node:fs";

vi.mock("node:fs", () => ({
  readFileSync: vi.fn(),
  writeFileSync: vi.fn(),
  mkdirSync: vi.fn(),
  existsSync: vi.fn(),
  statSync: vi.fn(),
  unlinkSync: vi.fn()
}));

import { getCached, getEtag, putCache } from "../src/config/cache.js";

describe("cache utility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("getCached", () => {
    it("returns null if cache file does not exist", () => {
      vi.mocked(fs.existsSync).mockReturnValue(false);
      expect(getCached("test-key")).toBeNull();
    });

    it("returns null if cache file read fails", () => {
      vi.mocked(fs.existsSync).mockReturnValue(true);
      vi.mocked(fs.statSync).mockReturnValue({ mtimeMs: Date.now() } as any);
      vi.mocked(fs.readFileSync).mockImplementation(() => {
        throw new Error("Read failed");
      });

      expect(getCached("test-key")).toBeNull();
    });

    it("returns data and stale: false if within TTL", () => {
      const now = 1000000;
      vi.setSystemTime(now);

      vi.mocked(fs.existsSync).mockReturnValue(true);
      // mtime is just 1 second ago
      vi.mocked(fs.statSync).mockReturnValue({ mtimeMs: now - 1000 } as any);
      vi.mocked(fs.readFileSync).mockReturnValue("cache-data");

      const result = getCached("test-key");
      expect(result).toEqual({ data: "cache-data", stale: false });
    });

    it("returns data and stale: true if outside TTL", () => {
      const now = 1000000;
      vi.setSystemTime(now);
      const CACHE_TTL_MS = 5 * 60 * 1000;

      vi.mocked(fs.existsSync).mockReturnValue(true);
      // mtime is just outside TTL
      vi.mocked(fs.statSync).mockReturnValue({ mtimeMs: now - CACHE_TTL_MS - 1 } as any);
      vi.mocked(fs.readFileSync).mockReturnValue("cache-data");

      const result = getCached("test-key");
      expect(result).toEqual({ data: "cache-data", stale: true });
    });
  });

  describe("getEtag", () => {
    it("returns null if etag file read fails", () => {
      vi.mocked(fs.existsSync).mockReturnValue(true);
      vi.mocked(fs.readFileSync).mockImplementation(() => {
        throw new Error("No file");
      });
      expect(getEtag("test-key")).toBeNull();
    });

    it("returns null if etag file does not exist", () => {
      vi.mocked(fs.existsSync).mockReturnValue(false);
      expect(getEtag("test-key")).toBeNull();
    });

    it("returns etag if etag file exists and can be read", () => {
      vi.mocked(fs.existsSync).mockReturnValue(true);
      vi.mocked(fs.readFileSync).mockReturnValue("etag123");
      expect(getEtag("test-key")).toBe("etag123");
    });
  });

  describe("putCache", () => {
    it("creates cache dir if it does not exist", () => {
      vi.mocked(fs.existsSync).mockReturnValue(false);

      putCache("test-key", "data", "etag");

      expect(fs.mkdirSync).toHaveBeenCalledWith(expect.any(String), { recursive: true });
    });

    it("writes cache data and etag", () => {
      vi.mocked(fs.existsSync).mockReturnValue(true);
      const now = 2000000;
      vi.setSystemTime(now);

      putCache("test!key", "new-data", "new-etag");

      // Should write to a sanitized path
      expect(fs.writeFileSync).toHaveBeenCalledWith(
        expect.stringMatching(/test_key\.json$/),
        "new-data"
      );

      // Should write etag file
      expect(fs.writeFileSync).toHaveBeenCalledWith(
        expect.stringMatching(/test_key\.json\.etag$/),
        "new-etag"
      );
    });

    it("unlinks etag file if no etag is provided and an old etag exists", () => {
      // Setup mock to return true for existsSync so ensureCacheDir doesn't create dir,
      // but also true for when we check if etag file exists
      vi.mocked(fs.existsSync).mockReturnValue(true);

      putCache("test!key", "new-data", "");

      // Should unlink old etag file
      expect(fs.unlinkSync).toHaveBeenCalledWith(
        expect.stringMatching(/test_key\.json\.etag$/)
      );

      // Should NOT write an empty etag file
      const writeEtagCall = vi.mocked(fs.writeFileSync).mock.calls.find(call =>
        typeof call[0] === 'string' && call[0].endsWith(".etag")
      );
      expect(writeEtagCall).toBeUndefined();
    });
  });
});
