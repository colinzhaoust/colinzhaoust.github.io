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

function setupTabGroup(tablist) {
  const buttons = [...tablist.querySelectorAll('[role="tab"]')];
  const panels = buttons
    .map((button) => document.getElementById(button.getAttribute("aria-controls")))
    .filter(Boolean);

  function activateTab(activeButton, moveFocus = false) {
    const activePanelId = activeButton.getAttribute("aria-controls");

    buttons.forEach((button) => {
      const isActive = button === activeButton;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-selected", String(isActive));
      button.tabIndex = isActive ? 0 : -1;
    });

    panels.forEach((panel) => {
      const isActive = panel.id === activePanelId;
      panel.classList.toggle("active", isActive);
      panel.hidden = !isActive;
    });

    if (moveFocus) activeButton.focus();
  }

  buttons.forEach((button, index) => {
    button.addEventListener("click", () => activateTab(button));
    button.addEventListener("keydown", (event) => {
      let targetIndex;
      if (event.key === "ArrowRight") targetIndex = (index + 1) % buttons.length;
      if (event.key === "ArrowLeft") targetIndex = (index - 1 + buttons.length) % buttons.length;
      if (event.key === "Home") targetIndex = 0;
      if (event.key === "End") targetIndex = buttons.length - 1;
      if (targetIndex === undefined) return;

      event.preventDefault();
      activateTab(buttons[targetIndex], true);
    });
  });

  const initialButton = buttons.find((button) => button.getAttribute("aria-selected") === "true") || buttons[0];
  if (initialButton) activateTab(initialButton);
}

document.querySelectorAll('[role="tablist"]').forEach(setupTabGroup);

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
