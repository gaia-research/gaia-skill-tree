/* icons.js — injects the SVG sprite into the document body so all
 * <use href="#..."> references resolve without XHR cross-origin issues.
 * Must be loaded BEFORE any script that uses icon().
 */
(function () {
  var base = document.documentElement.getAttribute('data-icon-base') || 'assets/icons.svg';

  function inject(svgText) {
    var div = document.createElement('div');
    div.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;pointer-events:none';
    div.innerHTML = svgText;
    document.body.insertBefore(div, document.body.firstChild);
  }

  fetch(base)
    .then(function (r) { return r.text(); })
    .then(inject)
    .catch(function () {
      /* silently ignore — SVG use with href still resolves via URL */
    });

  /* Global helper: icon(id, size) → inline <svg> string */
  window.icon = function (id, size) {
    size = size || 16;
    var base = document.documentElement.getAttribute('data-icon-base') || 'assets/icons.svg';
    return (
      '<svg class="ico" width="' + size + '" height="' + size + '" ' +
      'aria-hidden="true" focusable="false">' +
      '<use href="' + base + '#' + id + '"/></svg>'
    );
  };
})();
