// Fills the side column of a page with real drawings of the Voynich, as many as fit the height of the text.
// The first drawing is the page's own; the others come from img/margin/margin.json, in an order that differs by page.
(function () {
  var side = document.querySelector('.spread > .side');
  var text = document.querySelector('.spread > .text');
  if (!side || !text || !window.fetch) return;
  var pool = null;
  var GAP = 34;

  function seed() {
    var s = location.pathname, h = 7;
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 9973;
    return h;
  }

  function fill() {
    if (!pool) return;
    side.querySelectorAll('.extra').forEach(function (e) { e.remove(); });
    if (getComputedStyle(side).flexDirection !== 'column' || side.offsetWidth < 80) return;
    var width = side.clientWidth;
    var used = 0;
    Array.prototype.forEach.call(side.children, function (c) { used += c.offsetHeight + GAP; });
    var room = text.offsetHeight - used;
    var shown = Array.prototype.map.call(side.querySelectorAll('img'), function (i) { return i.getAttribute('src'); });
    var start = seed() % pool.length;
    for (var k = 0; k < pool.length; k++) {
      var d = pool[(start + k) % pool.length];
      var src = 'img/margin/' + d.f + '.jpg';
      if (shown.indexOf(src) >= 0) continue;
      var w = Math.min(width, d.w), h = Math.round(w * d.h / d.w);
      if (h + GAP + 30 > room) continue;           // too tall for what is left: try a smaller one
      var fig = document.createElement('figure');
      fig.className = 'illus extra';
      fig.innerHTML = '<img src="' + src + '" width="' + d.w + '" height="' + d.h + '" loading="lazy" alt="' +
        d.alt.replace(/"/g, '&quot;') + '"><figcaption>Beinecke MS 408, f. ' + d.f.slice(1) + '</figcaption>';
      side.appendChild(fig);
      room -= h + GAP + 30;
      if (room < 140) break;
    }
  }

  var timer = 0;
  function later() { clearTimeout(timer); timer = setTimeout(fill, 250); }
  fetch('img/margin/margin.json').then(function (r) { return r.json(); }).then(function (d) {
    pool = d;
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fill); else fill();
    if (window.ResizeObserver) new ResizeObserver(later).observe(text);
    window.addEventListener('resize', later);
  }).catch(function () {});
})();
