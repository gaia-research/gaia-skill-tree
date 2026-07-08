// Add to the Ascension v2 scroll-linked parallax loop.
const haze = ascension.querySelector(".ao-haze");
const hazeRate = 0.25;

function updateHazeParallax(progress, travel) {
  haze?.style.setProperty("--ao-haze-y", `${progress * travel * (1 - hazeRate)}px`);
}
