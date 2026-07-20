const sections = [...document.querySelectorAll("main section[id]")];
const navLinks = [...document.querySelectorAll(".top-nav a")];
const navToggle = document.querySelector(".nav-toggle");
const primaryNav = document.querySelector(".top-nav");

function updateActiveNav() {
  const marker = (document.querySelector(".site-header")?.getBoundingClientRect().bottom || 76) + 24;
  let activeId = sections[0]?.id;

  sections.forEach((section) => {
    if (section.getBoundingClientRect().top <= marker) activeId = section.id;
  });

  navLinks.forEach((link) => {
    const isActive = link.getAttribute("href") === `#${activeId}`;
    link.classList.toggle("active", isActive);
    if (isActive) link.setAttribute("aria-current", "location");
    else link.removeAttribute("aria-current");
  });
}

function closeMobileNav() {
  primaryNav?.classList.remove("open");
  navToggle?.setAttribute("aria-expanded", "false");
}

navToggle?.addEventListener("click", () => {
  const nextOpen = !primaryNav.classList.contains("open");
  primaryNav.classList.toggle("open", nextOpen);
  navToggle.setAttribute("aria-expanded", String(nextOpen));
});

navLinks.forEach((link) => link.addEventListener("click", closeMobileNav));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeMobileNav();
    navToggle?.focus();
  }
});

updateActiveNav();
document.addEventListener("scroll", updateActiveNav, { passive: true });
window.addEventListener("resize", updateActiveNav);

const matrixButtons = [...document.querySelectorAll("button.matrix-cell[data-video]")];
const player = document.querySelector("[data-player-video]");
const playerPoster = document.querySelector("[data-player-poster]");
const playerLoad = document.querySelector("[data-player-load]");
const playerTitle = document.querySelector("[data-player-title]");
const playerNote = document.querySelector("[data-player-note]");

let selectedVideo = matrixButtons[0]?.dataset.video || "";

