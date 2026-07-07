/**
 * docs/skills/index.js — aggregated skill index renderer.
 *
 * Fetches docs/okf/index.json (emitted by scripts/buildSkillsIndex.py)
 * and renders a flat per-family table of all skills.
 *
 * Design rules (W5):
 *   - NO custom CSS. Uses only existing design tokens (--tier-*, --text, --border-subtle).
 *   - Tables use the .skills-table utility class defined in docs/css/styles.css (standard).
 *   - If styles.css has no .skills-table, falls back to plain inline border styles
 *     via CSS custom properties only.
 */
(function () {
  'use strict';

  var ROOT_PATH = (function () {
    var script = document.currentScript || (function () {
      var scripts = document.querySelectorAll('script');
      return scripts[scripts.length - 1];
    }());
    var src = script ? script.getAttribute('src') : '';
    // index.js lives at /skills/index.js — root is one level up
    if (src && src.indexOf('../') === 0) return src.replace(/[^/]+$/, '');
    return '../';
  }());

  var VERSION = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
  var INDEX_URL = ROOT_PATH + 'okf/index.json' + VERSION;

  /** Map family id to a design token colour. */
  var FAMILY_COLORS = {
    basic:    'var(--tier-basic)',
    extra:    'var(--tier-extra)',
    ultimate: 'var(--tier-ultimate)',
  };

  /** Map family id to a human label. */
  var FAMILY_LABELS = {
    basic:    'Basic',
    extra:    'Extra',
    ultimate: 'Ultimate',
  };

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'style') {
          node.style.cssText = attrs[k];
        } else if (k === 'className') {
          node.className = attrs[k];
        } else {
          node.setAttribute(k, attrs[k]);
        }
      });
    }
    if (children) {
      if (typeof children === 'string') {
        node.textContent = children;
      } else if (Array.isArray(children)) {
        children.forEach(function (c) { if (c) node.appendChild(c); });
      } else {
        node.appendChild(children);
      }
    }
    return node;
  }

  function renderFamily(family) {
    var color = FAMILY_COLORS[family.id] || 'var(--text)';
    var label = FAMILY_LABELS[family.id] || family.id;

    var section = el('section', {
      style: 'margin-bottom: 3rem;',
    });

    var heading = el('h2', {
      style: 'color: ' + color + '; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.5rem; margin-bottom: 1rem; font-size: 1.1rem; letter-spacing: 0.04em; text-transform: uppercase;',
    }, label + ' skills (' + family.count + ')');
    section.appendChild(heading);

    if (!family.skills || family.skills.length === 0) {
      section.appendChild(el('p', { style: 'color: var(--muted);' }, 'No skills in this family.'));
      return section;
    }

    var table = el('table', {
      style: 'width: 100%; border-collapse: collapse; font-size: 0.9rem;',
      'aria-label': label + ' skills',
    });

    var thead = el('thead');
    var headerRow = el('tr');
    ['Skill', 'ID', 'Summary'].forEach(function (col) {
      headerRow.appendChild(el('th', {
        style: 'text-align: left; padding: 0.4rem 0.75rem; border-bottom: 2px solid var(--border-subtle); color: var(--muted); font-weight: 600; white-space: nowrap;',
      }, col));
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = el('tbody');
    family.skills.forEach(function (skill, idx) {
      var row = el('tr', {
        style: (idx % 2 === 1 ? 'background: var(--surface-raised, transparent);' : ''),
      });

      // Name cell — links to /codex.html#<id>
      var codexHref = ROOT_PATH + 'codex.html#' + skill.id;
      var nameLink = el('a', {
        href: codexHref,
        style: 'color: ' + color + '; text-decoration: none; font-weight: 500;',
      }, skill.name || skill.id);
      row.appendChild(el('td', {
        style: 'padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--border-subtle); white-space: nowrap;',
      }, [nameLink]));

      // ID cell
      row.appendChild(el('td', {
        style: 'padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--border-subtle); color: var(--muted); font-family: "JetBrains Mono", monospace; font-size: 0.8em; white-space: nowrap;',
      }, skill.id || ''));

      // Summary cell
      row.appendChild(el('td', {
        style: 'padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--border-subtle); color: var(--text);',
      }, skill.summary || ''));

      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    section.appendChild(table);
    return section;
  }

  function render(data) {
    var mount = document.getElementById('skills-index');
    var totalEl = document.getElementById('skills-total');
    if (!mount) return;

    var total = 0;
    data.families.forEach(function (f) { total += f.count; });
    if (totalEl) totalEl.textContent = total;

    data.families.forEach(function (family) {
      mount.appendChild(renderFamily(family));
    });
  }

  function renderError(msg) {
    var mount = document.getElementById('skills-index');
    if (mount) {
      mount.textContent = msg;
      mount.style.color = 'var(--muted)';
    }
  }

  fetch(INDEX_URL)
    .then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    })
    .then(function (data) {
      if (!data || !Array.isArray(data.families)) {
        throw new Error('Unexpected index.json shape');
      }
      render(data);
    })
    .catch(function (err) {
      console.warn('[skills-index] Failed to load okf/index.json:', err);
      renderError('Skill index temporarily unavailable. Try refreshing.');
    });
}());
