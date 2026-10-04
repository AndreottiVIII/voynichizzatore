// E-mail addresses are written in two halves in the page and joined here, to keep them away from address harvesters.
(function () {
  document.querySelectorAll('a.mail').forEach(function (a) {
    var m = a.getAttribute('data-u') + '@' + a.getAttribute('data-d');
    a.href = 'mailto:' + m;
    a.textContent = m;
  });
})();

// The "back to the top" button: shown once the reader has scrolled a screen down.
(function () {
  var b = document.querySelector('.totop');
  if (!b) return;
  var tick = function () { b.hidden = window.scrollY < window.innerHeight; };
  window.addEventListener('scroll', tick, { passive: true });
  tick();
})();
