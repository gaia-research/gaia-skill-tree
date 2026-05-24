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
  });
});
