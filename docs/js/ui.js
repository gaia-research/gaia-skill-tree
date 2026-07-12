window.switchOsTab = function(btn) {
  var scope = btn.closest('.path-a, .path-b, .rite-step, .step');
  if (!scope) return;
  scope.querySelectorAll('.os-tab').forEach(function(button) {
    var active = button === btn;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  scope.querySelectorAll('.os-panel').forEach(function(panel) {
    panel.classList.toggle('active', panel.dataset.os === btn.dataset.os);
  });
};

(function(){
  // Stage 1 — icon helper. Falls back to a no-op svg if icons.js failed to
  // load (e.g. while debugging) so the copy button stays clickable.
  function icon(id, opts){
    return (typeof window.gaiaIcon === 'function')
      ? window.gaiaIcon(id, opts || { size: 14 })
      : '<svg class="ico" width="14" height="14" aria-hidden="true"></svg>';
  }
  function CLIP(){ return icon('copy', { size: 14 }); }
  function CHECK(){ return icon('copy-check', { size: 14, className: 'ico ico--ok' }); }

  /* ── Reduced-motion helper ── */
  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /* ─────────────────────────────────────────
     MOBILE NAV SHEET
     Drawer is now owned by site-nav.js (it renders a dedicated
     .nav-mobile-drawer sibling element and wires open/close locally).
     This function is kept as a no-op so legacy callers don't break.
     ───────────────────────────────────────── */
  function initNavSheet() {
    /* no-op — see docs/js/site-nav.js */
  }

  /* ─────────────────────────────────────────
     FIRST-LOAD REVEAL SEQUENCE
     Runs once per session (sessionStorage gate).
     3 s cinematic, skippable on any click/keydown.
     Respects prefers-reduced-motion (instant skip).
     ───────────────────────────────────────── */
  function initFirstLoadReveal() {
    var SEEN_KEY = 'gaia-intro-seen';

    /* Skip entirely under reduced motion or if already seen */
    if (prefersReducedMotion()) return;
    if (sessionStorage.getItem(SEEN_KEY)) return;

    /* Mark as seen immediately so a refresh during the intro doesn't re-run */
    sessionStorage.setItem(SEEN_KEY, '1');

    /* Build overlay */
    var overlay = document.createElement('div');
    overlay.className = 'intro-overlay';
    overlay.setAttribute('aria-hidden', 'true');

    var line1 = document.createElement('div');
    line1.className = 'intro-reveal-line';
    line1.textContent = 'Skills are catalogued.';

    var line2 = document.createElement('div');
    line2.className = 'intro-reveal-line';
    line2.textContent = 'Names are earned.';

    var skipHint = document.createElement('div');
    skipHint.className = 'intro-skip';
    skipHint.textContent = 'click anywhere to skip';

    overlay.appendChild(line1);
    overlay.appendChild(line2);
    overlay.appendChild(skipHint);
    document.body.appendChild(overlay);

    var skipped = false;
    var timers = [];

    function dismiss() {
      if (skipped) return;
      skipped = true;
      timers.forEach(clearTimeout);
      overlay.classList.add('fading');
      setTimeout(function() { overlay.classList.add('done'); }, 1250);
    }

    /* Click or keydown skips */
    document.addEventListener('click', dismiss, { once: true });
    document.addEventListener('keydown', dismiss, { once: true });

    /* Sequence: line1 at 0.3s, line2 at 0.9s, dismiss at 1.8s */
    timers.push(setTimeout(function() {
      if (!skipped) line1.classList.add('visible');
    }, 300));
    timers.push(setTimeout(function() {
      if (!skipped) line2.classList.add('visible');
    }, 900));
    timers.push(setTimeout(function() {
      dismiss();
    }, 1800));
  }

  /* ─────────────────────────────────────────
     COPY BUTTONS
     ───────────────────────────────────────── */
  /* Clipboard write with fallback for insecure contexts (HTTP / LAN IP) */
  function copyToClipboard(text){
    if(window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText){
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function(resolve, reject){
      try{
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand('copy');
        document.body.removeChild(ta);
        ok ? resolve() : reject(new Error('execCommand returned false'));
      }catch(err){ reject(err); }
    });
  }
  window.copyToClipboard = copyToClipboard;

  function flashCopied(btn){
    btn.innerHTML = CHECK();
    btn.classList.add('copied');
    setTimeout(function(){ btn.innerHTML = CLIP(); btn.classList.remove('copied'); }, 1600);
  }
  // Stage 1 — expose the flash-to-check helper so other call sites (the
  // skill explorer install button, for example) can share the animation.
  window.gaiaFlashCopied = flashCopied;

  function initCopyButtons(){
    document.querySelectorAll('pre').forEach(function(pre){
      if(pre.closest('.pre-wrap')) return;
      var wrap = document.createElement('div');
      wrap.className = 'pre-wrap';
      pre.parentNode.insertBefore(wrap, pre);
      wrap.appendChild(pre);
      var btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.innerHTML = CLIP();
      btn.title = 'Copy';
      btn.setAttribute('aria-label', 'Copy to clipboard');
      btn.addEventListener('click', function(){
        copyToClipboard(pre.innerText).then(function(){ flashCopied(btn); }).catch(function(){
          /* surface failure visibly */
          btn.title = 'Copy failed — select and copy manually';
        });
      });
      wrap.appendChild(btn);
    });
  }

  function initHeroInstallCopy() {
    var copy = document.querySelector('[data-hero-install-copy]');
    if (!copy) return;

    var output = document.querySelector('[data-hero-install-output]');
    var icon = copy.querySelector('use');
    var platformButtons = Array.prototype.slice.call(document.querySelectorAll('[data-hero-install-platform]'));
    var commands = {
      curl: {
        value: 'curl -fsSL https://gaiaskilltree.com/install.sh | sh',
        label: 'Copy the macOS and Linux install command'
      },
      windows: {
        value: 'iex (irm https://gaiaskilltree.com/install.ps1)',
        label: 'Copy the Windows install command'
      }
    };
    var activePlatform = 'curl';
    var copyIcon = icon ? icon.getAttribute('href') : '';
    var copiedIcon = copyIcon.replace('#copy', '#copy-check');

    function selectPlatform(platform) {
      var command = commands[platform];
      if (!command) return;
      activePlatform = platform;
      copy.dataset.heroInstallCopy = command.value;
      copy.setAttribute('aria-label', command.label);
      if (output) output.textContent = command.value;
      platformButtons.forEach(function(button) {
        var active = button.dataset.heroInstallPlatform === platform;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
    }

    window.gaiaSetHeroInstallPlatform = selectPlatform;

    copy.addEventListener('click', function() {
      copyToClipboard(copy.dataset.heroInstallCopy).then(function() {
        copy.classList.add('copied');
        copy.setAttribute('aria-label', 'Install command copied');
        if (icon) icon.setAttribute('href', copiedIcon);
        setTimeout(function() {
          copy.classList.remove('copied');
          if (icon) icon.setAttribute('href', copyIcon);
          copy.setAttribute('aria-label', copy.dataset.heroInstallCopy === commands.windows.value
            ? commands.windows.label
            : commands.curl.label);
        }, 1600);
      }).catch(function() {
        copy.title = 'Copy failed — select and copy manually';
      });
    });
  }

  /* ─────────────────────────────────────────
     SCROLL TO TOP
     ───────────────────────────────────────── */
  function initScrollToTop() {
    var btn = document.getElementById('scrollToTop');
    if (!btn) return;
    window.addEventListener('scroll', function() {
      if (window.scrollY > 300) {
        btn.classList.add('visible');
      } else {
        btn.classList.remove('visible');
      }
    }, { passive: true });
    btn.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ─────────────────────────────────────────
     AGENT COPY BUTTONS
     ───────────────────────────────────────── */
  function initAgentCopyBtn() {
    var btn = document.getElementById('copyAgentBtn');
    var footerBtn = document.getElementById('copyAgentFooterBtn');

    function handleCopy(targetBtn) {
      if (!targetBtn || targetBtn.disabled) return;
      var origHTML = targetBtn.innerHTML;
      var origAria = targetBtn.getAttribute('aria-label') || 'Copy page context for agents';
      targetBtn.disabled = true;
      targetBtn.innerHTML = icon('copy', { size: 15, className: 'ico' });
      targetBtn.style.opacity = '0.5';
      targetBtn.setAttribute('aria-label', 'Fetching page context...');

      var version = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
      var prefix = (typeof window.gaiaIconBase === 'function') ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '') : '';
      fetch(prefix + 'agent.md' + version)
        .then(function(r) {
          if (!r.ok) throw new Error(r.status);
          return r.text();
        })
        .then(function(text) {
          return copyToClipboard(text);
        })
        .then(function() {
          targetBtn.innerHTML = icon('copy-check', { size: 15, className: 'ico ico--ok' });
          targetBtn.style.opacity = '';
          targetBtn.setAttribute('aria-label', 'Page context copied successfully!');
          targetBtn.classList.add('copied');
          setTimeout(function() {
            targetBtn.innerHTML = origHTML;
            targetBtn.style.opacity = '';
            targetBtn.setAttribute('aria-label', origAria);
            targetBtn.classList.remove('copied');
            targetBtn.disabled = false;
          }, 1800);
        })
        .catch(function() {
          targetBtn.innerHTML = origHTML;
          targetBtn.style.opacity = '';
          targetBtn.setAttribute('aria-label', 'Failed to copy page context');
          targetBtn.disabled = false;
          setTimeout(function() {
            targetBtn.setAttribute('aria-label', origAria);
          }, 1800);
        });
    }

    if (btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        handleCopy(btn);
      });
    }
    if (footerBtn) {
      footerBtn.addEventListener('click', function(e) {
        e.preventDefault();
        handleCopy(footerBtn);
      });
    }
  }

  function initAgentPrompts() {
    document.querySelectorAll('[data-prompt-copy]').forEach(function(button) {
      var label = button.querySelector('span');
      var iconUse = button.querySelector('use');
      var originalLabel = label ? label.textContent : '';
      var originalIcon = iconUse ? iconUse.getAttribute('href') : '';

      button.addEventListener('click', function() {
        var prompt = document.getElementById(button.dataset.promptCopy);
        if (!prompt) return;
        copyToClipboard(prompt.textContent.trim()).then(function() {
          button.classList.add('copied');
          if (label) label.textContent = 'Copied';
          if (iconUse) iconUse.setAttribute('href', originalIcon.replace('#copy', '#copy-check'));
          setTimeout(function() {
            button.classList.remove('copied');
            if (label) label.textContent = originalLabel;
            if (iconUse) iconUse.setAttribute('href', originalIcon);
          }, 1600);
        }).catch(function() {
          button.title = 'Copy failed — select and copy the prompt manually';
        });
      });
    });
  }

  function initAgentPromptBuilder() {
    var repoInput = document.getElementById('agentRepoInput');
    var repoPrompt = document.getElementById('agentRepoPrompt');
    var standalonePrompt = document.getElementById('agentStandalonePrompt');
    var fetcherContainer = document.getElementById('agentSkillFetcher');
    var fetchBtn = document.getElementById('fetchSkillsBtn');
    var checkboxesContainer = document.getElementById('agentSkillCheckboxes');

    if (!repoInput || !repoPrompt || !standalonePrompt) return;

    var repoBaseText = repoPrompt.textContent;
    var standaloneBaseText = standalonePrompt.textContent;
    var currentSkills = [];

    function parseGithubUrl(url) {
      var m = url.match(/github\.com\/([^\/]+)\/([^\/]+)/);
      return m ? { owner: m[1], repo: m[2].replace(/\.git$/, '') } : null;
    }

    function renderPrompts() {
      var url = repoInput.value.trim();
      var isGh = parseGithubUrl(url);

      // Update Repo Prompt
      if (url) {
        repoPrompt.textContent = repoBaseText.replace('my current repository', 'the repository at ' + url);
      } else {
        repoPrompt.textContent = repoBaseText;
      }

      // Update Standalone Prompt
      var sText = standaloneBaseText;
      if (url) {
        var qty = currentSkills.length > 0 ? currentSkills.length : 'standalone';
        sText = sText.replace('Prepare one standalone skill for Gaia Intake on my behalf.',
          'Prepare ' + qty + ' skill(s) for Gaia Intake on my behalf from ' + url + '.');
      }
      if (currentSkills.length > 0) {
        var list = '\n\nSpecifically target these skills:\n' + currentSkills.map(function(s){ return '- ' + s; }).join('\n');
        sText = sText.replace('\n\nUse https://github.com', list + '\n\nUse https://github.com');
      }
      standalonePrompt.textContent = sText;

      if (isGh) {
        fetcherContainer.removeAttribute('hidden');
      } else {
        fetcherContainer.setAttribute('hidden', '');
        checkboxesContainer.innerHTML = '';
        currentSkills = [];
        if (fetchBtn) {
          fetchBtn.textContent = 'Fetch SKILL.md files';
          fetchBtn.disabled = false;
        }
      }
    }

    repoInput.addEventListener('input', renderPrompts);

    if (fetchBtn) {
      fetchBtn.addEventListener('click', function() {
        var isGh = parseGithubUrl(repoInput.value.trim());
        if (!isGh) return;

        fetchBtn.disabled = true;
        fetchBtn.textContent = 'Fetching...';

        fetch('https://api.github.com/repos/' + isGh.owner + '/' + isGh.repo + '/git/trees/HEAD?recursive=1')
          .then(function(r) { return r.json(); })
          .then(function(data) {
            fetchBtn.textContent = 'Fetch SKILL.md files';
            fetchBtn.disabled = false;
            checkboxesContainer.innerHTML = '';
            currentSkills = [];
            renderPrompts();

            if (!data.tree) {
              fetchBtn.textContent = 'Failed to fetch';
              return;
            }

            var skills = [];
            data.tree.forEach(function(item) {
              if (item.path.endsWith('SKILL.md') || item.path.endsWith('skill.md')) {
                var parts = item.path.split('/');
                if (parts.length > 1) {
                  skills.push(parts[parts.length - 2]);
                } else {
                  skills.push('root');
                }
              }
            });

            if (skills.length === 0) {
              checkboxesContainer.innerHTML = '<span style="font-size:.7rem;color:var(--muted)">No SKILL.md files found.</span>';
              return;
            }

            skills.forEach(function(s) {
              var lbl = document.createElement('label');
              lbl.className = 'agent-skill-label';
              var cb = document.createElement('input');
              cb.type = 'checkbox';
              cb.value = s;
              cb.addEventListener('change', function() {
                if (cb.checked) {
                  currentSkills.push(s);
                } else {
                  currentSkills = currentSkills.filter(function(cs) { return cs !== s; });
                }
                renderPrompts();
              });
              lbl.appendChild(cb);
              lbl.appendChild(document.createTextNode(s));
              checkboxesContainer.appendChild(lbl);
            });
          })
          .catch(function() {
            fetchBtn.textContent = 'Error fetching skills';
            fetchBtn.disabled = false;
          });
      });
    }
  }

  /* ─────────────────────────────────────────
     INIT
     ───────────────────────────────────────── */
  function init() {
    initCopyButtons();
    initHeroInstallCopy();
    initNavSheet();
    initFirstLoadReveal();
    initScrollToTop();
    initAgentCopyBtn();
    initAgentPrompts();
    initAgentPromptBuilder();
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
