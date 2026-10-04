// The "back to the top" button: shown once the reader has scrolled a screen down.
(function () {
  var b = document.querySelector('.totop');
  if (!b) return;
  var tick = function () { b.hidden = window.scrollY < window.innerHeight; };
  window.addEventListener('scroll', tick, { passive: true });
  tick();
})();
