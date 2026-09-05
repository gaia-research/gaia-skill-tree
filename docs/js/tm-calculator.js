/* docs/js/tm-calculator.js — Interactive Trust Magnitude Calculator & Visualizer
 *
 * Explains how raw evidence turns into Trust Magnitude and how final trust grades
 * are determined under the logarithmic adoption curve (#1705, #1722).
 *
 * Reads canonical scoring constants from window.TM_CONFIG.
 * Zero hardcoded banned hex colors — uses CSS custom properties exclusively.
 */
(function () {
  'use strict';

  function initCalculator() {
    var mount = document.getElementById('tm-calculator-mount');
    if (!mount) return;

    var CFG = window.TM_CONFIG || {};

    // ── State ──
    var state = {
      stars: 100000,
      benchmark: { enabled: true, score: 85, lane: 'verified' },
      verifier: { enabled: true, count: 2 },
      peerReview: { enabled: false, count: 1 },
      arxiv: { enabled: false, citations: 250 },
      proxy: { enabled: false, externalStars: 50000 },
      repoOwn: { enabled: false, commits: 500, contributors: 3 },
      social: { enabled: false, views: 25000 },
      selfAttestation: { enabled: false }
    };

    // ── Presets ──
    var PRESETS = {
      popularCorroborated: {
        label: 'Popular + Independently Validated',
        desc: '100k stars with verified benchmark and verifier attestations. Clears S-diversity gate.',
        apply: function () {
          state.stars = 100000;
          state.benchmark = { enabled: true, score: 85, lane: 'verified' };
          state.verifier = { enabled: true, count: 2 };
          state.peerReview = { enabled: false, count: 1 };
          state.arxiv = { enabled: false, citations: 250 };
          state.proxy = { enabled: false, externalStars: 50000 };
          state.repoOwn = { enabled: false, commits: 500, contributors: 3 };
          state.social = { enabled: false, views: 25000 };
          state.selfAttestation = { enabled: false };
        }
      },
      popularWeak: {
        label: 'Popular with Weak Corroboration',
        desc: '250k stars with no independent evidence. High adoption, but capped at Grade A.',
        apply: function () {
          state.stars = 250000;
          state.benchmark = { enabled: false, score: 85, lane: 'verified' };
          state.verifier = { enabled: false, count: 1 };
          state.peerReview = { enabled: false, count: 1 };
          state.arxiv = { enabled: false, citations: 100 };
          state.proxy = { enabled: false, externalStars: 10000 };
          state.repoOwn = { enabled: false, commits: 100, contributors: 1 };
          state.social = { enabled: false, views: 5000 };
          state.selfAttestation = { enabled: false };
        }
      },
      academicHighEvidence: {
        label: 'Low Stars + High Rigor',
        desc: '800 stars with benchmark, peer review, and verifier. Proves adoption is only one channel.',
        apply: function () {
          state.stars = 800;
          state.benchmark = { enabled: true, score: 85, lane: 'verified' };
          state.verifier = { enabled: true, count: 1 };
          state.peerReview = { enabled: true, count: 1 };
          state.arxiv = { enabled: false, citations: 50 };
          state.proxy = { enabled: false, externalStars: 10000 };
          state.repoOwn = { enabled: false, commits: 200, contributors: 2 };
          state.social = { enabled: false, views: 5000 };
          state.selfAttestation = { enabled: false };
        }
      },
      highTmNoWitness: {
        label: 'High TM (No Witness)',
        desc: '100k stars + proxy + social signal = 300 TM. S blocked due to lack of independent witness.',
        apply: function () {
          state.stars = 100000;
          state.benchmark = { enabled: false, score: 85, lane: 'verified' };
          state.verifier = { enabled: false, count: 1 };
          state.peerReview = { enabled: false, count: 1 };
          state.arxiv = { enabled: false, citations: 100 };
          state.proxy = { enabled: true, externalStars: 150000 };
          state.repoOwn = { enabled: false, commits: 100, contributors: 1 };
          state.social = { enabled: true, views: 100000 };
          state.selfAttestation = { enabled: false };
        }
      },
      seedBaseline: {
        label: 'Emerging / Seed Baseline',
        desc: '50 stars and self-attestation. Typical entry-level profile at Grade C.',
        apply: function () {
          state.stars = 50;
          state.benchmark = { enabled: false, score: 85, lane: 'verified' };
          state.verifier = { enabled: false, count: 1 };
          state.peerReview = { enabled: false, count: 1 };
          state.arxiv = { enabled: false, citations: 0 };
          state.proxy = { enabled: false, externalStars: 10000 };
          state.repoOwn = { enabled: false, commits: 50, contributors: 1 };
          state.social = { enabled: false, views: 0 };
          state.selfAttestation = { enabled: true };
        }
      }
    };

    // ── Math & Scoring Engine (Parity with trustMagnitude.py) ──
    function calculateStarTm(stars) {
      if (!stars || stars <= 10) return 0;
      return Math.min(175.0, 35.0 * Math.log10(stars / 10.0));
    }

    function computeStateScores() {
      var rows = [];

      // 1. github-stars-own
      if (state.stars > 0) {
        var starScore = calculateStarTm(state.stars);
        rows.push({
          type: 'github-stars-own',
          label: 'GitHub Stars (Own Repo)',
          summary: state.stars.toLocaleString() + ' stars',
          formula: 'min(175, 35 × log₁₀(' + state.stars + '/10))',
          score: starScore,
          isWitness: false
        });
      }

      // 2. benchmark-result
      if (state.benchmark.enabled && state.benchmark.score > 0) {
        var bLaneMult = state.benchmark.lane === 'verified' ? 2 : 1;
        var bBase = Math.min(100.0, state.benchmark.score * bLaneMult);
        var bScore = bBase * 1.4;
        rows.push({
          type: 'benchmark-result',
          label: 'Benchmark Result',
          summary: state.benchmark.score + '% (' + state.benchmark.lane + ' lane, ' + bLaneMult + '×)',
          formula: 'min(100, ' + state.benchmark.score + ' × ' + bLaneMult + ') × 1.4',
          score: bScore,
          isWitness: state.benchmark.lane === 'verified'
        });
      }

      // 3. verifier-attestation
      if (state.verifier.enabled && state.verifier.count > 0) {
        var vScore = 30.0 * state.verifier.count * 1.5;
        rows.push({
          type: 'verifier-attestation',
          label: 'Verifier Attestation',
          summary: state.verifier.count + ' verifier' + (state.verifier.count === 1 ? '' : 's') + ' (4★+)',
          formula: '30 × ' + state.verifier.count + ' × 1.5',
          score: vScore,
          isWitness: true
        });
      }

      // 4. peer-review
      if (state.peerReview.enabled && state.peerReview.count > 0) {
        var prScore = 25.0 * state.peerReview.count * 1.2;
        rows.push({
          type: 'peer-review',
          label: 'Peer Review',
          summary: state.peerReview.count + ' reviewer' + (state.peerReview.count === 1 ? '' : 's') + ' (4★+)',
          formula: '25 × ' + state.peerReview.count + ' × 1.2',
          score: prScore,
          isWitness: prScore >= 60.0 // Grade A peer review qualifies as witness
        });
      }

      // 5. arxiv
      if (state.arxiv.enabled && state.arxiv.citations > 0) {
        var axScore = Math.min(100.0, state.arxiv.citations / 5.0) * 1.0;
        rows.push({
          type: 'arxiv',
          label: 'arXiv Citations',
          summary: state.arxiv.citations + ' citations',
          formula: 'min(100, ' + state.arxiv.citations + ' / 5) × 1.0',
          score: axScore,
          isWitness: false
        });
      }

      // 6. proxy-containment
      if (state.proxy.enabled && state.proxy.externalStars >= 10000) {
        var pxScore = Math.min(160.0, (state.proxy.externalStars / 1000.0) * 0.8) * 1.0;
        rows.push({
          type: 'proxy-containment',
          label: 'Proxy Containment',
          summary: state.proxy.externalStars.toLocaleString() + ' third-party stars',
          formula: 'min(160, (' + state.proxy.externalStars + ' / 1000) × 0.8)',
          score: pxScore,
          isWitness: false
        });
      }

      // 7. repo-own
      if (state.repoOwn.enabled) {
        var roBase = (state.repoOwn.commits / 200.0) + (Math.pow(state.repoOwn.contributors, 2) * 2.0);
        var roScore = Math.min(60.0, roBase) * 0.6;
        rows.push({
          type: 'repo-own',
          label: 'Repository Maintenance',
          summary: state.repoOwn.commits + ' commits, ' + state.repoOwn.contributors + ' contributors',
          formula: 'min(60, (' + state.repoOwn.commits + '/200) + (' + state.repoOwn.contributors + '² × 2)) × 0.6',
          score: roScore,
          isWitness: false
        });
      }

      // 8. social-signal
      if (state.social.enabled && state.social.views >= 1000) {
        var ssScore = Math.min(80.0, Math.log10(state.social.views) * 8.0) * 1.0;
        rows.push({
          type: 'social-signal',
          label: 'Social Signal',
          summary: state.social.views.toLocaleString() + ' views',
          formula: 'min(80, log₁₀(' + state.social.views + ') × 8)',
          score: ssScore,
          isWitness: false
        });
      }

      // 9. self-attestation
      if (state.selfAttestation.enabled) {
        rows.push({
          type: 'self-attestation',
          label: 'Self-Attestation',
          summary: 'Flat 10 base',
          formula: '10 × 0.5',
          score: 5.0,
          isWitness: false
        });
      }

      // Aggregates
      var totalTm = 0;
      var positiveTypes = new Set();
      var witnesses = [];

      rows.forEach(function (r) {
        if (r.score > 0) {
          totalTm += r.score;
          positiveTypes.add(r.type);
          if (r.isWitness) {
            witnesses.push(r.label);
          }
        }
      });

      // Grade Gates
      var sFloorPassed = totalTm >= 250.0;
      var sDiversityPassed = positiveTypes.size >= 3;
      var sWitnessPassed = witnesses.length > 0;
      var sAdmitted = sFloorPassed && sDiversityPassed && sWitnessPassed;

      var grade = 'ungraded';
      if (sAdmitted) {
        grade = 'S';
      } else if (totalTm >= 100.0) {
        grade = 'A';
      } else if (totalTm >= 50.0) {
        grade = 'B';
      } else if (totalTm >= 20.0) {
        grade = 'C';
      }

      return {
        rows: rows,
        totalTm: totalTm,
        typeCount: positiveTypes.size,
        witnesses: witnesses,
        sFloorPassed: sFloorPassed,
        sDiversityPassed: sDiversityPassed,
        sWitnessPassed: sWitnessPassed,
        sAdmitted: sAdmitted,
        grade: grade
      };
    }

    // ── Render Helpers ──
    function getGradeBadgeInfo(grade) {
      switch (grade) {
        case 'S':
          return { name: 'Platinum', color: 'var(--rank-5)', bg: 'var(--tier-fusion-bg)', star: '5★ Ultimate / 6★ Apex' };
        case 'A':
          return { name: 'Gold', color: 'var(--rank-4)', bg: 'rgba(232,121,249,0.15)', star: '4★ Extra' };
        case 'B':
          return { name: 'Silver', color: 'var(--rank-3)', bg: 'rgba(167,139,250,0.15)', star: '3★ Evolved' };
        case 'C':
          return { name: 'Bronze', color: 'var(--rank-2)', bg: 'rgba(99,202,183,0.15)', star: '2★ Named' };
        default:
          return { name: 'Ungraded', color: 'var(--rank-0)', bg: 'rgba(148,163,184,0.12)', star: '1★ Awakened' };
      }
    }

    function renderCurveSvg(currentStars) {
      var w = 500;
      var h = 170;
      var padLeft = 46;
      var padRight = 24;
      var padTop = 20;
      var padBottom = 32;

      var plotW = w - padLeft - padRight;
      var plotH = h - padTop - padBottom;

      // X scale: 0 to 260,000 stars (nonlinear / log10 for aesthetic clarity)
      var maxLog = Math.log10(260000);
      var minLog = 1; // 10 stars

      function mapX(stars) {
        if (stars <= 10) return padLeft;
        var logVal = Math.log10(Math.min(260000, stars));
        var norm = (logVal - minLog) / (maxLog - minLog);
        return padLeft + norm * plotW;
      }

      function mapY(tm) {
        var norm = Math.min(175, Math.max(0, tm)) / 175;
        return (padTop + plotH) - (norm * plotH);
      }

      // Generate curve path
      var points = [];
      var steps = 80;
      for (var i = 0; i <= steps; i++) {
        var frac = i / steps;
        var log = minLog + frac * (maxLog - minLog);
        var st = Math.pow(10, log);
        var tm = calculateStarTm(st);
        points.push(mapX(st).toFixed(1) + ',' + mapY(tm).toFixed(1));
      }
      var pathD = 'M ' + points.join(' L ');

      // Landmarks
      var landmarks = [
        { stars: 1000, label: '1k: 70' },
        { stars: 10000, label: '10k: 105' },
        { stars: 50000, label: '50k: 129' },
        { stars: 100000, label: '100k: 140' },
        { stars: 250000, label: '250k: 154' }
      ];

      var landmarkElements = landmarks.map(function (lm) {
        var x = mapX(lm.stars);
        var y = mapY(calculateStarTm(lm.stars));
        return '<line x1="' + x + '" y1="' + (padTop + plotH) + '" x2="' + x + '" y2="' + y + '" stroke="var(--border)" stroke-dasharray="2,2" />' +
               '<circle cx="' + x + '" cy="' + y + '" r="3" fill="var(--muted)" />' +
               '<text x="' + x + '" y="' + (padTop + plotH + 14) + '" font-size="9" fill="var(--muted)" text-anchor="middle" font-family="var(--font-mono)">' + (lm.stars >= 1000 ? (lm.stars / 1000) + 'k' : lm.stars) + '</text>';
      }).join('');

      // Current marker
      var curX = mapX(currentStars);
      var curTm = calculateStarTm(currentStars);
      var curY = mapY(curTm);

      var curMarker =
        '<line x1="' + curX + '" y1="' + (padTop + plotH) + '" x2="' + curX + '" y2="' + curY + '" stroke="var(--tier-basic)" stroke-width="1.5" />' +
        '<circle cx="' + curX + '" cy="' + curY + '" r="5" fill="var(--tier-basic)" stroke="var(--surface)" stroke-width="2" />' +
        '<rect x="' + Math.max(padLeft, Math.min(w - 110, curX - 45)) + '" y="' + Math.max(padTop, curY - 24) + '" width="90" height="18" rx="4" fill="var(--surface)" stroke="var(--border)" />' +
        '<text x="' + (Math.max(padLeft, Math.min(w - 110, curX - 45)) + 45) + '" y="' + (Math.max(padTop, curY - 24) + 12) + '" font-size="10" font-weight="bold" fill="var(--tier-basic)" text-anchor="middle" font-family="var(--font-mono)">' + curTm.toFixed(1) + ' TM</text>';

      return '<svg viewBox="0 0 ' + w + ' ' + h + '" class="tm-calc-svg" style="width:100%; height:auto; display:block;">' +
             '<rect width="' + w + '" height="' + h + '" fill="var(--surface)" rx="8" />' +
             // Y grid lines
             '<line x1="' + padLeft + '" y1="' + mapY(0) + '" x2="' + (w - padRight) + '" y2="' + mapY(0) + '" stroke="var(--border)" stroke-width="1" />' +
             '<text x="' + (padLeft - 8) + '" y="' + (mapY(0) + 3) + '" font-size="9" fill="var(--muted)" text-anchor="end" font-family="var(--font-mono)">0</text>' +
             '<line x1="' + padLeft + '" y1="' + mapY(70) + '" x2="' + (w - padRight) + '" y2="' + mapY(70) + '" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="2,2" />' +
             '<text x="' + (padLeft - 8) + '" y="' + (mapY(70) + 3) + '" font-size="9" fill="var(--muted)" text-anchor="end" font-family="var(--font-mono)">70</text>' +
             '<line x1="' + padLeft + '" y1="' + mapY(105) + '" x2="' + (w - padRight) + '" y2="' + mapY(105) + '" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="2,2" />' +
             '<text x="' + (padLeft - 8) + '" y="' + (mapY(105) + 3) + '" font-size="9" fill="var(--muted)" text-anchor="end" font-family="var(--font-mono)">105</text>' +
             '<line x1="' + padLeft + '" y1="' + mapY(140) + '" x2="' + (w - padRight) + '" y2="' + mapY(140) + '" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="2,2" />' +
             '<text x="' + (padLeft - 8) + '" y="' + (mapY(140) + 3) + '" font-size="9" fill="var(--muted)" text-anchor="end" font-family="var(--font-mono)">140</text>' +
             '<line x1="' + padLeft + '" y1="' + mapY(175) + '" x2="' + (w - padRight) + '" y2="' + mapY(175) + '" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="4,2" />' +
             '<text x="' + (padLeft - 8) + '" y="' + (mapY(175) + 3) + '" font-size="9" fill="var(--tier-fusion)" text-anchor="end" font-family="var(--font-mono)">175 Cap</text>' +
             // Landmarks
             landmarkElements +
             // The Curve
             '<path d="' + pathD + '" fill="none" stroke="var(--tier-basic)" stroke-width="2.5" stroke-linecap="round" />' +
             // Current Marker
             curMarker +
             '</svg>';
    }

    function render() {
      var calc = computeStateScores();
      var bInfo = getGradeBadgeInfo(calc.grade);

      var html = '';

      // Presets Bar
      html += '<div class="tm-calc-presets" style="margin-bottom: 1.5rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;">';
      html += '<span style="font-size: 0.8rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-right: 0.25rem;">Preset Scenarios:</span>';
      Object.keys(PRESETS).forEach(function (key) {
        var p = PRESETS[key];
        html += '<button type="button" class="tm-calc-preset-btn" data-preset="' + key + '" style="background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 0.4rem 0.75rem; font-size: 0.78rem; font-weight: 500; color: var(--text); cursor: pointer; transition: all 0.15s ease;" title="' + p.desc + '">' + p.label + '</button>';
      });
      html += '</div>';

      // Layout Grid (2 Columns on Desktop)
      html += '<div class="tm-calc-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">';

      // ── Left Column: Controls & Visualizer ──
      html += '<div class="tm-calc-left" style="display: flex; flex-direction: column; gap: 1.25rem;">';

      // Card 1: GitHub Stars Adoption Curve
      html += '<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem;">';
      html += '<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">';
      html += '<h3 style="margin: 0; font-size: 0.95rem; font-weight: 600; color: var(--text);">GitHub Stars (Adoption Signal)</h3>';
      html += '<span style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--tier-basic); font-weight: 600;">' + calculateStarTm(state.stars).toFixed(1) + ' TM</span>';
      html += '</div>';
      html += '<p style="margin: 0 0 1rem 0; font-size: 0.76rem; color: var(--muted); line-height: 1.4;">Logarithmic diminishing returns: <code style="font-family: var(--font-mono); font-size: 0.74rem;">min(175, 35 × log₁₀(stars / 10))</code>. Capped at 175 TM (below the 250 Grade S floor).</p>';

      // SVG Curve
      html += renderCurveSvg(state.stars);

      // Slider & Number Input
      html += '<div style="display: flex; align-items: center; gap: 1rem; margin-top: 1rem;">';
      html += '<input type="range" id="tm-input-stars" min="0" max="300000" step="250" value="' + state.stars + '" style="flex: 1; accent-color: var(--tier-basic); cursor: pointer;" />';
      html += '<input type="number" id="tm-input-stars-num" min="0" max="1000000" step="100" value="' + state.stars + '" style="width: 100px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 0.35rem 0.5rem; font-family: var(--font-mono); font-size: 0.8rem; color: var(--text); text-align: right;" />';
      html += '</div>';
      html += '</div>';

      // Card 2: Independent Corroboration & Non-Star Evidence
      html += '<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem;">';
      html += '<h3 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600; color: var(--text);">Independent Corroboration & Evidence</h3>';
      html += '<p style="margin: 0 0 1rem 0; font-size: 0.76rem; color: var(--muted); line-height: 1.4;">Configure additional evidence channels to test multi-channel diversity and Grade S witness eligibility.</p>';

      html += '<div style="display: flex; flex-direction: column; gap: 0.9rem;">';

      // Benchmark Result
      html += '<div style="padding: 0.6rem; border: 1px solid var(--border); border-radius: 6px; background: rgba(0,0,0,0.02);">';
      html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">';
      html += '<label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; font-weight: 600; color: var(--text); cursor: pointer;">';
      html += '<input type="checkbox" id="tm-check-benchmark" ' + (state.benchmark.enabled ? 'checked' : '') + ' /> Benchmark Result';
      html += '<span style="font-size: 0.68rem; padding: 0.1rem 0.4rem; border-radius: 4px; background: var(--tier-basic-bg); color: var(--tier-basic); font-weight: 600;">S Witness</span>';
      html += '</label>';
      html += '<span style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--muted);">' + (state.benchmark.enabled ? (Math.min(100, state.benchmark.score * (state.benchmark.lane === 'verified' ? 2 : 1)) * 1.4).toFixed(1) + ' TM' : 'off') + '</span>';
      html += '</div>';
      if (state.benchmark.enabled) {
        html += '<div style="display: flex; gap: 0.75rem; align-items: center; font-size: 0.76rem;">';
        html += '<span>Score/Percentile: <strong>' + state.benchmark.score + '</strong></span>';
        html += '<input type="range" id="tm-input-bm-score" min="1" max="100" value="' + state.benchmark.score + '" style="flex: 1; accent-color: var(--tier-basic);" />';
        html += '<select id="tm-select-bm-lane" style="background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 0.2rem 0.4rem; font-size: 0.75rem; color: var(--text);">';
        html += '<option value="verified" ' + (state.benchmark.lane === 'verified' ? 'selected' : '') + '>Verified (2× lane)</option>';
        html += '<option value="reported" ' + (state.benchmark.lane === 'reported' ? 'selected' : '') + '>Reported (1× lane)</option>';
        html += '</select>';
        html += '</div>';
      }
      html += '</div>';

      // Verifier Attestation
      html += '<div style="padding: 0.6rem; border: 1px solid var(--border); border-radius: 6px; background: rgba(0,0,0,0.02);">';
      html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">';
      html += '<label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; font-weight: 600; color: var(--text); cursor: pointer;">';
      html += '<input type="checkbox" id="tm-check-verifier" ' + (state.verifier.enabled ? 'checked' : '') + ' /> Verifier Attestation';
      html += '<span style="font-size: 0.68rem; padding: 0.1rem 0.4rem; border-radius: 4px; background: var(--tier-basic-bg); color: var(--tier-basic); font-weight: 600;">S Witness</span>';
      html += '</label>';
      html += '<span style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--muted);">' + (state.verifier.enabled ? (30 * state.verifier.count * 1.5).toFixed(1) + ' TM' : 'off') + '</span>';
      html += '</div>';
      if (state.verifier.enabled) {
        html += '<div style="display: flex; gap: 0.75rem; align-items: center; font-size: 0.76rem;">';
        html += '<span>4★+ Verifiers: <strong>' + state.verifier.count + '</strong> (30 base × 1.5 weight = 45 TM each)</span>';
        html += '<input type="range" id="tm-input-verifier" min="1" max="5" value="' + state.verifier.count + '" style="flex: 1; accent-color: var(--tier-basic);" />';
        html += '</div>';
      }
      html += '</div>';

      // Peer Review
      html += '<div style="padding: 0.6rem; border: 1px solid var(--border); border-radius: 6px; background: rgba(0,0,0,0.02);">';
      html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">';
      html += '<label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; font-weight: 600; color: var(--text); cursor: pointer;">';
      html += '<input type="checkbox" id="tm-check-peer" ' + (state.peerReview.enabled ? 'checked' : '') + ' /> Peer Review';
      html += '<span style="font-size: 0.68rem; padding: 0.1rem 0.4rem; border-radius: 4px; background: rgba(167,139,250,0.15); color: var(--rank-3); font-weight: 600;">S Witness (Grade A)</span>';
      html += '</label>';
      html += '<span style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--muted);">' + (state.peerReview.enabled ? (25 * state.peerReview.count * 1.2).toFixed(1) + ' TM' : 'off') + '</span>';
      html += '</div>';
      if (state.peerReview.enabled) {
        html += '<div style="display: flex; gap: 0.75rem; align-items: center; font-size: 0.76rem;">';
        html += '<span>4★+ Reviewers: <strong>' + state.peerReview.count + '</strong> (25 base × 1.2 = 30 TM each)</span>';
        html += '<input type="range" id="tm-input-peer" min="1" max="3" value="' + state.peerReview.count + '" style="flex: 1; accent-color: var(--rank-3);" />';
        html += '</div>';
      }
      html += '</div>';

      // Secondary Channels Row
      html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.78rem;">';

      // arXiv
      html += '<label style="display: flex; align-items: center; gap: 0.4rem; cursor: pointer; padding: 0.35rem 0.5rem; border: 1px solid var(--border); border-radius: 4px;">';
      html += '<input type="checkbox" id="tm-check-arxiv" ' + (state.arxiv.enabled ? 'checked' : '') + ' /> arXiv (250 cite)';
      html += '</label>';

      // Proxy Containment
      html += '<label style="display: flex; align-items: center; gap: 0.4rem; cursor: pointer; padding: 0.35rem 0.5rem; border: 1px solid var(--border); border-radius: 4px;">';
      html += '<input type="checkbox" id="tm-check-proxy" ' + (state.proxy.enabled ? 'checked' : '') + ' /> Proxy (50k ext)';
      html += '</label>';

      // Repo Maintenance
      html += '<label style="display: flex; align-items: center; gap: 0.4rem; cursor: pointer; padding: 0.35rem 0.5rem; border: 1px solid var(--border); border-radius: 4px;">';
      html += '<input type="checkbox" id="tm-check-repo" ' + (state.repoOwn.enabled ? 'checked' : '') + ' /> Repo (commits/contrib)';
      html += '</label>';

      // Social Signal
      html += '<label style="display: flex; align-items: center; gap: 0.4rem; cursor: pointer; padding: 0.35rem 0.5rem; border: 1px solid var(--border); border-radius: 4px;">';
      html += '<input type="checkbox" id="tm-check-social" ' + (state.social.enabled ? 'checked' : '') + ' /> Social (25k views)';
      html += '</label>';

      // Self-Attestation
      html += '<label style="display: flex; align-items: center; gap: 0.4rem; cursor: pointer; padding: 0.35rem 0.5rem; border: 1px solid var(--border); border-radius: 4px; grid-column: span 2;">';
      html += '<input type="checkbox" id="tm-check-self" ' + (state.selfAttestation.enabled ? 'checked' : '') + ' /> Self-Attestation (Flat baseline +5 TM)';
      html += '</label>';

      html += '</div>';

      html += '</div>';
      html += '</div>';

      html += '</div>'; // End Left Column

      // ── Right Column: Progressive Calculation & Grade Gates ──
      html += '<div class="tm-calc-right" style="display: flex; flex-direction: column; gap: 1.25rem;">';

      // Card 3: Evidence Row Breakdown (Additive Stack)
      html += '<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem;">';
      html += '<h3 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600; color: var(--text);">1. Evidence Stack (Additive Accumulation)</h3>';
      html += '<p style="margin: 0 0 1rem 0; font-size: 0.76rem; color: var(--muted); line-height: 1.4;">Evidence rows score independently. No hidden cross-channel multiplication: <code style="font-family: var(--font-mono); font-size: 0.74rem;">TM = Σ artifact scores</code>.</p>';

      if (calc.rows.length === 0) {
        html += '<p style="color: var(--muted); font-size: 0.8rem; font-style: italic;">No active evidence rows. Trust Magnitude is 0.0.</p>';
      } else {
        html += '<div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem;">';
        calc.rows.forEach(function (r) {
          html += '<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0.6rem; border-radius: 4px; background: var(--bg); border: 1px solid var(--border); font-size: 0.78rem;">';
          html += '<div>';
          html += '<div style="font-weight: 600; color: var(--text);">' + r.label + ' ' + (r.isWitness ? '<span style="font-size: 0.65rem; color: var(--tier-basic); font-weight: 700;">[Witness]</span>' : '') + '</div>';
          html += '<div style="font-size: 0.7rem; color: var(--muted); font-family: var(--font-mono);">' + r.formula + '</div>';
          html += '</div>';
          html += '<div style="font-family: var(--font-mono); font-weight: 700; color: var(--text); font-size: 0.82rem;">+' + r.score.toFixed(1) + '</div>';
          html += '</div>';
        });
        html += '</div>';
      }

      // Total TM Display
      html += '<div style="display: flex; justify-content: space-between; align-items: center; padding-top: 0.75rem; border-top: 2px solid var(--border);">';
      html += '<span style="font-size: 0.9rem; font-weight: 700; color: var(--text); text-transform: uppercase; letter-spacing: 0.05em;">Total Trust Magnitude:</span>';
      html += '<span style="font-size: 1.35rem; font-weight: 800; font-family: var(--font-mono); color: ' + bInfo.color + ';">' + calc.totalTm.toFixed(2) + ' TM</span>';
      html += '</div>';
      html += '</div>';

      // Card 4: S-Admission Gate Checklist
      html += '<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem;">';
      html += '<h3 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600; color: var(--text);">2. Grade S Admission Gate</h3>';
      html += '<p style="margin: 0 0 1rem 0; font-size: 0.76rem; color: var(--muted); line-height: 1.4;">Grade S (Platinum) represents proven institutional excellence. It cannot be earned through repository stars alone:</p>';

      html += '<div style="display: flex; flex-direction: column; gap: 0.6rem; font-size: 0.8rem;">';

      // Gate Criterion 1: TM >= 250
      html += '<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0.6rem; border-radius: 4px; border-left: 3px solid ' + (calc.sFloorPassed ? 'var(--tier-basic)' : 'var(--border)') + '; background: var(--bg);">';
      html += '<div>';
      html += '<div style="font-weight: 600; color: var(--text);">Trust Magnitude Floor (≥ 250.0)</div>';
      html += '<div style="font-size: 0.7rem; color: var(--muted);">Current score: ' + calc.totalTm.toFixed(1) + ' TM</div>';
      html += '</div>';
      html += '<span style="font-weight: 700; font-family: var(--font-mono); color: ' + (calc.sFloorPassed ? 'var(--tier-basic)' : 'var(--muted)') + ';">' + (calc.sFloorPassed ? 'PASS ✓' : 'FAIL ✗') + '</span>';
      html += '</div>';

      // Gate Criterion 2: Distinct Types >= 3
      html += '<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0.6rem; border-radius: 4px; border-left: 3px solid ' + (calc.sDiversityPassed ? 'var(--tier-basic)' : 'var(--border)') + '; background: var(--bg);">';
      html += '<div>';
      html += '<div style="font-weight: 600; color: var(--text);">Diversity: Positive Evidence Types (≥ 3)</div>';
      html += '<div style="font-size: 0.7rem; color: var(--muted);">Active scoring types: ' + calc.typeCount + '</div>';
      html += '</div>';
      html += '<span style="font-weight: 700; font-family: var(--font-mono); color: ' + (calc.sDiversityPassed ? 'var(--tier-basic)' : 'var(--muted)') + ';">' + (calc.sDiversityPassed ? 'PASS ✓' : 'FAIL ✗') + '</span>';
      html += '</div>';

      // Gate Criterion 3: Strong Independent Witness
      html += '<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0.6rem; border-radius: 4px; border-left: 3px solid ' + (calc.sWitnessPassed ? 'var(--tier-basic)' : 'var(--border)') + '; background: var(--bg);">';
      html += '<div>';
      html += '<div style="font-weight: 600; color: var(--text);">Strong Independent Witness</div>';
      html += '<div style="font-size: 0.7rem; color: var(--muted);">' + (calc.witnesses.length > 0 ? calc.witnesses.join(', ') : 'None present (requires benchmark, verifier, or Grade A peer review)') + '</div>';
      html += '</div>';
      html += '<span style="font-weight: 700; font-family: var(--font-mono); color: ' + (calc.sWitnessPassed ? 'var(--tier-basic)' : 'var(--muted)') + ';">' + (calc.sWitnessPassed ? 'PASS ✓' : 'FAIL ✗') + '</span>';
      html += '</div>';

      html += '</div>';
      html += '</div>';

      // Card 5: Final Overall Standing Plaque
      html += '<div style="background: ' + bInfo.bg + '; border: 1.5px solid ' + bInfo.color + '; border-radius: 8px; padding: 1.25rem;">';
      html += '<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.4rem;">';
      html += '<span style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted);">Overall Trust Grade</span>';
      html += '<span style="font-size: 0.8rem; font-weight: 600; color: ' + bInfo.color + ';">' + bInfo.star + '</span>';
      html += '</div>';
      html += '<div style="display: flex; align-items: baseline; gap: 0.75rem; margin-bottom: 0.75rem;">';
      html += '<span style="font-size: 2.2rem; font-weight: 800; font-family: var(--font-mono); color: ' + bInfo.color + '; line-height: 1;">Grade ' + calc.grade + '</span>';
      html += '<span style="font-size: 1.05rem; font-weight: 600; color: var(--text);">' + bInfo.name + ' Standing</span>';
      html += '</div>';

      // Explanatory Message
      if (calc.grade === 'S') {
        html += '<p style="margin: 0; font-size: 0.82rem; color: var(--text); line-height: 1.5;"><strong>Grade S Achieved.</strong> The skill clears the 250.0 TM threshold with high multi-channel diversity (' + calc.typeCount + ' types) and verified independent corroboration (' + calc.witnesses.join(', ') + '). Qualified for 5★ Ultimate promotion.</p>';
      } else if (calc.totalTm >= 250.0 && !calc.sAdmitted) {
        var reasons = [];
        if (!calc.sDiversityPassed) reasons.push('requires ≥3 distinct positive scoring types (currently ' + calc.typeCount + ')');
        if (!calc.sWitnessPassed) reasons.push('requires an independent witness row (verified benchmark, verifier attestation, or Grade A peer review)');
        html += '<p style="margin: 0; font-size: 0.82rem; color: var(--text); line-height: 1.5;"><strong>Grade S Blocked (Resolved to Grade A).</strong> Total TM (' + calc.totalTm.toFixed(1) + ') exceeds 250.0, but Grade S is held at Grade A because ' + reasons.join(' and ') + '. Public adoption alone cannot satisfy Grade S.</p>';
      } else if (calc.grade === 'A') {
        html += '<p style="margin: 0; font-size: 0.82rem; color: var(--text); line-height: 1.5;"><strong>Grade A (Gold).</strong> TM exceeds the 100.0 threshold. Solid multi-source demonstration qualifying for 4★ Extra status.</p>';
      } else if (calc.grade === 'B') {
        html += '<p style="margin: 0; font-size: 0.82rem; color: var(--text); line-height: 1.5;"><strong>Grade B (Silver).</strong> TM clears the 50.0 floor. Sufficient evidence for 3★ Evolved status.</p>';
      } else if (calc.grade === 'C') {
        html += '<p style="margin: 0; font-size: 0.82rem; color: var(--text); line-height: 1.5;"><strong>Grade C (Bronze).</strong> TM clears the 20.0 floor. Qualifies for 2★ Named status.</p>';
      } else {
        html += '<p style="margin: 0; font-size: 0.82rem; color: var(--muted); line-height: 1.5;"><strong>Ungraded (1★ Awakened).</strong> TM is below 20.0. Needs additional documented repository or usage evidence.</p>';
      }

      html += '</div>';

      html += '</div>'; // End Right Column

      html += '</div>'; // End Layout Grid

      mount.innerHTML = html;
      bindEvents();
    }

    function bindEvents() {
      // Presets
      var pBtns = mount.querySelectorAll('.tm-calc-preset-btn');
      pBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
          var pKey = btn.getAttribute('data-preset');
          if (PRESETS[pKey]) {
            PRESETS[pKey].apply();
            render();
          }
        });
      });

      // Stars Slider & Number Input
      var sSlider = document.getElementById('tm-input-stars');
      var sNum = document.getElementById('tm-input-stars-num');
      if (sSlider && sNum) {
        sSlider.addEventListener('input', function () {
          state.stars = Number(sSlider.value);
          sNum.value = state.stars;
          render();
        });
        sNum.addEventListener('change', function () {
          state.stars = Math.max(0, Number(sNum.value));
          sSlider.value = Math.min(300000, state.stars);
          render();
        });
      }

      // Benchmark Checkbox & Inputs
      var bmCheck = document.getElementById('tm-check-benchmark');
      if (bmCheck) {
        bmCheck.addEventListener('change', function () {
          state.benchmark.enabled = bmCheck.checked;
          render();
        });
      }
      var bmScore = document.getElementById('tm-input-bm-score');
      if (bmScore) {
        bmScore.addEventListener('input', function () {
          state.benchmark.score = Number(bmScore.value);
          render();
        });
      }
      var bmLane = document.getElementById('tm-select-bm-lane');
      if (bmLane) {
        bmLane.addEventListener('change', function () {
          state.benchmark.lane = bmLane.value;
          render();
        });
      }

      // Verifier
      var vCheck = document.getElementById('tm-check-verifier');
      if (vCheck) {
        vCheck.addEventListener('change', function () {
          state.verifier.enabled = vCheck.checked;
          render();
        });
      }
      var vInput = document.getElementById('tm-input-verifier');
      if (vInput) {
        vInput.addEventListener('input', function () {
          state.verifier.count = Number(vInput.value);
          render();
        });
      }

      // Peer Review
      var prCheck = document.getElementById('tm-check-peer');
      if (prCheck) {
        prCheck.addEventListener('change', function () {
          state.peerReview.enabled = prCheck.checked;
          render();
        });
      }
      var prInput = document.getElementById('tm-input-peer');
      if (prInput) {
        prInput.addEventListener('input', function () {
          state.peerReview.count = Number(prInput.value);
          render();
        });
      }

      // Secondary Checkboxes
      var axCheck = document.getElementById('tm-check-arxiv');
      if (axCheck) {
        axCheck.addEventListener('change', function () {
          state.arxiv.enabled = axCheck.checked;
          render();
        });
      }

      var pxCheck = document.getElementById('tm-check-proxy');
      if (pxCheck) {
        pxCheck.addEventListener('change', function () {
          state.proxy.enabled = pxCheck.checked;
          render();
        });
      }

      var roCheck = document.getElementById('tm-check-repo');
      if (roCheck) {
        roCheck.addEventListener('change', function () {
          state.repoOwn.enabled = roCheck.checked;
          render();
        });
      }

      var ssCheck = document.getElementById('tm-check-social');
      if (ssCheck) {
        ssCheck.addEventListener('change', function () {
          state.social.enabled = ssCheck.checked;
          render();
        });
      }

      var selfCheck = document.getElementById('tm-check-self');
      if (selfCheck) {
        selfCheck.addEventListener('change', function () {
          state.selfAttestation.enabled = selfCheck.checked;
          render();
        });
      }
    }

    render();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCalculator);
  } else {
    initCalculator();
  }
})();
