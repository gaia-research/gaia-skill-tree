window.switchOsTab = function(btn) {
  var step = btn.closest('.step');
  step.querySelectorAll('.os-tab').forEach(function(b){ b.classList.toggle('active', b === btn); });
  step.querySelectorAll('.os-panel').forEach(function(p){ p.classList.toggle('active', p.dataset.os === btn.dataset.os); });
};

(function(){
  var CLIP='<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M11 5V3a1 1 0 00-1-1H3a1 1 0 00-1 1v7a1 1 0 001 1h2"/></svg>';
  var CHECK='<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="#4ade80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8l4 4 8-8"/></svg>';

  function initMobileNav(){
    var toggle = document.querySelector('.nav-menu-toggle');
    if(!toggle) return;
    var nav = toggle.closest('nav');
    if(!nav) return;
    toggle.addEventListener('click', function(){
      var open = nav.classList.toggle('nav-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.querySelectorAll('a, .nav-tree').forEach(function(item){
      item.addEventListener('click', function(){
        nav.classList.remove('nav-open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  function initCopyButtons(){
    document.querySelectorAll('pre').forEach(function(pre){
      if(pre.closest('.pre-wrap')) return;
      var wrap = document.createElement('div');
      wrap.className = 'pre-wrap';
      pre.parentNode.insertBefore(wrap, pre);
      wrap.appendChild(pre);
      var btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.innerHTML = CLIP;
      btn.title = 'Copy';
      btn.setAttribute('aria-label', 'Copy to clipboard');
      btn.addEventListener('click', function(){
        var text = pre.innerText;
        navigator.clipboard.writeText(text).then(function(){
          btn.innerHTML = CHECK;
          btn.classList.add('copied');
          setTimeout(function(){ btn.innerHTML = CLIP; btn.classList.remove('copied'); }, 1800);
        }).catch(function(){
          btn.innerHTML = CLIP;
          setTimeout(function(){ btn.innerHTML = CLIP; }, 1800);
        });
      });
      wrap.appendChild(btn);
    });
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){ initCopyButtons(); initMobileNav(); });
  } else {
    initCopyButtons();
    initMobileNav();
  }
})();
