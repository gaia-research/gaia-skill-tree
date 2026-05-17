/* ── Hero word hover animations ──────────────────────────────────
   Line 1: "Skills" → "/skills" terminal typing (char-by-char, gold on dark pill)
   Line 2: "Names" → "@names" (EB Garamond italic, honor-red)
   Line 3: "Apex is rare" → white with rainbow text-shadow glow
   Triggered per-line on mouseenter, reverted on mouseleave.
   ============================================================ */
(function () {
  'use strict';

  var skillsLine = document.querySelector('.hero-line[data-line="skills"]');
  var namesLine  = document.querySelector('.hero-line[data-line="names"]');
  var apexLine   = document.querySelector('.hero-line[data-line="apex"]');
  if (!skillsLine || !namesLine || !apexLine) return;

  var skillsWord = skillsLine.querySelector('.hw-skills');
  var namesWord  = namesLine.querySelector('.hw-names');
  var apexWord   = apexLine.querySelector('.hw-apex');
  if (!skillsWord || !namesWord || !apexWord) return;

  /* ── Reduced-motion guard ── */
  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ════════════════════════════════════════════════════════════════
     Line 1 — Skills → /skills (terminal typing)
     ════════════════════════════════════════════════════════════ */
  var SKILLS_TARGET = '/skills';
  var CHAR_DELAY    = 55; // ms per character
  var skillsTimer   = null;

  function clearSkillsTimer() {
    if (skillsTimer !== null) {
      clearInterval(skillsTimer);
      skillsTimer = null;
    }
  }

  skillsLine.addEventListener('mouseenter', function () {
    clearSkillsTimer();
    skillsWord.classList.add('hw-skills--active');

    if (prefersReduced) {
      skillsWord.textContent = SKILLS_TARGET;
      return;
    }

    /* Build fresh: empty text + cursor span */
    skillsWord.textContent = '';
    var cursor = document.createElement('span');
    cursor.className = 'hw-cursor';
    cursor.textContent = '\u2588'; // full block
    skillsWord.appendChild(cursor);

    var i = 0;
    skillsTimer = setInterval(function () {
      if (i < SKILLS_TARGET.length) {
        cursor.before(document.createTextNode(SKILLS_TARGET[i]));
        i++;
      } else {
        clearSkillsTimer();
        cursor.classList.add('hw-cursor--blink');
      }
    }, CHAR_DELAY);
  });

  skillsLine.addEventListener('mouseleave', function () {
    clearSkillsTimer();
    skillsWord.classList.remove('hw-skills--active');
    skillsWord.textContent = 'Skills';
  });

  /* ════════════════════════════════════════════════════════════════
     Line 2 — Names → @names (foundation typography)
     ════════════════════════════════════════════════════════════ */
  namesLine.addEventListener('mouseenter', function () {
    namesWord.classList.add('hw-names--active');
    namesWord.textContent = '@names';
  });

  namesLine.addEventListener('mouseleave', function () {
    namesWord.classList.remove('hw-names--active');
    namesWord.textContent = 'Names';
  });

  /* ════════════════════════════════════════════════════════════════
     Line 3 — Apex is rare → white + rainbow glow
     ════════════════════════════════════════════════════════════ */
  apexLine.addEventListener('mouseenter', function () {
    apexWord.classList.add('hw-apex--active');
  });

  apexLine.addEventListener('mouseleave', function () {
    apexWord.classList.remove('hw-apex--active');
  });
})();
