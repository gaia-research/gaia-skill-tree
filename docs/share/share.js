/**
 * docs/share/share.js
 * Fetches a Gaia share bundle from ?b=<url> and renders the sharer's
 * Skill Tree preview + per-skill install rows with copy buttons.
 *
 * Bundle shape (from src/gaia_cli/share.py build_share_bundle):
 *   {
 *     kind:          "gaia-share-bundle",
 *     bundleVersion: "1",
 *     generatedAt:   "<ISO8601>",
 *     sharer:        "<username>",
 *     sourceRepo:    "<url|null>",
 *     tree: {
 *       userId, updatedAt,
 *       unlockedSkills: [{ skillId, level, ... }],
 *       stats: {}
 *     },
 *     skillMeta: {
 *       "<skillId>": {
 *         name, level, type, named, genericRef, prereqs: [...]
 *       }
 *     },
 *     install: [
 *       { id, name, level, type, github?, suiteComponents?, genericSkillRef? }
 *     ]
 *   }
 *
 * Production: loaded only when window.location.search has ?b=.
 * Dev/test:   set window.SHARE_BUNDLE_OVERRIDE to a bundle object before
 *             loading this script to bypass the fetch (see sample.json).
 *
 * No external dependencies. Vanilla JS, no build step.
 */

(function () {
  'use strict';

  /* ── Constants ─────────────────────────────────────────── */

  var BUNDLE_KIND = 'gaia-share-bundle';

  var TIER_SYMBOL = {
    basic:    '○',
    extra:    '◇',
    unique:   '◉',
    ultimate: '◆'
  };

  // Stars strings 0★–6★ as produced by gaia CLI.
  var STAR_LABELS = ['0★', '1★', '2★', '3★', '4★', '5★', '6★'];

  /* ── Helpers ────────────────────────────────────────────── */

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Parse a stars string like "3★" or "3" into an integer 0-6, or null.
  function parseStars(levelStr) {
    if (!levelStr) return null;
    var s = String(levelStr).replace('★', '').trim();
    var n = parseInt(s, 10);
    return isNaN(n) ? null : Math.min(6, Math.max(0, n));
  }

  // Produce the gaia install command for a manifest entry.
  // If the entry has a github URL and no canonical id (no "/" prefix needed),
  // fall back to the source URL so it installs even without a local registry.
  function installCommand(entry) {
    var id = entry.id || '';
    // Named-skill ids contain "/" (e.g. "mattpocock/grill-me") — install by id.
    // Canonical ids without "/" are also installable by id.
    if (id) return 'gaia install ' + id;
    if (entry.github) return 'gaia install ' + entry.github;
    return 'gaia install ' + id;
  }

  // Flash "Copied!" on a button for 1.4 s then restore the original label.
  function flashCopied(btn, originalLabel) {
    btn.setAttribute('data-copied', 'true');
    btn.textContent = 'Copied!';
    setTimeout(function () {
      btn.removeAttribute('data-copied');
      btn.textContent = originalLabel;
    }, 1400);
  }

  function copyText(text, btn, originalLabel) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        flashCopied(btn, originalLabel);
      }).catch(function () {
        legacyCopy(text, btn, originalLabel);
      });
    } else {
      legacyCopy(text, btn, originalLabel);
    }
  }

  function legacyCopy(text, btn, originalLabel) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand('copy');
      flashCopied(btn, originalLabel);
    } catch (e) {/* silent */ }
    document.body.removeChild(ta);
  }

  /* ── Tree preview renderer ──────────────────────────────── */

  // Produce a coloured ASCII tree from skillMeta.
  // Returns an array of HTML spans (one per line) with colour applied inline
  // via data-level attributes (CSS handles the colour via --rank-N tokens).
  function renderTreeLines(skillMeta) {
    var ids = Object.keys(skillMeta);
    if (!ids.length) return [];

    // Find roots: skills not referenced as a prereq of any other.
    var allPrereqs = {};
    ids.forEach(function (sid) {
      (skillMeta[sid].prereqs || []).forEach(function (p) { allPrereqs[p] = true; });
    });
    var roots = ids.filter(function (sid) { return !allPrereqs[sid]; }).sort();
    if (!roots.length) roots = ids.slice().sort(); // cycle fallback

    var lines = [];
    var seen = {};

    function render(sid, prefix, isLast) {
      var m = skillMeta[sid] || {};
      var type = m.type || 'basic';
      var symbol = TIER_SYMBOL[type] || '○';
      var levelStr = m.level || '?';
      var starNum = parseStars(levelStr);
      var star = (starNum !== null && starNum > 0) ? ' ' + levelStr : '';
      var label = symbol + ' ' + sid + star;
      var connector = isLast ? '└── ' : '├── ';

      if (seen[sid]) {
        lines.push(
          '<span class="tree-connector">' + escapeHtml(prefix + connector) + '</span>' +
          '<span class="tree-see-above">' + escapeHtml(label) + ' (see above)</span>'
        );
        return;
      }
      seen[sid] = true;

      var levelAttr = (starNum !== null) ? ' data-level="' + starNum + '"' : '';
      lines.push(
        '<span class="tree-connector">' + escapeHtml(prefix + connector) + '</span>' +
        '<span class="tree-skill"' + levelAttr + '>' + escapeHtml(label) + '</span>'
      );

      var children = (m.prereqs || []).filter(function (p) { return skillMeta[p]; }).sort();
      var childPrefix = prefix + (isLast ? '    ' : '│   ');
      children.forEach(function (child, i) {
        render(child, childPrefix, i === children.length - 1);
      });
    }

    roots.forEach(function (root, i) {
      render(root, '', i === roots.length - 1);
    });

    return lines;
  }

  /* ── Render functions ───────────────────────────────────── */

  function renderHero(sharer) {
    var sharerEl = document.getElementById('share-sharer');
    var subtitleEl = document.getElementById('share-subtitle');
    if (sharerEl) sharerEl.textContent = sharer;
    if (subtitleEl) subtitleEl.removeAttribute('hidden');
  }

  function renderTree(skillMeta, sharer) {
    var block = document.getElementById('share-tree-block');
    if (!block) return;

    var treeLines = renderTreeLines(skillMeta);
    if (!treeLines.length) {
      block.setAttribute('hidden', '');
      return;
    }

    var heading = block.querySelector('.share-tree-block__heading');
    if (heading) heading.textContent = 'Skill Tree — ' + sharer;

    var pre = block.querySelector('.share-tree-block__pre');
    if (pre) pre.innerHTML = treeLines.join('\n');

    block.removeAttribute('hidden');
  }

  function renderSkillRows(manifest) {
    var container = document.getElementById('share-skill-rows');
    var actionsEl = document.getElementById('share-actions');
    var countEl = document.getElementById('share-skill-count');

    if (!container) return;

    if (!manifest || !manifest.length) {
      // Empty bundle — show illustration block, hide actions.
      if (actionsEl) actionsEl.setAttribute('hidden', '');
      container.innerHTML = renderStateBlock(
        '◇',
        'Nothing to share yet.',
        'This Skill Tree has no installable skills. Once skills are named and pushed to a repository, they appear here.'
      );
      return;
    }

    if (countEl) countEl.textContent = manifest.length + ' skill' + (manifest.length !== 1 ? 's' : '');
    if (actionsEl) actionsEl.removeAttribute('hidden');

    var items = manifest.map(function (entry) {
      var type = entry.type || 'basic';
      var glyph = TIER_SYMBOL[type] || '○';
      var name = entry.name || entry.id || '(unknown)';
      var levelStr = entry.level || '?';
      var starNum = parseStars(levelStr);
      var levelAttr = (starNum !== null) ? ' data-level="' + starNum + '"' : '';
      var starsDisplay = (starNum !== null && starNum > 0) ? levelStr : '—';

      // Contributor handle: extract from id if it contains "/"
      var contributor = '';
      if (entry.id && entry.id.indexOf('/') !== -1) {
        contributor = entry.id.split('/')[0];
      }

      var cmd = installCommand(entry);

      return '<li class="share-skill-row">' +
        '<span class="share-skill-row__glyph" data-tier="' + escapeHtml(type) + '" aria-hidden="true">' +
          escapeHtml(glyph) +
        '</span>' +
        '<span class="share-skill-row__info">' +
          '<span class="share-skill-row__name"' + levelAttr + '>' + escapeHtml(name) + '</span>' +
          (contributor
            ? '<span class="share-skill-row__contributor" aria-label="Origin Contributor">' + escapeHtml(contributor) + '</span>'
            : '') +
        '</span>' +
        '<span class="share-skill-row__stars" aria-label="Stars">' + escapeHtml(starsDisplay) + '</span>' +
        '<button class="btn-copy-install" type="button" ' +
          'data-cmd="' + escapeHtml(cmd) + '" ' +
          'aria-label="Copy install command for ' + escapeHtml(name) + '">' +
          'Copy install' +
        '</button>' +
      '</li>';
    });

    var ul = document.createElement('ul');
    ul.className = 'share-skill-list';
    ul.setAttribute('aria-label', 'Installable skills');
    ul.innerHTML = items.join('');
    container.innerHTML = '';
    container.appendChild(ul);

    // Wire per-row copy buttons.
    ul.querySelectorAll('.btn-copy-install').forEach(function (btn) {
      btn.addEventListener('click', function () {
        copyText(btn.getAttribute('data-cmd'), btn, 'Copy install');
      });
    });
  }

  function renderFooterNote(generatedAt) {
    var el = document.getElementById('share-footer-note');
    if (!el) return;
    var genEl = el.querySelector('.share-footer-note__generated');
    if (genEl && generatedAt) {
      var d = new Date(generatedAt);
      var dateStr = isNaN(d.getTime()) ? generatedAt : d.toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
      });
      genEl.textContent = 'Generated ' + dateStr;
    }
    el.removeAttribute('hidden');
  }

  /* ── State blocks (empty / error / no-param) ─────────────── */

  function renderStateBlock(glyph, title, body, extra) {
    return '<div class="share-state-block">' +
      '<div class="share-state-block__glyph" aria-hidden="true">' + escapeHtml(glyph) + '</div>' +
      '<p class="share-state-block__title">' + escapeHtml(title) + '</p>' +
      '<p class="share-state-block__body">' + escapeHtml(body) + '</p>' +
      (extra || '') +
    '</div>';
  }

  function showError(title, body, urlStr) {
    hideLoading();
    var container = document.getElementById('share-skill-rows');
    var actions = document.getElementById('share-actions');
    var tree = document.getElementById('share-tree-block');
    var heroSub = document.getElementById('share-subtitle');

    if (actions) actions.setAttribute('hidden', '');
    if (tree) tree.setAttribute('hidden', '');
    if (heroSub) heroSub.setAttribute('hidden', '');

    if (container) {
      var urlBlock = urlStr
        ? '<p class="share-state-block__url">' + escapeHtml(urlStr) + '</p>'
        : '';
      container.innerHTML = renderStateBlock('◇', title, body, urlBlock);
    }
  }

  function hideLoading() {
    var el = document.getElementById('share-loading');
    if (el) el.setAttribute('hidden', '');
  }

  function showContent() {
    var el = document.getElementById('share-content');
    if (el) el.removeAttribute('hidden');
  }

  /* ── Copy-all button ─────────────────────────────────────── */

  function wireCopyAll(manifest) {
    var btn = document.getElementById('share-copy-all-btn');
    if (!btn || !manifest || !manifest.length) {
      if (btn) btn.setAttribute('disabled', '');
      return;
    }
    var block = manifest.map(function (e) { return installCommand(e); }).join('\n');
    btn.removeAttribute('disabled');
    btn.addEventListener('click', function () {
      copyText(block, btn, 'Copy all');
    });
  }

  /* ── Main render ─────────────────────────────────────────── */

  function renderBundle(bundle) {
    hideLoading();
    showContent();

    var sharer   = bundle.sharer || (bundle.tree || {}).userId || 'unknown';
    var skillMeta = bundle.skillMeta || {};
    var manifest  = bundle.install || [];
    var generatedAt = bundle.generatedAt || null;

    renderHero(sharer);
    renderTree(skillMeta, sharer);
    renderSkillRows(manifest);
    wireCopyAll(manifest);
    renderFooterNote(generatedAt);
  }

  /* ── Bundle fetcher ──────────────────────────────────────── */

  function validateBundle(data, ref) {
    if (!data || typeof data !== 'object') {
      throw new Error('Bundle at ' + ref + ' is not a JSON object.');
    }
    if (data.kind !== BUNDLE_KIND) {
      throw new Error('Not a Gaia share bundle (expected kind "' + BUNDLE_KIND + '").');
    }
  }

  function fetchBundle(url, onSuccess, onError) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.timeout = 30000;
    xhr.onload = function () {
      if (xhr.status === 200) {
        try {
          var data = JSON.parse(xhr.responseText);
          validateBundle(data, url);
          onSuccess(data);
        } catch (e) {
          onError('malformed', e.message, url);
        }
      } else if (xhr.status === 404) {
        onError('notfound', null, url);
      } else {
        onError('network', 'HTTP ' + xhr.status, url);
      }
    };
    xhr.ontimeout = function () {
      onError('network', 'Request timed out after 30 s.', url);
    };
    xhr.onerror = function () {
      onError('network', null, url);
    };
    xhr.send();
  }

  /* ── Entry point ─────────────────────────────────────────── */

  function init() {
    // Dev override — allows local testing without a live URL.
    if (window.SHARE_BUNDLE_OVERRIDE) {
      try {
        validateBundle(window.SHARE_BUNDLE_OVERRIDE, '(override)');
        renderBundle(window.SHARE_BUNDLE_OVERRIDE);
      } catch (e) {
        showError('Invalid bundle', 'The test bundle is malformed: ' + e.message, null);
      }
      return;
    }

    var params = new URLSearchParams(window.location.search);
    var bundleUrl = params.get('b');

    if (!bundleUrl) {
      hideLoading();
      showContent();
      showError(
        'No bundle link provided.',
        'Open this page from a gaia share link. Example:',
        null
      );
      // Swap the body text for the no-param case to show the example command.
      var container = document.getElementById('share-skill-rows');
      if (container) {
        var block = container.querySelector('.share-state-block');
        if (block) {
          var bodyEl = block.querySelector('.share-state-block__body');
          if (bodyEl) {
            bodyEl.textContent = 'Open this page from a gaia share link, or run:';
            var cmd = document.createElement('code');
            cmd.className = 'share-state-block__cmd';
            cmd.textContent = 'gaia share\n# then open the printed URL in a browser';
            block.appendChild(cmd);
          }
        }
      }
      return;
    }

    fetchBundle(
      bundleUrl,
      function (bundle) {
        renderBundle(bundle);
      },
      function (kind, detail, url) {
        if (kind === 'notfound') {
          showError(
            'Bundle not reachable.',
            'The link may have expired or moved. Ask the sharer to regenerate with gaia share.',
            url
          );
        } else if (kind === 'malformed') {
          showError(
            'Invalid bundle.',
            'The file could not be parsed as a Gaia share bundle. Ask the sharer to regenerate.',
            url
          );
        } else {
          showError(
            'Bundle not reachable.',
            'The link may have expired or moved. Ask the sharer to regenerate with gaia share.',
            url
          );
        }
      }
    );
  }

  // Run after DOM is ready.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

}());
