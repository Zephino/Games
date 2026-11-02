/**
 * Gameplay clips on the game cards.
 *
 * Each card's <video data-clips="a.mp4,b.mp4,c.mp4"> plays its clips one
 * after another, muted, only while the card is on screen. Every clip also
 * exists as .webm (VP9), used when the browser supports it; otherwise .mp4
 * (H.264), which every major browser plays. The dots on the video show which
 * clip is playing.
 *
 * Clips don't start by themselves when the visitor asks for reduced motion,
 * or when the browser refuses autoplay (for example iPhone Low Power Mode or
 * a data saver). Then the card's "Watch gameplay" button appears instead,
 * and a click plays them: browsers always allow playback the visitor starts.
 */
(() => {
  "use strict";

  const videos = Array.from(document.querySelectorAll("video[data-clips]"));
  if (!videos.length) return;
  const useWebm = videos[0].canPlayType('video/webm; codecs="vp9"') !== "";
  const autoplay = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function setup(video) {
    const clips = video.dataset.clips.split(",")
      .map((clip) => (useWebm ? clip.replace(/\.mp4$/, ".webm") : clip));
    const card = video.closest(".card");
    const dots = Array.from(card.querySelectorAll(".clip-dots i"));
    const toggle = card.querySelector(".clip-toggle");
    let index = 0;
    let wanted = autoplay; // Should the clips play while the card is on screen?
    let visible = false;

    function show(next) {
      index = next % clips.length;
      // Show the next clip's first frame while it loads, so there's no flash.
      video.poster = clips[index].replace(/\.(mp4|webm)$/, ".jpg");
      video.src = clips[index];
      dots.forEach((dot, i) => dot.classList.toggle("on", i === index));
    }

    function label() {
      const playing = wanted && !video.paused;
      toggle.textContent = playing ? "❚❚ Pause" : "▶ Watch gameplay";
      toggle.setAttribute("aria-pressed", String(playing));
    }

    function play() {
      if (!video.getAttribute("src")) show(index);
      video.play().then(label, (error) => {
        // Autoplay was refused: offer the button so the visitor can start it.
        if (error.name !== "NotAllowedError") console.warn("Clip failed to play:", error);
        wanted = false;
        toggle.hidden = false;
        label();
      });
    }

    function update() {
      if (wanted && visible) play();
      else video.pause();
      label();
    }

    video.addEventListener("ended", () => { show(index + 1); play(); });
    video.addEventListener("pause", label);
    toggle.addEventListener("click", () => {
      wanted = !(wanted && !video.paused);
      update();
    });
    toggle.hidden = autoplay;
    label();

    return (isVisible) => { visible = isVisible; update(); };
  }

  const players = new Map(videos.map((video) => [video, setup(video)]));

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) players.get(entry.target)(entry.isIntersecting);
  }, { threshold: 0.35 });

  videos.forEach((video) => observer.observe(video));
})();
