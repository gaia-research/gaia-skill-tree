/* profile-share.js — Web Share API with Canvas-generated 1080×1080 PNG.
 * Targets Instagram, WhatsApp, Twitter/X, and any OS share sheet.
 *
 * API:
 *   profileShare.open(btn)   — open share popover for the plaque containing btn
 *   profileShare.close()     — close any open popover
 *
 * Depends on: window.PROFILE_SKILLS (injected by generateProfilePages.py)
 */
(function () {
  var ICON_BASE = document.documentElement.getAttribute('data-icon-base') || '../../assets/icons.svg';

  /* ── design tokens — read from CSS custom properties at draw time ── */
  var _T = null;
  var _RC = null;

  function getT() {
    if (_T) return _T;
    var cs = getComputedStyle(document.documentElement);
    function v(n) { return cs.getPropertyValue(n).trim(); }
    var apexGold = v('--apex-gold');
    if (apexGold.indexOf('var(') === 0) apexGold = v('--rank-5');
    _T = {
      bg:      v('--bg')       || '#030712',
      surface: v('--surface')  || '#0f172a',
      border:  v('--border')   || '#1e293b',
      text:    v('--text')     || '#e2e8f0',
      muted:   v('--muted')    || '#64748b',
      red:     v('--honor-red') || '#ef4444',
      gold:    apexGold,
      basic:   v('--tier-basic'),
      extra:   v('--tier-extra'),
      unique:  v('--tier-unique'),
      ultimate:v('--tier-ultimate'),
    };
    return _T;
  }

  function getRankColors() {
    if (_RC) return _RC;
    var cs = getComputedStyle(document.documentElement);
    function v(n) { return cs.getPropertyValue(n).trim(); }
    _RC = [v('--rank-0'),v('--rank-1'),v('--rank-2'),v('--rank-3'),v('--rank-4'),v('--rank-5'),v('--rank-6')];
    return _RC;
  }

  /* ── canvas card renderer ─────────────────────────────────── */
  function drawCard(ns, canvas) {
    var T  = getT();
    var RC = getRankColors();
    var S = 1080;
    canvas.width = canvas.height = S;
    var ctx = canvas.getContext('2d');
    var n   = parseInt(ns.levelNum || ns.level || 0, 10);
    var typ = ns.type || 'basic';
    var rankColor = RC[Math.min(n, 6)] || RC[0];

    /* ── background ── */
    ctx.fillStyle = T.bg;
    ctx.fillRect(0, 0, S, S);

    /* ── tier glow overlay (top-left radial) ── */
    var typeGlows = {
      basic:    [56,189,248], extra:   [192,132,252],
      unique:   [124,58,237], ultimate:[245,158,11],
    };
    var glowRgb = typeGlows[typ] || typeGlows.basic;
    var grd = ctx.createRadialGradient(0, 0, 0, 0, 0, S * 0.75);
    grd.addColorStop(0,   'rgba(' + glowRgb + ',.22)');
    grd.addColorStop(1,   'rgba(' + glowRgb + ',0)');
    ctx.fillStyle = grd;
    ctx.fillRect(0, 0, S, S);

    /* ── card surface ── */
    var pad = 70;
    var r   = 28;
    roundRect(ctx, pad, pad, S - pad * 2, S - pad * 2, r);
    ctx.fillStyle = T.surface;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,.07)';
    ctx.lineWidth   = 1.5;
    ctx.stroke();

    /* ── orb ── */
    var orbR = 36, orbX = pad + 72, orbY = pad + 100;
    var orbGrds = {
      basic:    ['#7dd3fc','#0ea5e9'], extra:   ['#d8b4fe','#9333ea'],
      unique:   [T.unique, '#6d28d9'], ultimate:['#fde68a','#d97706'],
    };
    var og = orbGrds[typ] || orbGrds.basic;
    var orbGrd = ctx.createRadialGradient(orbX - orbR * 0.3, orbY - orbR * 0.3, 0, orbX, orbY, orbR);
    orbGrd.addColorStop(0, og[0]);
    orbGrd.addColorStop(1, og[1]);
    ctx.beginPath();
    ctx.arc(orbX, orbY, orbR, 0, Math.PI * 2);
    ctx.fillStyle = orbGrd;
    ctx.fill();

    /* ── rank chip ── */
    var chipX = orbX + orbR + 22, chipY = orbY - 22;
    var chipLabel = n + '★';
    ctx.font = 'bold 28px Inter,system-ui,sans-serif';
    ctx.textBaseline = 'top';
    var chipW = ctx.measureText(chipLabel).width + 28;
    roundRect(ctx, chipX, chipY, chipW, 44, 22);
    ctx.fillStyle = 'rgba(0,0,0,.35)';
    ctx.fill();
    ctx.strokeStyle = rankColor;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.fillStyle = rankColor;
    ctx.fillText(chipLabel, chipX + 14, chipY + 8);

    /* ── origin badge (if origin) ── */
    if (ns.origin) {
      var bx = S - pad - 88, by = pad + 78;
      ctx.font = 'bold 22px Inter,system-ui,sans-serif';
      ctx.fillStyle = T.red;
      ctx.fillText('#1', bx, by);
    }

    /* ── slug ── */
    var slug = '/' + String(ns.id || '').split('/').pop();
    ctx.font = '22px "JetBrains Mono",monospace';
    ctx.fillStyle = T.muted;
    ctx.textBaseline = 'alphabetic';
    ctx.fillText(slug, pad + 72, pad + 165);

    /* ── title (name) ── */
    ctx.font = 'bold 56px Inter,system-ui,sans-serif';
    ctx.fillStyle = T.text;
    wrapText(ctx, ns.name || slug, pad + 72, pad + 255, S - pad * 2 - 140, 66);

    /* ── contributor handle ── */
    ctx.font = '30px Inter,system-ui,sans-serif';
    ctx.fillStyle = T.red;
    ctx.fillText('@' + (ns.contributor || ''), pad + 72, pad + 380);

    /* ── description (2 lines max) ── */
    if (ns.description) {
      ctx.font = '26px Inter,system-ui,sans-serif';
      ctx.fillStyle = T.muted;
      wrapText(ctx, ns.description, pad + 72, pad + 450, S - pad * 2 - 140, 38, 2);
    }

    /* ── tags ── */
    var tagY = pad + 560, tagX = pad + 72;
    (ns.tags || []).slice(0, 5).forEach(function (tag) {
      ctx.font = 'bold 20px Inter,system-ui,sans-serif';
      var tw = ctx.measureText(tag).width + 24;
      roundRect(ctx, tagX, tagY, tw, 34, 17);
      ctx.fillStyle = 'rgba(255,255,255,.07)';
      ctx.fill();
      ctx.fillStyle = T.muted;
      ctx.fillText(tag, tagX + 12, tagY + 22);
      tagX += tw + 10;
    });

    /* ── rank stars (bottom) ── */
    var stY = S - pad - 160;
    for (var i = 1; i <= 6; i++) {
      ctx.font = '36px Inter,system-ui,sans-serif';
      ctx.fillStyle = i <= n ? T.gold : 'rgba(255,255,255,.12)';
      ctx.fillText('★', pad + 72 + (i - 1) * 44, stY);
    }

    /* ── rank name label ── */
    var RANK_NAMES = ['','Awakened','Named','Evolved','Hardened','Transcendent','Transcendent ★'];
    ctx.font = '22px Inter,system-ui,sans-serif';
    ctx.fillStyle = rankColor;
    ctx.fillText(RANK_NAMES[n] || '', pad + 72 + 6 * 44 + 16, stY - 2);

    /* ── bottom gold underline ── */
    var ulY = S - pad - 100;
    var ulGrd = ctx.createLinearGradient(pad + 72, ulY, S - pad - 72, ulY);
    ulGrd.addColorStop(0, 'rgba(251,191,36,.7)');
    ulGrd.addColorStop(1, 'rgba(251,191,36,.05)');
    ctx.beginPath();
    ctx.moveTo(pad + 72, ulY);
    ctx.lineTo(S - pad - 72, ulY);
    ctx.strokeStyle = ulGrd;
    ctx.lineWidth = 3;
    ctx.stroke();

    /* ── Gaia wordmark footer ── */
    ctx.font = 'bold 22px Inter,system-ui,sans-serif';
    ctx.fillStyle = T.muted;
    ctx.fillText('◆ GAIA  ·  gaia-skill-tree', pad + 72, S - pad - 52);
  }

  /* ── helpers ─────────────────────────────────────────────── */

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  function wrapText(ctx, text, x, y, maxW, lineH, maxLines) {
    var words = text.split(' ');
    var line  = '';
    var lines = 0;
    for (var i = 0; i < words.length; i++) {
      var test = line ? line + ' ' + words[i] : words[i];
      if (ctx.measureText(test).width > maxW && line) {
        ctx.fillText(line, x, y);
        y += lineH;
        line = words[i];
        lines++;
        if (maxLines && lines >= maxLines) { ctx.fillText(line + '…', x, y); return; }
      } else {
        line = test;
      }
    }
    if (line) ctx.fillText(line, x, y);
  }

  /* ── popover UI ──────────────────────────────────────────── */

  var _openPopover = null;

  function closeAll() {
    if (_openPopover) {
      _openPopover.classList.remove('open');
      _openPopover = null;
    }
  }

  document.addEventListener('click', function (e) {
    if (_openPopover && !_openPopover.contains(e.target) && !e.target.closest('.plaque__share-btn')) {
      closeAll();
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeAll();
  });

  function findNs(skillId) {
    var skills = window.PROFILE_SKILLS || [];
    for (var i = 0; i < skills.length; i++) {
      if (skills[i].id === skillId) return skills[i];
    }
    return null;
  }

  function open(btn) {
    closeAll();

    var plaque = btn.closest('.plaque');
    if (!plaque) return;
    var skillId = plaque.dataset.skillId;
    var ns = findNs(skillId);
    if (!ns) return;

    /* build popover */
    var pop = document.createElement('div');
    pop.className = 'share-popover';

    var profileUrl = window.location.href.split('#')[0] + '#' + encodeURIComponent(skillId.replace(/\//g, '-'));

    pop.innerHTML = (
      '<div class="share-popover-title">Share Skill</div>' +

      /* native share (Instagram, WhatsApp, etc.) */
      '<button class="share-action" id="sp-native" type="button">' +
      _ico('share', 16) + 'Share to apps…</button>' +

      /* copy link */
      '<button class="share-action" id="sp-copy" type="button">' +
      _ico('link', 16) + 'Copy link</button>' +

      /* download PNG */
      '<button class="share-action" id="sp-png" type="button">' +
      _ico('download', 16) + 'Download card (PNG)</button>' +

      /* badge — coming soon */
      '<button class="share-action" type="button" disabled>' +
      _ico('badge-soon', 16) + 'Embed badge ' +
      '<span class="badge-soon-label">soon</span></button>'
    );

    plaque.style.position = 'relative';
    plaque.appendChild(pop);
    _openPopover = pop;
    requestAnimationFrame(function () { pop.classList.add('open'); });

    /* ── wire actions ── */

    pop.querySelector('#sp-copy').addEventListener('click', function () {
      navigator.clipboard.writeText(profileUrl).then(function () {
        var btn2 = pop.querySelector('#sp-copy');
        btn2.textContent = '✓ Copied!';
        setTimeout(closeAll, 1200);
      }).catch(function () {});
    });

    var offscreen = document.createElement('canvas');
    drawCard(ns, offscreen);

    function getPng(cb) {
      offscreen.toBlob(function (blob) { cb(blob); }, 'image/png');
    }

    pop.querySelector('#sp-png').addEventListener('click', function () {
      getPng(function (blob) {
        var url = URL.createObjectURL(blob);
        var a   = document.createElement('a');
        a.href  = url;
        a.download = (ns.contributor || 'gaia') + '-' + (String(ns.id).split('/').pop()) + '-skill-card.png';
        a.click();
        setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
        closeAll();
      });
    });

    var nativeBtn = pop.querySelector('#sp-native');
    if (navigator.share && navigator.canShare) {
      nativeBtn.addEventListener('click', function () {
        getPng(function (blob) {
          var file = new File([blob], 'gaia-skill-card.png', { type: 'image/png' });
          if (!navigator.canShare({ files: [file] })) {
            /* fallback: share URL only */
            navigator.share({ title: ns.name, text: ns.description || '', url: profileUrl });
          } else {
            navigator.share({
              title: ns.name + ' — Gaia Skill',
              text: '@' + ns.contributor + ' · ' + (ns.level || '') + ' · ' + (ns.description || '').slice(0, 120),
              files: [file],
            }).catch(function () {});
          }
          closeAll();
        });
      });
    } else {
      /* Web Share not available — swap to a direct download fallback */
      nativeBtn.textContent = 'Share (unsupported) ↓';
      nativeBtn.disabled = true;
    }
  }

  function _ico(id, size) {
    return '<svg class="ico" width="' + size + '" height="' + size + '" aria-hidden="true"><use href="' + ICON_BASE + '#' + id + '"/></svg>';
  }

  window.profileShare = { open: open, close: closeAll };
})();
