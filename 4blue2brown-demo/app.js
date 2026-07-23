(() => {
  "use strict";

  const FORMULA_SECTION_ID = "formula";
  const CODE_SECTION_ID = "code-understanding";
  const state = { catalog: null, backtranslation: null, bundles: new Map(), activeRun: null, activePaper: null, activeSection: null, activeBacktranslationModel: null };
  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  const refs = (items = []) => `<span class="source-ref">${items.map(esc).join(" · ")}</span>`;
  const accent = (name) => ({ green: "var(--green)", violet: "var(--violet)", orange: "var(--orange)", cyan: "var(--cyan)", coral: "var(--coral)" }[name] || "var(--gray)");
  const bundleKey = (runId, paperId) => `${runId}:${paperId}`;
  const currentRun = () => state.catalog.runs.find((run) => run.run_id === state.activeRun);
  const currentBundle = (paperId = state.activePaper) => state.bundles.get(bundleKey(state.activeRun, paperId));
  const routeHash = (view, section) => {
    const suffix = section ? `/${section}` : "";
    return `run/${state.activeRun}/${view}${suffix}`;
  };
  const fmtTokens = (value) => value == null ? "not recorded" : value >= 1000000 ? `${(value / 1000000).toFixed(2)}M` : value >= 1000 ? `${(value / 1000).toFixed(1)}K` : String(value);
  const fmtDuration = (value) => !value ? "replay / 0 s" : value >= 60000 ? `${(value / 60000).toFixed(1)} min` : `${(value / 1000).toFixed(1)} s`;
  const fmtCost = (value) => value == null ? "not available" : `$${value < .01 ? value.toFixed(4) : value.toFixed(2)}`;
  const defaultStatusText = () => `${state.catalog.runs.length} rendered model run${state.catalog.runs.length === 1 ? "" : "s"} · ${state.catalog.papers.length} fixed papers · 3 JSON API stages · deterministic renderer`;

  async function load() {
    const [catalogResponse, backtranslationResponse] = await Promise.all([
      fetch("data/catalog.json", { cache: "no-store" }),
      fetch("data/backtranslation/catalog.json", { cache: "no-store" }),
    ]);
    if (!catalogResponse.ok) throw new Error(`catalog ${catalogResponse.status}`);
    if (!backtranslationResponse.ok) throw new Error(`backtranslation catalog ${backtranslationResponse.status}`);
    state.catalog = await catalogResponse.json();
    state.backtranslation = await backtranslationResponse.json();
    state.activeBacktranslationModel = state.backtranslation.models[0].candidate_id;
    state.activeRun = state.catalog.default_run;
    await Promise.all(state.catalog.runs.flatMap((run) => run.papers.map(async (paper) => {
      const response = await fetch(paper.bundle, { cache: "no-store" });
      if (!response.ok) throw new Error(`${run.run_id}/${paper.paper_id} bundle ${response.status}`);
      state.bundles.set(bundleKey(run.run_id, paper.paper_id), await response.json());
    })));
    buildModelSelector();
    buildTabs();
    $("#status-strip span:last-child").textContent = defaultStatusText();
    route();
  }

  function buildModelSelector() {
    const options = $("#model-run-options");
    const shortLabel = (run) => run.run_id === "reviewed-reference" ? "Demo" : run.label.includes("Gemini") ? "Gemini 3.1" : run.label.includes("GPT-5.5") ? "GPT-5.5" : run.label.split("·")[0].trim();
    options.innerHTML = state.catalog.runs.map((run) => `<button type="button" class="model-run-option" data-run-id="${esc(run.run_id)}" aria-pressed="${run.run_id === state.activeRun ? "true" : "false"}" title="${esc(run.label)} · ${esc(run.models.join(" + "))}">${esc(shortLabel(run))}</button>`).join("");
    options.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-run-id]");
      if (!button || button.dataset.runId === state.activeRun) return;
      state.activeRun = button.dataset.runId;
      const view = state.activePaper && !$("#paper-view").hidden ? state.activePaper : !$("#backtranslation-view").hidden ? "backtranslation" : !$("#appendix-view").hidden ? "appendix" : "overview";
      const section = view === state.activePaper ? state.activeSection : undefined;
      location.hash = routeHash(view, section);
    });
  }

  function buildTabs() {
    const tabs = [
      { id: "overview", label: "Overview" },
      ...state.catalog.papers.map((paper) => ({ id: paper.paper_id, label: paper.short_title.split("/")[0].trim() })),
      { id: "backtranslation", label: "Backtranslation" },
      { id: "appendix", label: "Appendix" },
    ];
    $("#top-tabs").innerHTML = tabs.map((tab, index) => `<button type="button" role="tab" id="tab-${esc(tab.id)}" data-view="${esc(tab.id)}" aria-selected="false" tabindex="${index === 0 ? 0 : -1}">${esc(tab.label)}</button>`).join("");
    $("#top-tabs").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-view]");
      if (!button) return;
      const id = button.dataset.view;
      if (id === "overview" || id === "appendix") {
        location.hash = routeHash(id);
      } else if (id === "backtranslation") {
        location.hash = routeHash(id, state.activeBacktranslationModel);
      } else {
        location.hash = routeHash(id, currentBundle(id).lesson_plan.sections[0].id);
      }
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
    $("#backtranslation-view").hidden = name !== "backtranslation";
    $("#paper-view").hidden = name !== "paper";
    $("#appendix-view").hidden = name !== "appendix";
    document.body.classList.toggle("is-backtranslation", name === "backtranslation");
    $("#status-strip span:last-child").textContent = name === "backtranslation"
      ? `${state.backtranslation.execution_summary.cases} human references · ${state.backtranslation.models.length} model candidates · ${state.backtranslation.execution_summary.completed_rounds} completed reconstruction rounds · evidence, not mockups`
      : defaultStatusText();
    const selected = name === "paper" ? state.activePaper : name;
    $("#top-tabs").querySelectorAll("button").forEach((button) => {
      const active = button.dataset.view === selected;
      button.setAttribute("aria-selected", active ? "true" : "false");
      button.tabIndex = active ? 0 : -1;
    });
  }

  function route() {
    if (!state.catalog) return;
    let parts = location.hash.replace(/^#/, "").split("/").filter(Boolean);
    if (parts[0] === "run") {
      if (!state.catalog.runs.some((run) => run.run_id === parts[1])) {
        location.hash = routeHash("overview");
        return;
      }
      state.activeRun = parts[1];
      parts = parts.slice(2);
    }
    $("#model-run-options").querySelectorAll("button[data-run-id]").forEach((button) => button.setAttribute("aria-pressed", button.dataset.runId === state.activeRun ? "true" : "false"));
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
    if (parts[0] === "backtranslation") {
      const requested = parts[1];
      state.activeBacktranslationModel = state.backtranslation.models.some((model) => model.candidate_id === requested) ? requested : state.backtranslation.models[0].candidate_id;
      renderBacktranslation();
      setView("backtranslation");
      window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
      return;
    }
    if (!currentBundle(parts[0])) {
      location.hash = routeHash("overview");
      return;
    }
    state.activePaper = parts[0];
    const bundle = currentBundle();
    const validSections = [...bundle.lesson_plan.sections.map((section) => section.id), FORMULA_SECTION_ID, CODE_SECTION_ID];
    state.activeSection = validSections.includes(parts[1]) ? parts[1] : validSections[0];
    renderPaper(bundle, state.activeSection);
    setView("paper");
    window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function renderOverview() {
    const run = currentRun();
    const liveRuns = state.catalog.runs.filter((item) => item.generation_modes.includes("live"));
    const isLive = run.generation_modes.includes("live");
    const comparisonLabel = (item) => item.run_id === "reviewed-reference" ? "Demo" : item.label.includes("Gemini") ? "Gemini 3.1" : item.label.includes("GPT-5.5") ? "GPT-5.5" : item.label.split("·")[0].trim();
    const runLedger = state.catalog.runs.map((item) => `<button type="button" data-overview-run="${esc(item.run_id)}" aria-current="${item.run_id === state.activeRun ? "true" : "false"}"><strong>${esc(comparisonLabel(item))}</strong><span><b>${fmtTokens(item.trace_summary?.total_tokens)}</b><small>tokens</small></span><span><b>${fmtCost(item.trace_summary?.estimated_cost_usd)}</b><small>est. cost</small></span></button>`).join("");
    const outputs = state.catalog.papers.map((paper) => {
      const runPaper = run.papers.find((item) => item.paper_id === paper.paper_id);
      const metrics = runPaper?.trace_summary || {};
      return `<div class="run-row"><strong>${esc(paper.short_title)}</strong><span>${esc(paper.central_question)}</span><div class="paper-run-metrics"><b>${esc(runPaper?.section_count || 0)} sections</b><b>${esc(runPaper?.block_count || 0)} blocks</b><b>${esc(runPaper?.animation_count || 0)} animations</b><b>${fmtTokens(metrics.total_tokens)} tokens</b><b>${fmtCost(metrics.estimated_cost_usd)}</b><b>${fmtDuration(metrics.duration_ms)}</b></div><button type="button" data-open-paper="${esc(paper.paper_id)}">Open run</button></div>`;
    }).join("");
    const protocol = state.catalog.comparison_protocol;
    const failedCandidates = (state.catalog.candidate_runs || []).filter((candidate) => candidate.status === "generation_failed");
    const candidates = (state.catalog.candidate_runs || []).map((candidate) => `<article><div><span class="candidate-status">${esc(candidate.status.replaceAll("_", " "))}</span><h3>${esc(candidate.label)}</h3></div><p class="model-summary">${esc(candidate.model_summary)}</p><dl><div><dt>Provider</dt><dd>${esc(candidate.provider)}</dd></div><div><dt>Model ID</dt><dd>${esc(candidate.model_id)}</dd></div><div><dt>Endpoint</dt><dd>${esc(candidate.endpoint)}</dd></div></dl><p>${esc(candidate.note)}</p>${candidate.documentation_url && candidate.documentation_url !== "#" ? `<a href="${esc(candidate.documentation_url)}" target="_blank" rel="noreferrer">Endpoint documentation ↗</a>` : ""}</article>`).join("");
    $("#overview-view").innerHTML = `
      <div class="overview-hero">
        <div><span class="eyebrow">Paper + repository → sourced explainer</span><h1>From source material to scientific scenes.</h1></div>
        <div class="overview-intro"><p>The API returns grounded JSON: the paper's motivation, terms, related work, formula/code mappings, and findings. A fixed renderer builds the website; a reusable Manim library renders selected state changes without asking a coding agent to write Python.</p><div class="overview-run-ledger" aria-label="Run token and cost comparison"><div class="overview-run-head"><span>Run</span><span>Tokens</span><span>Cost</span></div>${runLedger}<p>Totals cover FeynRL + RoPE. Live costs use the frozen provider rate card; Demo is a reviewed replay with no recorded API usage.</p></div></div>
      </div>
      <section class="quality-audit" aria-labelledby="quality-audit-title">
        <div><span class="eyebrow">Quality provenance</span><h2 id="quality-audit-title">${isLive ? "This is an untouched live-model lesson inside a fixed harness." : "The reviewed run is the teaching target; live runs remain visibly separate."}</h2></div>
        <dl><div><dt>Selected narrative</dt><dd>${isLive ? "Generated by the selected model API; no manual editing after generation" : "Human/Codex-reviewed from paper, code, and iterative reader feedback"}</dd></div><div><dt>Live model API</dt><dd>${liveRuns.length ? `${liveRuns.length} complete runs, each covering both papers under the same contract` : "No complete live run is published yet"}</dd></div><div><dt>Harness</dt><dd>Validation, deterministic maps, registered Manim rendering, traces, and publication</dd></div></dl>
        <p>${isLive ? "Judge its section split, narrative continuity, evidence use, and animation decisions against the reviewed reference—not just whether its JSON passed." : "Use the model switcher to compare section boundaries, block balance, and Manim choices without blending authorship."}</p>
      </section>
      <section class="responsibility-board" aria-labelledby="responsibility-title">
        <div class="responsibility-head"><span class="eyebrow">Execution boundary</span><h2 id="responsibility-title">What the model decides—and what it never touches.</h2><p>A model comparison is meaningful only when the harness stays fixed. The API is a constrained reasoning component; it is not the website renderer or the animation coder.</p></div>
        <div class="responsibility-columns">
          <article class="model-duty"><span>MODEL API</span><h3>Produce grounded, typed decisions</h3><ul><li>Extract paper-native intent and concept relations from the frozen packet.</li><li>Propose the lesson path and transitions between related work, formulas, code, and findings.</li><li>Fill validated JSON blocks with source locators and explicit claim types.</li></ul><code>JSON only · no Python · no HTML · no shell</code></article>
          <article class="harness-duty"><span>HARNESS</span><h3>Hold the experiment and rendering fixed</h3><ul><li>Freeze PDF, repository revision, source packet, prompts, and schemas.</li><li>Reject invalid claims, unknown media, missing equations, or dangling links.</li><li>Compile Formula IR, select registered Manim functions, render HTML/video, hash, and publish.</li></ul><code>deterministic renderer · fail closed · replayable</code></article>
        </div>
      </section>
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
      <section class="run-provenance">
        <div><span class="eyebrow">Selected frozen run</span><h2>${esc(run.label)}</h2><p>${esc(run.description)}</p></div>
        <dl><div><dt>Provider</dt><dd>${esc(run.providers.join(" + "))}</dd></div><div><dt>Model</dt><dd>${esc(run.models.join(" + "))}</dd></div><div><dt>What it is</dt><dd>${esc(run.model_summary)}</dd></div><div><dt>Endpoint</dt><dd>${esc(run.endpoint)}</dd></div><div><dt>Tokens</dt><dd>${fmtTokens(run.trace_summary?.total_tokens)}</dd></div><div><dt>API time</dt><dd>${fmtDuration(run.trace_summary?.duration_ms)}</dd></div><div><dt>Estimated cost</dt><dd>${fmtCost(run.trace_summary?.estimated_cost_usd)}</dd></div><div><dt>API calls</dt><dd>${esc(run.trace_summary?.api_call_count ?? "not recorded")}</dd></div><div><dt>Semantic repairs</dt><dd>${esc(run.trace_summary?.repair_count ?? "not recorded")}</dd></div><div><dt>Harness compile ops</dt><dd>${esc(run.trace_summary?.structural_compilation_count ?? 0)}</dd></div><div><dt>Corrective normalizations</dt><dd>${esc(run.trace_summary?.corrective_normalization_count ?? 0)}</dd></div><div><dt>Status</dt><dd>${esc(run.status)}</dd></div></dl>
      </section>
      <section class="comparison-contract"><div><span class="eyebrow">Cross-model contract</span><h2>Same evidence and renderer; different planning JSON.</h2></div><div><b>FIXED</b><p>${protocol.fixed.map(esc).join(" · ")}</p></div><div><b>VARIED</b><p>${protocol.varied.map(esc).join(" · ")}</p></div><small>${esc(protocol.rule)}</small></section>
      ${candidates ? `<section class="candidate-matrix"><div class="candidate-head"><span class="eyebrow">Requested comparison matrix</span><h2>${failedCandidates.length ? "Failed runs remain visible, but cannot enter the selector." : "Queued, not fabricated."}</h2><p>A model appears in the top-right selector only after both paper bundles are generated, validated, frozen, and hashed. ${failedCandidates.length ? "The failure note below is the harness boundary it did not cross." : ""}</p></div><div class="candidate-grid">${candidates}</div></section>` : ""}
      <div class="run-table"><span class="eyebrow">Generated outputs in this run</span>${outputs}</div>`;
    $("#overview-view").querySelectorAll("[data-open-paper]").forEach((button) => button.addEventListener("click", () => {
      const id = button.dataset.openPaper;
      location.hash = routeHash(id, currentBundle(id).lesson_plan.sections[0].id);
    }));
    $("#overview-view").querySelectorAll("[data-overview-run]").forEach((button) => button.addEventListener("click", () => {
      if (button.dataset.overviewRun === state.activeRun) return;
      state.activeRun = button.dataset.overviewRun;
      location.hash = routeHash("overview");
    }));
  }

  function renderPaper(bundle, sectionId) {
    const plan = bundle.lesson_plan;
    const navItems = [
      ...plan.sections,
      { id: FORMULA_SECTION_ID, nav_label: "Formula", title: "Formula → Manim map" },
      { id: CODE_SECTION_ID, nav_label: "Code", title: "Code understanding" },
    ];
    $("#section-nav").innerHTML = navItems.map((item) => `<button type="button" data-section="${esc(item.id)}" aria-current="${item.id === sectionId ? "step" : "false"}">${esc(item.nav_label)}</button>`).join("");
    $("#section-nav").querySelectorAll("button").forEach((button) => button.addEventListener("click", () => location.hash = routeHash(bundle.paper_id, button.dataset.section)));
    const activeSectionButton = $("#section-nav").querySelector('[aria-current="step"]');
    requestAnimationFrame(() => activeSectionButton?.scrollIntoView({ block: "nearest", inline: "center" }));
    if (sectionId === FORMULA_SECTION_ID) {
      renderFormulaMap(bundle);
      return;
    }
    if (sectionId === CODE_SECTION_ID) {
      renderCodeMap(bundle);
      return;
    }
    const sectionPlan = plan.sections.find((item) => item.id === sectionId);
    const content = bundle.section_content.sections[sectionId];
    const sectionIndex = plan.sections.findIndex((item) => item.id === sectionId);
    const nextSection = plan.sections[sectionIndex + 1];
    const modeDefinitions = [
      { label: "Read", types: ["paper_question", "prose", "comparison", "lineage", "equation_thread", "formula_steps", "numeric_fixture", "rotation"] },
      { label: "Watch", types: ["video", "micro_video"] },
      { label: "Verify", types: ["code", "result_story", "line_chart", "bar_chart", "reported_trends", "related_reading"] },
      { label: "Check", types: ["learner_check", "limitation"] },
    ];
    const blockTypes = new Set(content.blocks.map((block) => block.type));
    const learningModes = modeDefinitions.filter((mode) => mode.types.some((type) => blockTypes.has(type)));
    $("#lesson").innerHTML = `
      <header class="lesson-header" data-section-role="${esc(sectionPlan.role)}">
        <span class="eyebrow">${esc(bundle.source_packet.short_title)} · ${String(sectionIndex + 1).padStart(2, "0")} ${esc(sectionPlan.nav_label)} · ${esc(sectionPlan.role)}</span>
        <h1>${esc(sectionPlan.title)}</h1>
        <p class="promise">${esc(sectionPlan.summary)}</p>
        <div class="intent-line"><b>WHY NOW</b><span>${esc(sectionPlan.intent)}</span></div>
        <div class="question-line"><b>QUESTION</b><span>${esc(sectionPlan.question)}</span></div>
        <div class="learning-contract"><div><b>LEAVE ABLE TO</b><span>${esc(sectionPlan.learning_goal)}</span></div><div><b>WATCH FOR</b><span>${esc(sectionPlan.misconception)}</span></div><div class="learning-modes" aria-label="Learning media sequence">${learningModes.map((mode, index) => `<span><i>${index + 1}</i>${esc(mode.label)}</span>`).join("")}</div></div>
      </header>
      <div class="blocks">${content.blocks.map((block) => renderBlock(block, bundle)).join("")}</div>
      <footer class="section-outcome"><div><span class="eyebrow">Section takeaway</span><strong>${esc(sectionPlan.learning_goal)}</strong></div>${nextSection ? `<button type="button" data-next-section="${esc(nextSection.id)}"><small>Next · ${esc(nextSection.nav_label)}</small><span>${esc(nextSection.intent)}</span></button>` : `<button type="button" data-next-section="${FORMULA_SECTION_ID}"><small>Next · Formula</small><span>Audit the complete equation thread and inspect its registered animation mappings.</span></button>`}</footer>`;
    bindLessonInteractions();
    $("#lesson [data-next-section]")?.addEventListener("click", (event) => location.hash = routeHash(bundle.paper_id, event.currentTarget.dataset.nextSection));
    renderSourcePanel(bundle, sectionPlan);
  }

  function renderFormulaMap(bundle) {
    const map = bundle.formula_map;
    const formulaLookup = new Map(map.formulas.map((item) => [item.formula_id, item]));
    const edgeStateLabel = { implemented: "implemented", candidate: "candidate mapping", unresolved: "unresolved" };
    const showcases = (bundle.source_packet.formula_showcase || []).map((item, index) => {
      const video = media(bundle, item.media_id);
      const poster = media(bundle, item.poster_id);
      const captions = media(bundle, item.captions_id);
      return `<article><div><span class="formula-index">M${String(index + 1).padStart(2, "0")}</span><h3>${esc(item.title)}</h3><p>${esc(item.focus)}</p><span class="source-ref">${item.source_refs.map(esc).join(" · ")}</span></div><video controls preload="metadata" playsinline poster="${esc(poster?.published_path || "")}"><source src="${esc(video?.published_path || "")}" type="video/mp4">${captions ? `<track default kind="captions" srclang="en" label="English" src="${esc(captions.published_path)}">` : ""}</video></article>`;
    }).join("");
    $("#lesson").innerHTML = `
      <header class="lesson-header formula-header">
        <span class="eyebrow">${esc(bundle.source_packet.short_title)} · ${String(bundle.lesson_plan.sections.length + 1).padStart(2, "0")} Formula · deterministic capability view</span>
        <h1>Formula → Manim map</h1>
        <p class="promise">Formula IR is on the left; callable Manim functions are on the right. An edge means the registry can express that operation—not that every compatible animation is equally explanatory.</p>
        <div class="question-line"><b>QUESTION</b><span>Which mappings are implemented, merely compatible, or still unresolved?</span></div>
      </header>
      <div class="blocks formula-blocks">
        <section class="block equation-audit">
          <span class="eyebrow">Equation coverage contract</span>
          <h2>What is animated, explained, or folded</h2>
          <p class="mapping-help">This inventory is produced during source grounding, before scene selection. A formula cannot disappear merely because no animation was authored for it.</p>
          <div class="equation-audit-list">${bundle.source_packet.equation_coverage.map((item) => `<article class="coverage-${esc(item.coverage)}"><div><span class="coverage-state">${esc(item.coverage)}</span><strong>${item.equation_ids.map(esc).join(" · ")}</strong><small>${esc(item.role)} · ${esc(item.thread_stage)}</small></div><p>${esc(item.intent)}</p>${item.fold_reason ? `<p class="fold-reason">Folded: ${esc(item.fold_reason)}</p>` : ""}</article>`).join("")}</div>
        </section>
        <section class="block formula-showcase"><span class="eyebrow">Formula motion library · selected paper thread</span><h2>One conceptual state change per clip</h2><p class="mapping-help">These are not decorative equation reveals. Each clip holds the surrounding question fixed and animates the exact operation that changes.</p><div>${showcases}</div></section>
        <section class="block formula-inventory">
          <span class="eyebrow">Fully parsed Formula IR subset</span>
          <div class="formula-inventory-grid">${map.formulas.map((formula, index) => `<article>
            <span class="formula-index">F${String(index + 1).padStart(2, "0")}</span>
            <h2>${esc(formula.title)}</h2>
            <div class="formula-display">${esc(formula.plain_text)}</div>
            <a href="${esc(formula.source_anchor.source_url)}" target="_blank" rel="noreferrer">${esc(formula.source_anchor.locator)} ↗</a>
          </article>`).join("")}</div>
        </section>
        <section class="block mapping-lab">
          <div class="mapping-intro"><div><span class="eyebrow">Bipartite capability graph</span><h2>Fragments and operations ↔ render functions</h2></div><div class="mapping-legend">${Object.entries(edgeStateLabel).map(([stateName, label]) => `<span class="edge-${stateName}"><i></i>${esc(label)}</span>`).join("")}</div></div>
          <p class="mapping-help">Focus either side to isolate its N-to-N mappings. Coverage nodes account for the complete equation audit; operation nodes add compiler-level detail where Formula IR exists. Solid edges are callable implementations; dashed edges await scene-level selection.</p>
          <div class="formula-bipartite" id="formula-bipartite">
            <svg class="mapping-lines" id="mapping-lines" aria-hidden="true"></svg>
            <div class="mapping-column formula-side"><h3>Formula layer</h3>${map.formula_nodes.map((node) => {
              const formula = formulaLookup.get(node.formula_id);
              return `<button type="button" class="mapping-node level-${esc(node.level)}" data-map-node="${esc(node.node_id)}"><span>${esc(node.level)}</span><strong>${esc(node.label)}</strong><small>${esc(node.expression)}</small><i>${esc(formula?.title || "")}</i></button>`;
            }).join("")}</div>
            <div class="mapping-column manim-side"><h3>Manim layer</h3>${map.manim_nodes.map((node) => `<button type="button" class="mapping-node origin-${esc(node.origin)}" data-map-node="${esc(node.primitive_id)}"><span>${esc(node.origin_label)}</span><strong>${esc(node.label)}</strong><small>${esc(node.primitive_id)}</small><i>${esc(node.status)}</i></button>`).join("")}</div>
          </div>
          <div class="mapping-evidence" id="mapping-evidence" aria-live="polite"><span class="eyebrow">Mapping evidence</span><p>Focus a formula fragment or Manim function to inspect why the edge exists.</p></div>
        </section>
        <section class="block prose"><span class="eyebrow">How to read this</span><h2>The graph is also a pipeline test surface.</h2><p>A missing edge means the formula compiler has no registered visual operation. A candidate edge means the API signatures are compatible, but the scene planner still needs evidence that the mapping teaches the intended concept. Implemented edges resolve to real source symbols; no runtime coding agent is needed.</p><span class="source-ref">${esc(map.registry_ref)} · Manim ${map.manim_compatibility.validated_render_versions.map(esc).join(" / ")}</span></section>
      </div>`;
    bindFormulaMap(map);
    renderSourcePanel(bundle, {
      deep_links: [],
      id: FORMULA_SECTION_ID,
      title: "Formula → Manim map",
    });
  }

  function bindFormulaMap(map) {
    const graph = $("#formula-bipartite");
    const svg = $("#mapping-lines");
    if (!graph || !svg) return;
    const nodeElements = [...graph.querySelectorAll("[data-map-node]")];

    const draw = () => {
      const graphRect = graph.getBoundingClientRect();
      svg.setAttribute("viewBox", `0 0 ${graphRect.width} ${graphRect.height}`);
      svg.innerHTML = map.edges.map((edge) => {
        const from = nodeElements.find((item) => item.dataset.mapNode === edge.source)?.getBoundingClientRect();
        const to = nodeElements.find((item) => item.dataset.mapNode === edge.target)?.getBoundingClientRect();
        if (!from || !to) return "";
        const x1 = from.right - graphRect.left;
        const y1 = from.top + from.height / 2 - graphRect.top;
        const x2 = to.left - graphRect.left;
        const y2 = to.top + to.height / 2 - graphRect.top;
        const bend = Math.max(28, (x2 - x1) * .42);
        return `<path data-map-edge="${esc(edge.edge_id)}" data-source="${esc(edge.source)}" data-target="${esc(edge.target)}" class="edge-${esc(edge.state)}" d="M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}"/>`;
      }).join("");
    };

    const inspect = (nodeId) => {
      const connected = map.edges.filter((edge) => edge.source === nodeId || edge.target === nodeId);
      nodeElements.forEach((item) => item.classList.toggle("is-related", connected.some((edge) => edge.source === item.dataset.mapNode || edge.target === item.dataset.mapNode)));
      svg.querySelectorAll("[data-map-edge]").forEach((path) => path.classList.toggle("is-active", connected.some((edge) => edge.edge_id === path.dataset.mapEdge)));
      const evidence = $("#mapping-evidence");
      evidence.innerHTML = `<span class="eyebrow">${connected.length} connected mapping${connected.length === 1 ? "" : "s"}</span>${connected.map((edge) => `<article><b>${esc(edge.operation_type.replaceAll("_", " "))}</b><span class="edge-pill edge-${esc(edge.state)}">${esc(edge.state)}</span><p>${esc(edge.reason)}</p><small>${edge.evidence_refs.map(esc).join(" · ")}</small></article>`).join("") || "<p>No registered mapping.</p>"}`;
    };

    nodeElements.forEach((node) => {
      node.addEventListener("mouseenter", () => inspect(node.dataset.mapNode));
      node.addEventListener("focus", () => inspect(node.dataset.mapNode));
      node.addEventListener("click", () => inspect(node.dataset.mapNode));
    });
    requestAnimationFrame(draw);
    const observer = new ResizeObserver(draw);
    observer.observe(graph);
  }

  function renderCodeMap(bundle) {
    const map = bundle.code_map;
    const codeById = new Map(map.code_nodes.map((node) => [node.node_id, node]));
    const edgesByFormula = new Map(map.formula_nodes.map((node) => [node.node_id, map.formula_code_edges.filter((edge) => edge.source === node.node_id)]));
    const lifecycleEdges = new Map(map.dag_nodes.map((node) => [node.id, map.dag_edges.filter((edge) => edge.source === node.id)]));
    const repository = map.repository_sources[0];
    $("#lesson").innerHTML = `<header class="lesson-header code-header"><span class="eyebrow">${esc(bundle.source_packet.short_title)} · original repository @ ${esc(repository.revision.slice(0, 8))}</span><h1>Follow one example through the repo.</h1><p class="promise">The formula map points to upstream files and exact line ranges. The lifecycle below follows one named input through repository functions, stored artifacts, the method-specific computation, and the final metric or next policy version.</p><div class="intent-line"><b>EXAMPLE</b><span>${esc(map.example.label)}: ${esc(map.example.input)} ${esc(map.example.output)}</span></div></header>
      <div class="blocks code-understanding-blocks">
        <section class="block mapping-lab"><span class="eyebrow">Paper formula ↔ upstream repository</span><h2>One equation can act through several original code sites.</h2><p class="mapping-help">Every path below is relative to <a href="${esc(repository.repository)}/tree/${esc(repository.revision)}" target="_blank" rel="noreferrer">the pinned upstream checkout ↗</a>, not this explainer pipeline.</p><div class="code-bipartite"><div class="code-map-column"><h3>Paper formulas</h3>${map.formula_nodes.map((formula) => `<article class="code-formula-node"><strong>${esc(formula.label)}</strong><code>${esc(formula.expression)}</code>${formula.source_url ? `<a href="${esc(formula.source_url)}" target="_blank" rel="noreferrer">paper source ↗</a>` : ""}</article>`).join("")}</div><div class="code-edge-column">${map.formula_nodes.flatMap((formula) => (edgesByFormula.get(formula.node_id) || []).map((edge) => { const target = codeById.get(edge.target); return `<article><span>${esc(formula.label)}</span><i>→</i><strong>${esc(target.symbol)}</strong><p>${esc(edge.role)}</p><small>${edge.evidence_refs.map(esc).join(" · ")}</small></article>`; })).join("")}</div><div class="code-map-column"><h3>Confirmed upstream sites</h3>${map.code_nodes.map((node) => `<article class="code-symbol-node"><strong>${esc(node.symbol)}</strong><a href="${esc(node.source_url)}" target="_blank" rel="noreferrer"><code>${esc(node.path)}:${node.line_start}–${node.line_end}</code> ↗</a><p>${esc(node.role)}</p></article>`).join("")}</div></div></section>
        <section class="block execution-lifecycle"><span class="eyebrow">Concrete execution lifecycle</span><h2>${esc(map.example.label)}</h2><div class="lifecycle-flow">${map.dag_nodes.map((node, index) => { const outgoing = lifecycleEdges.get(node.id) || []; const handoff = outgoing.find((edge) => edge.edge_kind !== "loop"); return `<article class="lifecycle-node kind-${esc(node.kind)}"><div class="lifecycle-index">${String(index + 1).padStart(2, "0")}<span>${esc(node.stage)}</span></div><div><strong>${esc(node.label)}</strong><p>${esc(node.detail)}</p><code>${esc(node.artifact)}</code><a href="${esc(node.source_url)}" target="_blank" rel="noreferrer">${esc(node.path)}:${node.line_start}–${node.line_end} ↗</a></div>${handoff ? `<small>next · ${esc(handoff.label)} ↓</small>` : ""}</article>`; }).join("")}</div><div class="lifecycle-loop">↺ ${map.dag_edges.filter((edge) => edge.edge_kind === "loop").map((edge) => esc(edge.label)).join(" · ")}</div></section>
        <section class="block experiment-pipeline"><span class="eyebrow">Experiment pipeline</span><h2>What changes, what runs, and what gets measured.</h2><div>${map.experiment_pipeline.map((step, index) => `<article><b>${String(index + 1).padStart(2, "0")}</b><strong>${esc(step.label)}</strong><p>${esc(step.detail)}</p><small>${step.source_refs.map(esc).join(" · ")}</small></article>`).join("")}</div></section>
      </div>`;
    renderSourcePanel(bundle, { deep_links: [], id: CODE_SECTION_ID, title: "Code understanding" });
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
    equation_thread: (b) => `<section class="block equation-thread"><span class="eyebrow">Paper → equation → limitation → next move</span><h2>${esc(b.title)}</h2><div class="equation-thread-list">${b.stages.map((stage, index) => `<article><span class="thread-index">${String(index + 1).padStart(2, "0")}</span><div>${stage.paper ? `<div class="thread-paper"><b>${esc(stage.paper)}</b><span>${esc(stage.year)}</span>${stage.source_url ? `<a href="${esc(stage.source_url)}" target="_blank" rel="noreferrer">primary source ↗</a>` : ""}</div>` : ""}<strong>${esc(stage.equation)}</strong><code>${esc(stage.formula)}</code><p>${esc(stage.intent)}</p><small>${esc(stage.change)}</small></div></article>`).join("")}</div><details class="folded-equations"><summary>${b.folded.length} folded equation famil${b.folded.length === 1 ? "y" : "ies"}</summary>${b.folded.map((item) => `<p><strong>${esc(item.equations)}</strong> ${esc(item.reason)}</p>`).join("")}</details>${refs(b.source_refs)}</section>`,
    result_story: (b) => `<section class="block result-story"><div class="result-question"><span class="eyebrow">Experimental question</span><h2>${esc(b.question)}</h2></div><dl><div><dt>Setting / factor</dt><dd>${esc(b.setting)}</dd></div><div><dt>Metric</dt><dd>${esc(b.metric)}</dd></div><div><dt>Evidence</dt><dd><span class="claim-label">${esc(b.evidence_kind.replaceAll("_", " "))}</span>${esc(b.evidence)}</dd></div><div><dt>Takeaway</dt><dd>${esc(b.takeaway)}</dd></div></dl>${refs(b.source_refs)}</section>`,
    related_reading: (b) => `<section class="block related-reading"><span class="eyebrow">Primary-source links</span><h2>${esc(b.title)}</h2><div class="reading-grid">${b.items.map((item) => `<a href="${esc(item.url)}" target="_blank" rel="noreferrer"><strong>${esc(item.title)}</strong><span>${esc(item.relation)}</span><i aria-hidden="true">↗</i></a>`).join("")}</div>${refs(b.source_refs)}</section>`,
    numeric_fixture: (b) => `<section class="block"><span class="eyebrow">${esc(b.claim_label)}</span><h2>${esc(b.title)}</h2><div class="formula-display">${esc(b.formula)}</div><div class="fixture-grid">${b.fixtures.map((fixture) => { const max = Math.max(...fixture.values); return `<article class="fixture"><h3>${esc(fixture.label)}</h3><div class="weight-bars">${fixture.values.map((value) => `<i style="height:${Math.max(2, value / max * 100)}%;--bar-color:${accent(fixture.accent)}" title="${esc(value)}"></i>`).join("")}</div><div class="ess-readout"><span>ρ = [${fixture.values.map(esc).join(", ")}]</span><b>ESS ${esc(fixture.ess)}</b></div></article>`; }).join("")}</div><p>${esc(b.note)}</p>${refs(b.source_refs)}</section>`,
    video: (b, bundle) => { const video = media(bundle, b.media_id); const poster = media(bundle, b.poster_id); const captions = media(bundle, b.captions_id); return `<section class="block"><span class="eyebrow">Manim where motion carries meaning</span><h2>${esc(b.title)}</h2><div class="video-frame"><video controls preload="metadata" poster="${esc(poster?.published_path || "")}"><source src="${esc(video?.published_path || "")}" type="video/mp4">${captions ? `<track default kind="captions" srclang="en" label="English" src="${esc(captions.published_path)}">` : ""}</video><div class="video-caption"><span>${esc(b.caption)}</span><div class="beat-list">${b.beats.map((beat) => `<span>${esc(beat)}</span>`).join("")}</div></div></div>${refs(b.source_refs)}</section>`; },
    micro_video: (b, bundle) => { const video = media(bundle, b.media_id); const poster = media(bundle, b.poster_id); const captions = media(bundle, b.captions_id); const heading = b.title === b.intro ? "Watch the state change" : b.title; return `<section class="block micro-video"><div class="micro-copy"><span class="eyebrow">Micro-video · one state change</span><h2>${esc(heading)}</h2><p class="micro-intro">${esc(b.intro)}</p><dl><div><dt>Observe</dt><dd>${esc(b.observation)}</dd></div><div><dt>Therefore</dt><dd>${esc(b.consequence)}</dd></div></dl>${refs(b.source_refs)}</div><div class="micro-media"><video controls preload="metadata" playsinline poster="${esc(poster?.published_path || "")}"><source src="${esc(video?.published_path || "")}" type="video/mp4">${captions ? `<track default kind="captions" srclang="en" label="English" src="${esc(captions.published_path)}">` : ""}</video><div class="beat-list">${b.beats.map((beat) => `<span>${esc(beat)}</span>`).join("")}</div></div></section>`; },
    formula_steps: (b) => `<section class="block"><span class="claim-label">${esc(b.claim_label)}</span><div class="formula-display">${esc(b.formula)}</div><div class="formula-steps">${b.steps.map((step, index) => `<article class="formula-step"><span class="step-number">0${index + 1} / ${esc(step.label)}</span><div class="step-expression">${esc(step.expression)}</div><p>${esc(step.meaning)}</p><span class="primitive-tag origin-${esc(step.primitive.origin)}">${esc(step.primitive.id)}</span></article>`).join("")}</div>${refs(b.source_refs)}</section>`,
    code: (b, bundle) => { const source = bundle.source_packet.code_sources.find((item) => item.code_id === b.code_source_id); const url = source ? `${source.repository}/blob/${source.revision}/${b.path}` : ""; return `<section class="block"><span class="eyebrow">Confirmed upstream code mapping</span><h2>${esc(b.symbol)}</h2><div class="code-block"><div class="code-head">${url ? `<a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(b.path)} ↗</a>` : `<span>${esc(b.path)}</span>`}<span>${esc(b.code_source_id)}</span></div>${b.lines.map((line) => `<div class="code-line"><span class="line-no">${esc(line.number)}</span><code>${esc(line.code)}</code><span class="code-map">↳ ${esc(line.maps_to)}</span></div>`).join("")}</div>${refs(b.source_refs)}</section>`; },
    line_chart: (b) => {
      const points = b.series.flatMap((series) => series.points);
      const xs = points.map((point) => Number(point.x));
      const ys = points.map((point) => Number(point.y));
      const xMin = Math.min(...xs); const xMax = Math.max(...xs);
      const yMin = Math.min(...ys); const yMax = Math.max(...ys);
      const scale = (value, min, max, start, end) => max === min ? (start + end) / 2 : start + (value - min) / (max - min) * (end - start);
      const polyline = (series) => series.points.map((point) => `${scale(Number(point.x), xMin, xMax, 70, 610)},${scale(Number(point.y), yMin, yMax, 300, 30)}`).join(" ");
      return `<section class="block chart"><span class="claim-label">${esc(b.claim_label)}</span><h2>${esc(b.title)}</h2><div class="line-chart-wrap"><svg class="line-chart-svg" viewBox="0 0 680 360" role="img" aria-label="${esc(b.title)}"><line x1="70" y1="300" x2="630" y2="300"/><line x1="70" y1="20" x2="70" y2="300"/>${b.series.map((series) => `<polyline points="${polyline(series)}" style="--series-color:${accent(series.accent)}"/>${series.points.map((point) => `<circle cx="${scale(Number(point.x), xMin, xMax, 70, 610)}" cy="${scale(Number(point.y), yMin, yMax, 300, 30)}" r="5" style="--series-color:${accent(series.accent)}"><title>${esc(series.label)}: ${esc(point.x)}, ${esc(point.y)}</title></circle>`).join("")}`).join("")}<text x="350" y="346" text-anchor="middle">${esc(b.x_label)}</text><text x="18" y="165" text-anchor="middle" transform="rotate(-90 18 165)">${esc(b.y_label)}</text><text x="70" y="322" text-anchor="middle">${esc(xMin)}</text><text x="610" y="322" text-anchor="middle">${esc(xMax)}</text><text x="58" y="304" text-anchor="end">${esc(yMin)}</text><text x="58" y="34" text-anchor="end">${esc(yMax)}</text></svg><div class="chart-legend">${b.series.map((series) => `<span style="--legend-color:${accent(series.accent)}"><i></i>${esc(series.label)}</span>`).join("")}</div></div>${refs(b.source_refs)}</section>`;
    },
    bar_chart: (b) => { const min = b.axis_min || 0; const range = Math.max(1e-9, b.axis_max - min); return `<section class="block chart"><span class="claim-label">${esc(b.claim_label)}</span><h2>${esc(b.title)}</h2><div class="chart-bars">${b.groups.map((group) => `<div class="chart-row"><span>${esc(group.label)}</span><div class="chart-track" title="axis ${min} to ${b.axis_max}"><div class="chart-fill" style="--width:${Math.max(0, (group.value - min) / range * 100)}%;--bar-color:${accent(group.accent)}"></div></div><span class="chart-value">${esc(group.value)}${group.uncertainty ? ` ${esc(group.uncertainty)}` : ""}</span></div>`).join("")}</div><div class="chart-note">axis ${esc(min)}–${esc(b.axis_max)} ${esc(b.unit)} · ${esc(b.claim_label)}</div>${refs(b.source_refs)}</section>`; },
    reported_trends: (b) => `<section class="block"><span class="claim-label">${esc(b.claim_label)}</span><h2>${esc(b.title)}</h2><div class="trend-list">${b.items.map((item) => `<article class="trend-item"><strong>${esc(item.label)}</strong><p>${esc(item.finding)} <span class="source-ref">${esc(item.source_ref)}</span></p></article>`).join("")}</div></section>`,
    limitation: (b) => `<section class="block"><span class="eyebrow">Claim boundary</span><h2>What remains conditional</h2><div class="limitation-list">${b.items.map((item) => `<article class="limitation-item"><strong>${esc(item.label)}</strong><p>${esc(item.detail)}</p></article>`).join("")}</div>${refs(b.source_refs)}</section>`,
    rotation: (b) => `<section class="block"><span class="claim-label">${esc(b.claim_label)}</span><h2>${esc(b.title)}</h2><div class="rotation-stage"><svg viewBox="0 0 420 420" role="img" aria-label="Two vectors separated by a rotation angle"><line x1="40" y1="210" x2="380" y2="210" stroke="var(--line-strong)"/><line x1="210" y1="40" x2="210" y2="380" stroke="var(--line-strong)"/><circle cx="210" cy="210" r="150" fill="none" stroke="var(--line)"/><line x1="210" y1="210" x2="350" y2="180" stroke="var(--violet)" stroke-width="7"/><line x1="210" y1="210" x2="280" y2="80" stroke="var(--orange)" stroke-width="7"/><path d="M 280 195 A 74 74 0 0 0 250 145" fill="none" stroke="var(--orange)" stroke-width="3"/><circle cx="210" cy="210" r="6" fill="var(--ink)"/></svg><div class="rotation-copy"><span class="big-angle">${esc(b.angle_label)}</span><div class="formula-display">${esc(b.formula)}</div><p>${esc(b.note)}</p></div></div>${refs(b.source_refs)}</section>`,
  };

  function media(bundle, id) { return bundle.source_packet.media.find((item) => item.media_id === id); }

  function renderSourcePanel(bundle, sectionPlan) {
    const run = currentRun();
    const sourceLinks = bundle.source_packet.sources.map((source) => source.url ? `<a href="${esc(source.url)}" target="_blank" rel="noreferrer">${esc(source.revision)} · ${source.page_count} pages ↗</a>` : `<div class="source-meta">${esc(source.revision)} · ${source.page_count} pages · local input</div>`).join("");
    const codeLinks = bundle.source_packet.code_sources.map((source) => `<a href="${esc(source.repository)}/tree/${esc(source.revision)}" target="_blank" rel="noreferrer">repository @ ${esc(source.revision.slice(0, 8))} ↗</a>`).join("");
    const deep = sectionPlan.deep_links.map((id) => {
      const entry = bundle.section_content.appendix_entries.find((item) => item.id === id);
      return `<button type="button" data-appendix="${esc(id)}">${esc(entry?.title || id)} →</button>`;
    }).join("");
    const trace = bundle.generation.stage_traces.map((item) => `${item.stage}: ${item.response_sha256.slice(0, 8)}`).join("<br>");
    $("#source-panel").innerHTML = `<section><h2>Selected model run</h2><div class="source-meta"><b>${esc(run.label)}</b><br>provider: ${esc(run.providers.join(" + "))}<br>model: ${esc(run.models.join(" + "))}<br>status: ${esc(run.status)}</div></section><section><h2>Primary sources</h2>${sourceLinks}${codeLinks}<div class="source-meta">source packet ${esc(bundle.generation.source_packet_sha256.slice(0, 16))}…<br>PDF SHA ${esc(bundle.source_packet.sources[0].sha256.slice(0, 16))}…<br>Manim: ${esc(bundle.source_packet.scene_renderer.engine)}<br>coding agent: not required</div></section><section><h2>Deep links</h2>${deep}</section><section><h2>API trace</h2><div class="source-meta">${trace}<br>mode: ${esc(bundle.generation.stage_traces[0].generation_mode)}</div></section>`;
    $("#source-panel").querySelectorAll("[data-appendix]").forEach((button) => button.addEventListener("click", () => location.hash = routeHash("appendix", `${bundle.paper_id}/${button.dataset.appendix}`)));
  }

  function bindLessonInteractions() {
    document.querySelectorAll(".learner-check").forEach((details) => {
      details.addEventListener("toggle", () => {
        const button = details.querySelector("button");
        if (button) button.textContent = details.open ? "Answer revealed" : "Reveal answer";
      });
    });
  }

  function renderBacktranslation() {
    const data = state.backtranslation;
    const model = data.models.find((item) => item.candidate_id === state.activeBacktranslationModel);
    const completedForModel = data.cases.reduce((total, item) => total + item.runs[model.candidate_id].rounds.filter((round) => round.status === "completed").length, 0);
    const modelButtons = data.models.map((item) => `<button type="button" data-bt-model="${esc(item.candidate_id)}" aria-pressed="${item.candidate_id === model.candidate_id ? "true" : "false"}"><strong>${esc(item.label)}</strong><span>${esc(item.model_id)}</span></button>`).join("");
    const loop = data.feedback_loop.map((item, index) => `<li><b>${String(index + 1).padStart(2, "0")}</b><span>${esc(item)}</span></li>`).join("");
    const headers = ["Description", "Human original", ...data.display_columns].map((item, index) => `<div class="bt-column-head ${index < 2 ? "bt-sticky-head" : ""}" style="--sticky-index:${index}">${esc(item)}</div>`).join("");
    const matrixRows = data.cases.map((item) => renderBacktranslationRow(item, model)).join("");
    const weights = Object.entries(data.score_policy).filter(([, value]) => typeof value === "number").map(([key, value]) => `<span><b>${Math.round(value * 100)}%</b>${esc(key.replaceAll("_", " "))}</span>`).join("");
    const smoke = model.adapter_smoke?.successful_attempt;
    const library = data.library_context;
    const trajectory = data.trajectory_dataset;
    const trajectoryLabels = trajectory?.transition_label_counts || {};
    const trajectoryErrors = Object.entries(trajectory?.error_label_counts || {})
      .sort((left, right) => right[1] - left[1])
      .slice(0, 7)
      .map(([label, count]) => `<span><b>${count}</b>${esc(label.replaceAll("_", " "))}</span>`)
      .join("");
    const harnessFlow = (trajectory?.harness?.control_loop || [])
      .map((step, index) => `<li><b>${String(index + 1).padStart(2, "0")}</b><span>${esc(step)}</span></li>`)
      .join("");
    const adapterEvidence = smoke ? `${fmtTokens(smoke.total_tokens)} tokens · ${fmtDuration(smoke.duration_ms)} · ${esc(smoke.perception_mode_observed.replaceAll("_", " "))}` : "video capability is not yet verified";
    $("#backtranslation-view").innerHTML = `
      <header class="bt-hero">
        <div>
          <span class="eyebrow">Human video → recovered visual program</span>
          <h1>Backtranslation,<br>as signal finding.</h1>
        </div>
        <div class="bt-hero-copy">
          <p>Each model watches one complete reference video, decomposes it into teaching scenes, then renders and composes those scenes into one candidate. It reads a pinned Manim repository and may add reusable functions only inside its own isolated namespace.</p>
          <div class="bt-run-status"><span>${esc(data.execution_summary.status.replaceAll("_", " "))}</span><b>${data.execution_summary.cases} sources</b><b>${completedForModel} completed rounds</b><b>iter0 → iter5 → X</b></div>
          <small>${esc(data.execution_summary.note)}</small>
        </div>
      </header>
      <section class="bt-method" aria-labelledby="bt-loop-title">
        <div>
          <span class="eyebrow">Closed visual feedback loop</span>
          <h2 id="bt-loop-title">The candidate is also its own critic.</h2>
          <p>The official Manim library source is visible. The upstream 3b1b scene source and every other model workspace stay hidden. This separates API grounding from answer leakage.</p>
        </div>
        <ol>${loop}</ol>
      </section>
      <section class="bt-candidate-bar" aria-label="Backtranslation model candidate">
        <div><span class="eyebrow">Candidate</span><strong>${esc(model.label)}</strong><small>${esc(model.provider)} · ${esc(model.model_id)}</small><small>${esc(model.status.replaceAll("_", " "))}</small><small>${adapterEvidence}</small></div>
        <div class="bt-candidate-options">${modelButtons}</div>
      </section>
      <section class="bt-score-strip" aria-label="Best round score weights">${weights}<small>Pixel similarity is a tiebreaker only.</small></section>
      <section class="bt-library-contract" aria-label="Multi-scene and library contract">
        <div><span>Library substrate</span><strong>Manim Community ${esc(library.version)}</strong><small>${esc(library.revision.slice(0, 12))} · pinned source</small></div>
        <div class="bt-compose-path"><b>Complete video</b><i>→</i><b>Scene graph</b><i>→</i><b>Independent renders</b><i>→</i><b>Composed candidate</b></div>
        <div><span>Extension boundary</span><strong>model_extensions/&lt;candidate&gt;/</strong><small>case-local · cross-model reads disabled</small></div>
      </section>
      ${trajectory ? `<section class="bt-harness-corpus" aria-labelledby="bt-harness-title">
        <div class="bt-harness-heading">
          <span class="eyebrow">Two durable outputs</span>
          <h2 id="bt-harness-title">A better generation harness—and the mistakes that can train the next model.</h2>
          <p>The harness narrows each revision to observable evidence. The trajectory corpus keeps the old code, paired feedback, error labels, new code, and measured outcome. A worse revision is supervision, not discarded history.</p>
        </div>
        <div class="bt-harness-metrics">
          <article><span>Harness</span><strong>${trajectory.harness.stages} stages</strong><small>${trajectory.harness.tools} tools · ${trajectory.harness.error_types} error types</small></article>
          <article><span>Observed corpus</span><strong>${trajectory.round_records} rounds</strong><small>${trajectory.training_views.sft_positive} SFT · ${trajectory.training_views.reward_labeled} reward · ${trajectory.training_views.preference_pairs} valid preference pairs</small></article>
          <article><span>Repair outcomes</span><strong>${trajectoryLabels.positive_repair || 0} better / ${trajectoryLabels.negative_regression || 0} worse</strong><small>${trajectoryLabels.duplicate_noop || 0} rendered no-op · all retained</small></article>
          <article><span>Prompt provenance</span><strong>${trajectory.prompt_capture.exact} exact / ${trajectory.prompt_capture.hash_only_legacy} hash-only</strong><small>exact prompt capture is mandatory for future rounds</small></article>
        </div>
        <ol class="bt-harness-flow">${harnessFlow}</ol>
        <div class="bt-error-ledger"><b>Observed error labels</b><div>${trajectoryErrors}</div></div>
      </section>` : ""}
      <section class="bt-matrix-section" aria-labelledby="bt-matrix-title">
        <div class="bt-matrix-intro"><div><span class="eyebrow">10-source reconstruction contact sheet</span><h2 id="bt-matrix-title">One authored reference. Six observed attempts. One selected round.</h2></div><p>Scroll horizontally to follow a row. Exact lesson clips play inline; remaining source posters load the creator-hosted YouTube video. The first two columns stay anchored on wide screens.</p></div>
        <div class="bt-matrix" role="table" aria-label="Backtranslation iterations for ${esc(model.label)}">
          <div class="bt-grid bt-header-row" role="row">${headers}</div>
          ${matrixRows}
        </div>
      </section>
      <section class="bt-boundary"><span class="eyebrow">Evidence boundary</span><p>${esc(data.claim_scope)} ${esc(data.public_original_policy)}</p></section>`;
    $("#backtranslation-view").querySelectorAll("[data-bt-model]").forEach((button) => button.addEventListener("click", () => {
      location.hash = routeHash("backtranslation", button.dataset.btModel);
    }));
    $("#backtranslation-view").querySelectorAll("[data-load-source]").forEach((button) => button.addEventListener("click", () => {
      const host = button.parentElement;
      host.innerHTML = `<iframe src="${esc(button.dataset.embed)}?autoplay=1&rel=0" title="${esc(button.dataset.title)} — original 3Blue1Brown video" loading="lazy" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>`;
    }));
  }

  function renderBacktranslationRow(item, model) {
    const run = item.runs[model.candidate_id];
    const description = `<article class="bt-description bt-sticky-cell" style="--sticky-index:0"><div><span>${esc(item.case_id)}</span><b>${esc(item.year)}</b></div><h3>${esc(item.title)}</h3><p>${esc(item.description)}</p><strong>Why this case</strong><p>${esc(item.why_in_set)}</p><div class="bt-signal-list">${item.signal_targets.map((signal) => `<i>${esc(signal)}</i>`).join("")}</div><div class="bt-source-links"><a href="${esc(item.lesson_url)}" target="_blank" rel="noreferrer">lesson ↗</a><a href="${esc(item.source_url)}" target="_blank" rel="noreferrer">hidden source audit ↗</a></div></article>`;
    const original = item.reference_clip_url
      ? `<div class="bt-original bt-sticky-cell" style="--sticky-index:1"><video controls preload="metadata"><source src="${esc(item.reference_clip_url)}" type="video/mp4"></video><small class="bt-reference-label">${esc(item.reference_unit)}</small><a href="${esc(item.lesson_url)}" target="_blank" rel="noreferrer">Open creator-hosted lesson ↗</a></div>`
      : `<div class="bt-original bt-sticky-cell" style="--sticky-index:1"><button type="button" data-load-source data-embed="${esc(item.original_embed_url)}" data-title="${esc(item.title)}" aria-label="Load original video: ${esc(item.title)}"><img src="https://i.ytimg.com/vi/${esc(item.video_id)}/hqdefault.jpg" alt="" loading="lazy"><span aria-hidden="true">▶</span><small>Load human original</small></button><a href="${esc(item.original_watch_url)}" target="_blank" rel="noreferrer">Watch on YouTube ↗</a></div>`;
    const iterations = run.rounds.map((round) => renderBacktranslationRound(round, run.selected_round)).join("");
    const selected = run.selected_round == null
      ? `<div class="bt-round bt-selected bt-empty"><span>X</span><strong>No observed best yet</strong><p>Selection waits for at least one completed, scored render.</p></div>`
      : `<div class="bt-round bt-selected"><span>X → iter${run.selected_round}</span><strong>Best observed round</strong><p>Weighted score ${run.rounds[run.selected_round].score.toFixed(3)}</p><a href="${esc(run.rounds[run.selected_round].video_url)}">Open selected video ↗</a></div>`;
    return `<div class="bt-grid bt-case-row" role="row">${description}${original}${iterations}${selected}</div>`;
  }

  function renderBacktranslationRound(round, selectedRound) {
    const selected = round.index === selectedRound;
    if (round.status !== "completed") {
      const emptyNote = round.status !== "not_run" && round.critic_summary
        ? round.critic_summary
        : (round.index === 0 ? "Initial video-conditioned generation." : "Reference/candidate critique, then one targeted repair.");
      return `<div class="bt-round bt-empty"><span>iter${round.index}</span><strong>${esc(round.status.replaceAll("_", " "))}</strong><p>${esc(emptyNote)}</p></div>`;
    }
    const media = round.video_url ? `<video controls preload="metadata" ${round.poster_url ? `poster="${esc(round.poster_url)}"` : ""}><source src="${esc(round.video_url)}" type="video/mp4"></video>` : "";
    const modelScore = round.model_score == null ? "n/a" : Number(round.model_score).toFixed(3);
    const judgeScore = round.score == null ? "n/a" : Number(round.score).toFixed(3);
    const modelComponents = renderBacktranslationScoreComponents(round.model_score_components);
    const judgeComponents = renderBacktranslationScoreComponents(round.score_components);
    const sceneCount = round.scene_count || 1;
    const extensionCount = Array.isArray(round.library_extensions) ? round.library_extensions.length : 0;
    const packageLabel = round.package_contract === "legacy-single-scene/v2" ? "legacy pilot" : "isolated package";
    const scenePlan = Array.isArray(round.scene_plan) ? round.scene_plan : [];
    const scenePlanDetail = scenePlan.length ? `<details class="bt-package-detail"><summary>Scene plan & model functions</summary><ol>${scenePlan.map((scene) => `<li><b>${esc(scene.scene_id)}</b><span>${Number(scene.start_time).toFixed(1)}–${Number(scene.end_time).toFixed(1)}s</span><p>${esc(scene.purpose)}</p></li>`).join("")}</ol>${extensionCount ? `<div>${round.library_extensions.map((item) => `<code>${esc(item.symbol)}</code>`).join("")}</div>` : `<small>No candidate-owned extension in this round.</small>`}</details>` : "";
    return `<div class="bt-round ${selected ? "bt-round-best" : ""}"><span>iter${round.index}${selected ? " · selected" : ""}</span>${media}<div class="bt-package-meta"><b>${sceneCount} scene${sceneCount === 1 ? "" : "s"}</b><b>${extensionCount} new function${extensionCount === 1 ? "" : "s"}</b><small>${esc(packageLabel)}</small></div>${scenePlanDetail}<div class="bt-round-scores"><div><small>Model self-score</small><strong>${modelScore}</strong></div><div><small>Cross-model judge</small><strong>${judgeScore}</strong></div></div><small class="bt-judge-label">${esc(round.judge_label || "Independent evaluator")}</small><details class="bt-score-detail"><summary>Score components</summary><div><b>Self</b>${modelComponents}</div><div><b>Judge</b>${judgeComponents}</div></details><p>${esc(round.critic_summary || "Critique recorded in the run manifest.")}</p>${round.changes ? `<small>${esc(round.changes)}</small>` : ""}</div>`;
  }

  function renderBacktranslationScoreComponents(components) {
    if (!components) return `<small class="bt-score-missing">not recorded</small>`;
    return Object.entries(components).map(([key, value]) => `<span title="${esc(key.replaceAll("_", " "))}"><i style="--score:${Math.max(0, Math.min(1, Number(value)))}"></i><em>${esc(key.split("_").map((word) => word[0]).join("").toUpperCase())}</em><strong>${Number(value).toFixed(2)}</strong></span>`).join("");
  }

  function renderAppendix(paperFilter, entryId) {
    const bundles = paperFilter && currentBundle(paperFilter) ? [currentBundle(paperFilter)] : state.catalog.papers.map((paper) => currentBundle(paper.paper_id));
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
