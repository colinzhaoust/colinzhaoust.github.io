const sections = [...document.querySelectorAll("main section[id]")];
const navLinks = [...document.querySelectorAll(".top-nav a")];

function updateActiveNav() {
  const header = document.querySelector(".site-header");
  const marker = (header?.getBoundingClientRect().bottom || 96) + 24;
  let activeId = sections[0]?.id;
  for (const section of sections) {
    if (section.getBoundingClientRect().top <= marker) activeId = section.id;
  }
  navLinks.forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === `#${activeId}`);
  });
}

updateActiveNav();
document.addEventListener("scroll", updateActiveNav, { passive: true });
window.addEventListener("resize", updateActiveNav);

const tabButtons = [...document.querySelectorAll(".tab-button")];
const tabPanels = [...document.querySelectorAll(".snippet-panel")];

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const tab = button.dataset.tab;
    tabButtons.forEach((item) => item.classList.toggle("active", item === button));
    tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${tab}`));
  });
});

const slidesTabButtons = [...document.querySelectorAll(".slides-tab-button")];
const slidesPanels = [...document.querySelectorAll(".slides-panel")];

slidesTabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const tab = button.dataset.slidesTab;
    slidesTabButtons.forEach((item) => item.classList.toggle("active", item === button));
    slidesPanels.forEach((panel) => {
      panel.classList.toggle("active", panel.id === `slides-tab-${tab}`);
    });
  });
});

document.querySelectorAll(".copy-button").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copy);
    if (!target) return;
    try {
      await navigator.clipboard.writeText(target.textContent.trim());
      button.textContent = "Copied";
      setTimeout(() => {
        button.textContent = "Copy";
      }, 1400);
    } catch {
      button.textContent = "Select text";
    }
  });
});

document.querySelectorAll("video").forEach((video) => {
  video.addEventListener("play", () => {
    document.querySelectorAll("video").forEach((other) => {
      if (other !== video) other.pause();
    });
  });
});
