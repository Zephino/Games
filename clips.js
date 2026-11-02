/**
 * Gameplay clips on the game cards.
 *
 * Each card's <video data-clips="a.mp4,b.mp4,c.mp4"> plays its clips one
 * after another, muted, only while the card is on screen. Every clip also
 * exists as .webm (VP9), used when the browser supports it; otherwise .mp4
 * (H.264), which every major browser plays. Visitors who ask
 * for reduced motion keep the still poster image instead. The dots on the
 * video show which clip is playing.
 */
(() => {
  "use strict";

  const videos = Array.from(document.querySelectorAll("video[data-clips]"));
  if (!videos.length) return;
  const useWebm = videos[0].canPlayType('video/webm; codecs="vp9"') !== "";
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  function setup(video) {
    const clips = video.dataset.clips.split(",")
      .map((clip) => (useWebm ? clip.replace(/\.mp4$/, ".webm") : clip));
    const dots = Array.from(video.parentElement.querySelectorAll(".clip-dots i"));
    let index = 0;

    function show(next) {
      index = next % clips.length;
      // Show the next clip's first frame while it loads, so there's no flash.
      video.poster = clips[index].replace(/\.(mp4|webm)$/, ".jpg");
      video.src = clips[index];
      dots.forEach((dot, i) => dot.classList.toggle("on", i === index));
    }

    function play() {
      if (!video.getAttribute("src")) show(index);
      // Browsers may refuse autoplay (for example in data-saver modes); the
      // poster image then stays, which is the intended fallback.
      video.play().catch(() => {});
    }

    video.addEventListener("ended", () => { show(index + 1); play(); });
    return { play, pause: () => video.pause() };
  }

  const players = new Map(videos.map((video) => [video, setup(video)]));

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      const player = players.get(entry.target);
      if (entry.isIntersecting) player.play();
      else player.pause();
    }
  }, { threshold: 0.35 });

  videos.forEach((video) => observer.observe(video));
})();