function selectMatrixCell(button, announce = true) {
  matrixButtons.forEach((item) => {
    const selected = item === button;
    item.classList.toggle("selected", selected);
    item.setAttribute("aria-pressed", String(selected));
  });

  selectedVideo = button.dataset.video;
  if (playerTitle) playerTitle.textContent = button.dataset.title;
  if (playerNote) playerNote.textContent = button.dataset.note;
  if (playerPoster) {
    playerPoster.src = button.dataset.poster;
    playerPoster.alt = `Contact sheet for ${button.dataset.title}`;
    playerPoster.hidden = false;
  }
  if (player) {
    player.pause();
    player.removeAttribute("src");
    player.load();
    player.hidden = true;
  }
  if (playerLoad) {
    playerLoad.hidden = false;
    playerLoad.textContent = "▶ Load selected clip";
    playerLoad.setAttribute("aria-label", `Load and play ${button.dataset.title}`);
  }

  if (announce) document.querySelector(".shared-player")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

matrixButtons.forEach((button) => {
  button.setAttribute("aria-pressed", "false");
  button.addEventListener("click", () => selectMatrixCell(button));
});

if (matrixButtons[0]) selectMatrixCell(matrixButtons[0], false);

playerLoad?.addEventListener("click", async () => {
  if (!player || !selectedVideo) return;
  player.src = selectedVideo;
  player.hidden = false;
  if (playerPoster) playerPoster.hidden = true;
  playerLoad.hidden = true;
  player.load();
  try {
    await player.play();
  } catch {
    player.controls = true;
  }
});

document.querySelectorAll(".load-inline-video").forEach((button) => {
  button.addEventListener("click", async () => {
    const stage = button.closest(".player-stage");
    const video = stage?.querySelector("video");
    const poster = stage?.querySelector("img");
    if (!video || !button.dataset.videoSrc) return;

    video.src = button.dataset.videoSrc;
    if (button.dataset.trackSrc) {
      const track = document.createElement("track");
      track.kind = "captions";
      track.label = "English labels";
      track.srclang = "en";
      track.src = button.dataset.trackSrc;
      video.appendChild(track);
    }
    video.hidden = false;
    if (poster) poster.hidden = true;
    button.hidden = true;
    video.load();
    try {
      await video.play();
    } catch {
      video.controls = true;
    }
  }, { once: true });
});

const refineTopics = [...document.querySelectorAll("[data-refine-topic]")];
const refineColumns = [...document.querySelectorAll("[data-refine-column]")];
const refineScores = document.querySelector("[data-refine-score-list]");
const refineVerdict = document.querySelector("[data-refine-verdict]");

function resetRefinementColumn(column, topicButton) {
  const key = column.dataset.refineColumn;
  const topic = topicButton.dataset.topicTitle;
  const videoSrc = topicButton.dataset[`${key}Video`];
  const posterSrc = topicButton.dataset[`${key}Poster`];
  const trackSrc = topicButton.dataset[`${key}Track`] || "";
  const note = topicButton.dataset[`${key}Note`] || "";
  const stage = column.querySelector(".player-stage");
  const poster = stage?.querySelector("img");
  const video = stage?.querySelector("video");
  const load = stage?.querySelector(".load-refinement-video");
  const noteNode = column.querySelector("[data-refine-note]");
  const nameNode = column.querySelector("[data-refine-name]");
  const roundLabel = key === "v0" ? "project-native v0" : key === "r1" ? "round 1" : "round 5";

  if (video) {
    video.pause();
    video.removeAttribute("src");
    video.querySelectorAll("track").forEach((track) => track.remove());
    video.load();
    video.hidden = true;
    video.setAttribute("aria-label", `${topic} ${roundLabel}`);
  }
  if (poster) {
    poster.src = posterSrc;
    poster.alt = `${topic} ${roundLabel} contact sheet`;
    poster.hidden = false;
  }
  if (load) {
    load.dataset.videoSrc = videoSrc;
    if (trackSrc) load.dataset.trackSrc = trackSrc;
    else delete load.dataset.trackSrc;
    load.hidden = false;
    load.setAttribute("aria-label", `Load ${topic} ${roundLabel}${trackSrc ? " with captions" : ""}`);
  }
  if (noteNode) noteNode.textContent = note;
  if (nameNode) nameNode.textContent = topic;
}

function selectRefinementTopic(topicButton) {
  refineTopics.forEach((button) => {
    const selected = button === topicButton;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  refineColumns.forEach((column) => resetRefinementColumn(column, topicButton));

  const scores = (topicButton.dataset.scores || "").split(",");
  if (refineScores) {
    refineScores.setAttribute("aria-label", `${topicButton.dataset.topicTitle} scores over five rounds`);
    refineScores.querySelectorAll("b").forEach((node, index) => { node.textContent = scores[index] || ""; });
  }
  if (refineVerdict) {
    refineVerdict.textContent = topicButton.dataset.refineTopic === "ess" ? "borderline oral-ready, narration recommended" : "oral-ready visual";
  }
}

refineTopics.forEach((button) => button.addEventListener("click", () => selectRefinementTopic(button)));

document.querySelectorAll(".load-refinement-video").forEach((button) => {
  button.addEventListener("click", async () => {
    const stage = button.closest(".player-stage");
    const video = stage?.querySelector("video");
    const poster = stage?.querySelector("img");
    if (!video || !button.dataset.videoSrc) return;

    video.querySelectorAll("track").forEach((track) => track.remove());
    video.src = button.dataset.videoSrc;
    if (button.dataset.trackSrc) {
      const track = document.createElement("track");
      track.kind = "captions";
      track.label = "English narration cues";
      track.srclang = "en";
      track.src = button.dataset.trackSrc;
      track.default = true;
      video.appendChild(track);
    }
    video.hidden = false;
    if (poster) poster.hidden = true;
    button.hidden = true;
    video.load();
    try {
      await video.play();
    } catch {
      video.controls = true;
    }
  });
});

const referenceChoices = [...document.querySelectorAll("[data-reference-video]")];
const referenceVideo = document.querySelector("[data-reference-player-video]");
const referencePoster = document.querySelector("[data-reference-player-poster]");
const referenceLoad = document.querySelector("[data-reference-load]");
const referenceTitle = document.querySelector("[data-reference-player-title]");
const referenceNote = document.querySelector("[data-reference-player-note]");
let selectedReference = referenceChoices[0]?.dataset.referenceVideo || "";

function selectReference(choice) {
  referenceChoices.forEach((item) => {
    const selected = item === choice;
    item.classList.toggle("selected", selected);
    item.setAttribute("aria-pressed", String(selected));
  });

  selectedReference = choice.dataset.referenceVideo;
  if (referenceTitle) referenceTitle.textContent = choice.dataset.referenceTitle;
  if (referenceNote) referenceNote.textContent = choice.dataset.referenceNote;
  if (referencePoster) {
    referencePoster.src = choice.dataset.referencePoster;
    referencePoster.alt = `${choice.dataset.referenceTitle} poster`;
    referencePoster.hidden = false;
  }
  if (referenceVideo) {
    referenceVideo.pause();
    referenceVideo.removeAttribute("src");
    referenceVideo.load();
    referenceVideo.hidden = true;
  }
  if (referenceLoad) {
    referenceLoad.hidden = false;
    referenceLoad.setAttribute("aria-label", `Load and play ${choice.dataset.referenceTitle} source reference`);
  }
}

referenceChoices.forEach((choice) => choice.addEventListener("click", () => selectReference(choice)));

referenceLoad?.addEventListener("click", async () => {
  if (!referenceVideo || !selectedReference) return;
  referenceVideo.src = selectedReference;
  referenceVideo.hidden = false;
  if (referencePoster) referencePoster.hidden = true;
  referenceLoad.hidden = true;
  referenceVideo.load();
  try {
    await referenceVideo.play();
  } catch {
    referenceVideo.controls = true;
  }
});

document.querySelectorAll("video").forEach((video) => {
  video.addEventListener("play", () => {
    document.querySelectorAll("video").forEach((other) => {
      if (other !== video) other.pause();
    });
  });
});
