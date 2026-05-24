<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> a383a9de (🧪 Add tests for caching utility in mcp server (#428))
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fs from 'node:fs';

// Mock fs first
vi.mock('node:fs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:fs')>();
  return {
    ...actual,
    existsSync: vi.fn(),
    readFileSync: vi.fn(),
    writeFileSync: vi.fn(),
    mkdirSync: vi.fn(),
    statSync: vi.fn(),
  };
});

// Important: The code uses readFileSync with utf-8, so we mock accordingly.
import { getCached, getEtag, putCache } from '../src/config/cache.js';

describe('cache utility', () => {
  let mockFs: Record<string, string> = {};
  let mockFsTimes: Record<string, number> = {};

  beforeEach(() => {
    mockFs = {};
    mockFsTimes = {};

    // We capture dynamically generated paths by storing whatever the cache writes!
    vi.mocked(fs.existsSync).mockImplementation((path) => {
      if (typeof path === 'string') {
        return mockFs[path] !== undefined;
      }
      return false;
    });

    vi.mocked(fs.readFileSync).mockImplementation((path, options) => {
      if (typeof path === 'string') {
        if (mockFs[path] === undefined) {
          throw new Error(`ENOENT: no such file or directory, open '${path}'`);
        }
        return mockFs[path];
      }
      throw new Error(`Unexpected read of ${path}`);
    });

    vi.mocked(fs.writeFileSync).mockImplementation((path, data) => {
      if (typeof path === 'string') {
        mockFs[path] = data.toString();
        mockFsTimes[path] = Date.now();
        return;
      }
    });

    vi.mocked(fs.mkdirSync).mockImplementation((path, options) => {
      if (typeof path === 'string') {
        mockFs[path] = 'DIR';
        mockFsTimes[path] = Date.now();
        return path;
      }
      return path as string;
    });

    vi.mocked(fs.statSync).mockImplementation((path) => {
      if (typeof path === 'string') {
        if (mockFs[path] === undefined) {
          throw new Error(`ENOENT: no such file or directory, stat '${path}'`);
        }
        return { mtimeMs: mockFsTimes[path] || Date.now() } as any;
      }
      return {} as any;
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should return null when cache is empty', () => {
    expect(getCached('some-key')).toBeNull();
    expect(getEtag('some-key')).toBeNull();
  });

  it('should store and retrieve cache successfully', () => {
    putCache('my-key', '{"data": "value"}', 'etag-123');

    expect(getEtag('my-key')).toBe('etag-123');
    const cached = getCached('my-key');
    expect(cached).not.toBeNull();
    expect(cached?.data).toBe('{"data": "value"}');
    expect(cached?.stale).toBe(false);
  });

  it('should identify stale cache entries', () => {
    vi.useFakeTimers();
    try {
      putCache('my-stale-key', 'old-data', 'etag-old');

      // Advance time beyond TTL_MS (5 * 60 * 1000 = 300000ms)
      vi.advanceTimersByTime(5 * 60 * 1000 + 1000); // 5 mins and 1 sec

      const cached = getCached('my-stale-key');
      expect(cached).not.toBeNull();
      expect(cached?.data).toBe('old-data');
      expect(cached?.stale).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('should return null when cached file is missing', () => {
    putCache('broken-key', 'data', 'etag');

    // Find the data file and delete it dynamically
    const files = Object.keys(mockFs);
    const dataFile = files.find(f => !f.endsWith('meta.json') && mockFs[f] === 'data');
    if (dataFile) {
        delete mockFs[dataFile];
    }

    expect(getCached('broken-key')).toBeNull();
  });

  it('should sanitize keys for file paths (or at least store data correctly)', () => {
    putCache('strange/key*with:chars', 'data', 'etag');

    const cached = getCached('strange/key*with:chars');
    expect(cached?.data).toBe('data');
=======
<<<<<<< HEAD
=======
>>>>>>> 20140742 (🧪 Add tests for caching utility in mcp package (#421))
=======
>>>>>>> a383a9de (🧪 Add tests for caching utility in mcp server (#428))
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
<<<<<<< HEAD
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> 20140742 (🧪 Add tests for caching utility in mcp package (#421))
=======
>>>>>>> origin/main
>>>>>>> a383a9de (🧪 Add tests for caching utility in mcp server (#428))
  });
});
