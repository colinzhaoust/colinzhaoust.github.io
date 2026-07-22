(() => {
  "use strict";

  const state = { catalog: null, bundles: new Map(), activePaper: null, activeSection: null };
  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  const refs = (items = []) => `<span class="source-ref">${items.map(esc).join(" · ")}</span>`;
  const accent = (name) => ({ green: "var(--green)", violet: "var(--violet)", orange: "var(--orange)", cyan: "var(--cyan)", coral: "var(--coral)" }[name] || "var(--gray)");

  async function load() {
    const catalogResponse = await fetch("data/catalog.json");
    if (!catalogResponse.ok) throw new Error(`catalog ${catalogResponse.status}`);
    state.catalog = await catalogResponse.json();
    await Promise.all(state.catalog.papers.map(async (paper) => {
      const response = await fetch(paper.bundle);
      if (!response.ok) throw new Error(`${paper.paper_id} bundle ${response.status}`);
      state.bundles.set(paper.paper_id, await response.json());
    }));
    buildTabs();
    $("#status-strip span:last-child").textContent = `${state.bundles.size} reviewed runs · 3 JSON API stages · deterministic Manim · no coding agent`;
    route();
  }

  function buildTabs() {
    const tabs = [
      { id: "overview", label: "Overview" },
      ...state.catalog.papers.map((paper) => ({ id: paper.paper_id, label: paper.short_title.split("/")[0].trim() })),
      { id: "appendix", label: "Appendix" },
    ];
    $("#top-tabs").innerHTML = tabs.map((tab, index) => `<button type="button" role="tab" id="tab-${esc(tab.id)}" data-view="${esc(tab.id)}" aria-selected="false" tabindex="${index === 0 ? 0 : -1}">${esc(tab.label)}</button>`).join("");
    $("#top-tabs").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-view]");
      if (!button) return;
      const id = button.dataset.view;
      location.hash = id === "overview" || id === "appendix" ? id : `${id}/${state.bundles.get(id).source_packet.required_section_ids[0]}`;
    });
    $("#top-tabs").addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      const buttons = [...$("#top-tabs").querySelectorAll("button")];
      let next = buttons.indexOf(document.activeElement);
      if (event.key === "ArrowRight") next = (next + 1) % buttons.length;
      if (event.key === "ArrowLeft") next = (next - 1 + buttons.length) % buttons.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = buttons.length - 1;
      buttons.forEach((item, index) => item.tabIndex = index === next ? 0 : -1);
      buttons[next].focus();
      event.preventDefault();
    });
  }

  function setView(name) {
    $("#overview-view").hidden = name !== "overview";
    $("#paper-view").hidden = name !== "paper";
    $("#appendix-view").hidden = name !== "appendix";
    const selected = name === "paper" ? state.activePaper : name;
    $("#top-tabs").querySelectorAll("button").forEach((button) => {
      const active = button.dataset.view === selected;
      button.setAttribute("aria-selected", active ? "true" : "false");
      button.tabIndex = active ? 0 : -1;
    });
  }

  function route() {
    if (!state.catalog) return;
    const parts = location.hash.replace(/^#/, "").split("/").filter(Boolean);
    if (!parts.length || parts[0] === "overview") {
      renderOverview();
      setView("overview");
      return;
    }
    if (parts[0] === "appendix") {
      renderAppendix(parts[1], parts[2]);
      setView("appendix");
      return;
    }
    if (!state.bundles.has(parts[0])) {
      location.hash = "overview";
      return;
    }
    state.activePaper = parts[0];
    const bundle = state.bundles.get(state.activePaper);
    const validSections = bundle.source_packet.required_section_ids;
    state.activeSection = validSections.includes(parts[1]) ? parts[1] : validSections[0];
    renderPaper(bundle, state.activeSection);
    setView("paper");
    window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function renderOverview() {
    const runs = state.catalog.papers.map((paper) => `<div class="run-row"><strong>${esc(paper.short_title)}</strong><span>${esc(paper.central_question)}</span><button type="button" data-open-paper="${esc(paper.paper_id)}">Open run</button></div>`).join("");
    $("#overview-view").innerHTML = `
      <div class="overview-hero">
        <div><span class="eyebrow">Paper + repository → sourced explainer</span><h1>From source material to scientific scenes.</h1></div>
        <p>The API returns grounded JSON: the paper's motivation, terms, related work, formula/code mappings, and findings. A fixed renderer builds the website; a reusable Manim library renders selected state changes without asking a coding agent to write Python.</p>
      </div>
      <div class="pipeline-flow" aria-label="Pipeline stages">
        ${[
          ["01", "Ingest", "Paper PDF + revision-pinned repository"],
          ["02", "Ground", "Paper terms, questions, equations, code symbols, citations"],
          ["03", "Plan", "Concept graph and paper-native section transitions"],
          ["04", "Render scenes", "Typed HTML blocks + deterministic Manim templates"],
          ["05", "Validate", "Claims, links, hashes, media, and appendix provenance"],
        ].map(([n, title, body]) => `<article class="pipeline-step"><b>${n}</b><h2>${title}</h2><p>${body}</p></article>`).join("")}
      </div>
      <div class="legend" aria-label="Animation primitive provenance">
        <span style="--legend-color:var(--green)"><i></i>paper equation or exact value</span>
        <span style="--legend-color:var(--violet)"><i></i>confirmed repository mapping</span>
        <span style="--legend-color:var(--orange)"><i></i>new native Manim scene</span>
        <span style="--legend-color:var(--gray)"><i></i>conditional claim / open issue</span>
      </div>
      <div class="run-table"><span class="eyebrow">Generated outputs</span>${runs}</div>`;
    $("#overview-view").querySelectorAll("[data-open-paper]").forEach((button) => button.addEventListener("click", () => {
      const id = button.dataset.openPaper;
      location.hash = `${id}/${state.bundles.get(id).source_packet.required_section_ids[0]}`;
    }));
  }

  function renderPaper(bundle, sectionId) {
    const plan = bundle.lesson_plan;
    const sectionPlan = plan.sections.find((item) => item.id === sectionId);
    const content = bundle.section_content.sections[sectionId];
    $("#section-nav").innerHTML = plan.sections.map((item) => `<button type="button" data-section="${esc(item.id)}" aria-current="${item.id === sectionId ? "step" : "false"}">${esc(item.nav_label)}</button>`).join("");
    $("#section-nav").querySelectorAll("button").forEach((button) => button.addEventListener("click", () => location.hash = `${bundle.paper_id}/${button.dataset.section}`));
    const activeSectionButton = $("#section-nav").querySelector('[aria-current="step"]');
    requestAnimationFrame(() => activeSectionButton?.scrollIntoView({ block: "nearest", inline: "center" }));
    $("#lesson").innerHTML = `
      <header class="lesson-header">
        <span class="eyebrow">${esc(bundle.source_packet.short_title)} · ${esc(sectionPlan.nav_label)} · generated scene</span>
        <h1>${esc(sectionPlan.title)}</h1>
        <p class="promise">${esc(sectionPlan.summary)}</p>
        <div class="question-line"><b>QUESTION</b><span>${esc(sectionPlan.question)}</span></div>
      </header>
      <div class="blocks">${content.blocks.map((block) => renderBlock(block, bundle)).join("")}</div>`;
    bindLessonInteractions();
    renderSourcePanel(bundle, sectionPlan);
  }

  function renderBlock(block, bundle) {
    const renderer = blockRenderers[block.type];
    if (!renderer) return `<section class="block"><p>Unsupported block: ${esc(block.type)}</p></section>`;
    return renderer(block, bundle);
  }

  const blockRenderers = {
    paper_question: (b) => `<section class="block paper-question"><span class="eyebrow">${esc(b.label || "Paper question")}</span><h2>${esc(b.question)}</h2><p>${esc(b.context)}</p>${refs(b.source_refs)}</section>`,
    prose: (b) => `<section class="block prose">${b.eyebrow ? `<span class="eyebrow">${esc(b.eyebrow)}</span>` : ""}${b.heading ? `<h2>${esc(b.heading)}</h2>` : ""}${(b.paragraphs || []).map((p) => `<p>${esc(p)}</p>`).join("")}${refs(b.source_refs)}</section>`,
    comparison: (b) => `<section class="block"><div class="comparison">${b.columns.map((column) => `<article class="accent-${esc(column.accent)}"><span class="label">${esc(column.label)}</span><div class="question">${esc(column.question)}</div><div class="answer">${esc(column.answer)}</div></article>`).join("")}</div>${refs(b.source_refs)}</section>`,
    learner_check: (b) => `<details class="block learner-check"><summary><span class="eyebrow">Pause and predict</span><h3>${esc(b.prompt)}</h3><button type="button" tabindex="-1">Reveal answer</button></summary><p class="answer">${esc(b.answer)}</p></details>`,
    lineage: (b) => `<section class="block"><span class="eyebrow">Conceptual lineage</span><div class="lineage-track" style="--count:${b.nodes.length}">${b.nodes.map((node, index) => `<article class="lineage-node" style="--node-color:${index === b.nodes.length - 1 ? "var(--orange)" : index > b.nodes.length / 2 ? "var(--green)" : "var(--violet)"}"><strong>${esc(node.label)}</strong><span>${esc(node.note)}</span></article>`).join("")}</div>${refs(b.source_refs)}</section>`,
    related_reading: (b) => `<section class="block related-reading"><span class="eyebrow">Primary-source links</span><h2>${esc(b.title)}</h2><div class="reading-grid">${b.items.map((item) => `<a href="${esc(item.url)}" target="_blank" rel="noreferrer"><strong>${esc(item.title)}</strong><span>${esc(item.relation)}</span><i aria-hidden="true">↗</i></a>`).join("")}</div>${refs(b.source_refs)}</section>`,
    numeric_fixture: (b) => `<section class="block"><span class="eyebrow">${esc(b.claim_label)}</span><h2>${esc(b.title)}</h2><div class="formula-display">${esc(b.formula)}</div><div class="fixture-grid">${b.fixtures.map((fixture) => { const max = Math.max(...fixture.values); return `<article class="fixture"><h3>${esc(fixture.label)}</h3><div class="weight-bars">${fixture.values.map((value) => `<i style="height:${Math.max(2, value / max * 100)}%;--bar-color:${accent(fixture.accent)}" title="${esc(value)}"></i>`).join("")}</div><div class="ess-readout"><span>ρ = [${fixture.values.map(esc).join(", ")}]</span><b>ESS ${esc(fixture.ess)}</b></div></article>`; }).join("")}</div><p>${esc(b.note)}</p>${refs(b.source_refs)}</section>`,
    video: (b, bundle) => { const video = media(bundle, b.media_id); const poster = media(bundle, b.poster_id); const captions = media(bundle, b.captions_id); return `<section class="block"><span class="eyebrow">Manim where motion carries meaning</span><h2>${esc(b.title)}</h2><div class="video-frame"><video controls preload="metadata" poster="${esc(poster?.published_path || "")}"><source src="${esc(video?.published_path || "")}" type="video/mp4">${captions ? `<track default kind="captions" srclang="en" label="English" src="${esc(captions.published_path)}">` : ""}</video><div class="video-caption"><span>${esc(b.caption)}</span><div class="beat-list">${b.beats.map((beat) => `<span>${esc(beat)}</span>`).join("")}</div></div></div>${refs(b.source_refs)}</section>`; },
    formula_steps: (b) => `<section class="block"><span class="claim-label">${esc(b.claim_label)}</span><div class="formula-display">${esc(b.formula)}</div><div class="formula-steps">${b.steps.map((step, index) => `<article class="formula-step"><span class="step-number">0${index + 1} / ${esc(step.label)}</span><div class="step-expression">${esc(step.expression)}</div><p>${esc(step.meaning)}</p><span class="primitive-tag origin-${esc(step.primitive.origin)}">${esc(step.primitive.id)}</span></article>`).join("")}</div>${refs(b.source_refs)}</section>`,
    code: (b) => `<section class="block"><span class="eyebrow">Confirmed code mapping</span><h2>${esc(b.symbol)}</h2><div class="code-block"><div class="code-head"><span>${esc(b.path)}</span><span>${esc(b.code_source_id)}</span></div>${b.lines.map((line) => `<div class="code-line"><span class="line-no">${esc(line.number)}</span><code>${esc(line.code)}</code><span class="code-map">↳ ${esc(line.maps_to)}</span></div>`).join("")}</div>${refs(b.source_refs)}</section>`,
    bar_chart: (b) => { const min = b.axis_min || 0; const range = b.axis_max - min; return `<section class="block chart"><span class="claim-label">${esc(b.claim_label)}</span><h2>${esc(b.title)}</h2><div class="chart-bars">${b.groups.map((group) => `<div class="chart-row"><span>${esc(group.label)}</span><div class="chart-track" title="axis ${min} to ${b.axis_max}"><div class="chart-fill" style="--width:${Math.max(0, (group.value - min) / range * 100)}%;--bar-color:${accent(group.accent)}"></div></div><span class="chart-value">${esc(group.value)}${group.uncertainty ? ` ${esc(group.uncertainty)}` : ""}</span></div>`).join("")}</div><div class="chart-note">axis ${esc(min)}–${esc(b.axis_max)} ${esc(b.unit)} · ${esc(b.claim_label)}</div>${refs(b.source_refs)}</section>`; },
    reported_trends: (b) => `<section class="block"><span class="claim-label">${esc(b.claim_label)}</span><h2>${esc(b.title)}</h2><div class="trend-list">${b.items.map((item) => `<article class="trend-item"><strong>${esc(item.label)}</strong><p>${esc(item.finding)} <span class="source-ref">${esc(item.source_ref)}</span></p></article>`).join("")}</div></section>`,
    limitation: (b) => `<section class="block"><span class="eyebrow">Claim boundary</span><h2>What remains conditional</h2><div class="limitation-list">${b.items.map((item) => `<article class="limitation-item"><strong>${esc(item.label)}</strong><p>${esc(item.detail)}</p></article>`).join("")}</div>${refs(b.source_refs)}</section>`,
    rotation: (b) => `<section class="block"><span class="claim-label">${esc(b.claim_label)}</span><h2>${esc(b.title)}</h2><div class="rotation-stage"><svg viewBox="0 0 420 420" role="img" aria-label="Two vectors separated by a rotation angle"><line x1="40" y1="210" x2="380" y2="210" stroke="var(--line-strong)"/><line x1="210" y1="40" x2="210" y2="380" stroke="var(--line-strong)"/><circle cx="210" cy="210" r="150" fill="none" stroke="var(--line)"/><line x1="210" y1="210" x2="350" y2="180" stroke="var(--violet)" stroke-width="7"/><line x1="210" y1="210" x2="280" y2="80" stroke="var(--orange)" stroke-width="7"/><path d="M 280 195 A 74 74 0 0 0 250 145" fill="none" stroke="var(--orange)" stroke-width="3"/><circle cx="210" cy="210" r="6" fill="var(--ink)"/></svg><div class="rotation-copy"><span class="big-angle">${esc(b.angle_label)}</span><div class="formula-display">${esc(b.formula)}</div><p>${esc(b.note)}</p></div></div>${refs(b.source_refs)}</section>`,
  };

  function media(bundle, id) { return bundle.source_packet.media.find((item) => item.media_id === id); }

  function renderSourcePanel(bundle, sectionPlan) {
    const sourceLinks = bundle.source_packet.sources.map((source) => source.url ? `<a href="${esc(source.url)}" target="_blank" rel="noreferrer">${esc(source.revision)} · ${source.page_count} pages ↗</a>` : `<div class="source-meta">${esc(source.revision)} · ${source.page_count} pages · local input</div>`).join("");
    const codeLinks = bundle.source_packet.code_sources.map((source) => `<a href="${esc(source.repository)}/tree/${esc(source.revision)}" target="_blank" rel="noreferrer">repository @ ${esc(source.revision.slice(0, 8))} ↗</a>`).join("");
    const deep = sectionPlan.deep_links.map((id) => {
      const entry = bundle.section_content.appendix_entries.find((item) => item.id === id);
      return `<button type="button" data-appendix="${esc(id)}">${esc(entry?.title || id)} →</button>`;
    }).join("");
    const trace = bundle.generation.stage_traces.map((item) => `${item.stage}: ${item.response_sha256.slice(0, 8)}`).join("<br>");
    $("#source-panel").innerHTML = `<section><h2>Primary sources</h2>${sourceLinks}${codeLinks}<div class="source-meta">PDF SHA ${esc(bundle.source_packet.sources[0].sha256.slice(0, 16))}…<br>Manim: ${esc(bundle.source_packet.scene_renderer.engine)}<br>coding agent: not required</div></section><section><h2>Deep links</h2>${deep}</section><section><h2>API trace</h2><div class="source-meta">${trace}<br>mode: ${esc(bundle.generation.stage_traces[0].generation_mode)}</div></section>`;
    $("#source-panel").querySelectorAll("[data-appendix]").forEach((button) => button.addEventListener("click", () => location.hash = `appendix/${bundle.paper_id}/${button.dataset.appendix}`));
  }

  function bindLessonInteractions() {
    document.querySelectorAll(".learner-check").forEach((details) => {
      details.addEventListener("toggle", () => {
        const button = details.querySelector("button");
        if (button) button.textContent = details.open ? "Answer revealed" : "Reveal answer";
      });
    });
  }

  function renderAppendix(paperFilter, entryId) {
    const bundles = paperFilter && state.bundles.has(paperFilter) ? [state.bundles.get(paperFilter)] : [...state.bundles.values()];
    $("#appendix-view").innerHTML = `<header class="appendix-header"><span class="eyebrow">Derivations, provenance, and claim boundaries</span><h1>Appendix</h1><p>Paper and repository provenance, equation notes, formula-to-code mappings, results-reading guidance, and explicit limitations.</p></header>${bundles.map((bundle) => `<section><h2>${esc(bundle.source_packet.short_title)}</h2><div class="appendix-grid">${bundle.section_content.appendix_entries.map((entry) => `<article class="appendix-entry ${entry.id === entryId ? "highlight" : ""}" id="${esc(entry.id)}"><span class="eyebrow">${esc(bundle.paper_id)} / deep link</span><h2>${esc(entry.title)}</h2><p>${esc(entry.body)}</p>${refs(entry.source_refs)}</article>`).join("")}</div></section>`).join("")}`;
    if (entryId) requestAnimationFrame(() => document.getElementById(entryId)?.scrollIntoView({ block: "center" }));
  }

  $("#source-toggle").addEventListener("click", () => {
    const panel = $("#source-panel");
    const open = panel.classList.toggle("open");
    $("#source-toggle").setAttribute("aria-expanded", String(open));
  });
  window.addEventListener("hashchange", route);
  load().catch((error) => {
    $("#status-strip span:last-child").textContent = `Pipeline site failed to load: ${error.message}`;
    $("#status-strip").style.background = "var(--coral)";
  });
})();
