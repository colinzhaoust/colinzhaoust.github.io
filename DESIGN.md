# Design

## Direction and scene

User-approved: Rulin Shao's left-text/right-portrait layout and top navigation with the current homepage's understated academic style. Industry researchers read in a normally lit office and need legible evidence quickly: light canvas, dark text, restrained blue links.

## Layout and typography

Approximately 860px reading column. Compact navigation. Two-column bio on desktop; compact name and portrait row followed by full-width biography on mobile. Retain Lato from the existing site with system fallbacks and font-display: swap. Load fonts separately so legacy CSS cannot override the new layout or keyboard focus styles. Plain links, bold titles, smaller author and venue metadata, fine horizontal dividers.

## Architecture

Research: complete legacy biography with internship and mentor acknowledgments, job-market line, original high-level research questions, three research directions with links, selected publications and user-chosen manuscripts. All Research: complete publication list with Large-scale Collaborations immediately before Academic Events. CV and Legacy links in navigation. Large-scale Collaborations uses native details/summary and starts collapsed. Original projects and personal sections remain in Legacy.

## States and interaction

Real page and anchor links, no required JavaScript or loading state. Navigation wraps on phones. Visible focus and hover treatments. Distinguish manuscripts, peer-reviewed papers, workshops, and collaborations while preserving venue labels.

## Visual assets

Generated probes and mockups skipped: the user explicitly selected an existing layout and asked for less embellishment. Reuse the existing portrait and avoid invented paper figures.

## Editorial order

Lead with Information Seeking & Human–AI Interaction, followed by Reasoning, Planning & Coding Agents, then Persuasion & Human–AI Alignment. Representative links open public papers directly; work without a public destination points to its local All Research entry.

## Content preservation

Keep every internship and mentor acknowledgment from the legacy bio, merging internship and education paragraphs where possible, and preserve the original high-level research interests. Submission venues and cycles must not be displayed; use “In submission.” The homepage combines selected publications and user-chosen submissions in Selected Research; the full submission list remains in All Research. 3DCodeEdit is coding research and Xinran is an equal-contribution author.

Unpublished submissions without an arXiv release must not link to OpenReview. Keep their titles as plain text; thematic representative links may point to local All Research entries.

## Awards

Honors and Awards is an independent section between the research overview and Selected Research, following Shangbin Feng’s homepage reference (https://bunsenfeng.github.io/): a compact heading, fine divider below it, and a simple bulleted list with dates inline. Retain the Awards navigation link. Content is based on CV sections/honors.tex; preserve award amounts and distinctions without adding unverified details.

## Selected research and reference ordering

Order representative links and Selected Research newest year first, preserving editorial order for year ties. Show verified venue labels on thematic references, with unpublished work labeled only In submission and no OpenReview link. Include 3DCodeEdit, new debate, ReSHAPE search, Tea Leaves, Knowing When to Stop, Better Harnesses, and Ramon Llull alongside existing published/workshop selections. Pivot-ICL belongs to efficient reasoning in the overview and All Research, not Selected Research. Remove the casual invitation to discuss ideas from the current bio.

ReSHAPE search-space and planning-specification titles refer to versions of one work. Keep a single current-title record and retain BiAlign NeurIPS 2026 Oral in the venue label without the words earlier version; preserve the old page anchor as an alias.

Pivot-ICL is listed under 2025 with In submission, per the author. CV author-order convention puts Xinran first only when he shares first authorship, retaining contribution stars; the website retains its existing publication author ordering.

## Academic events

Follow the date-and-text layout of Rulin Shao’s News section: a compact, lightly bordered scroll region with muted monospaced dates in a narrow left column. Keep Academic Events as the section title and retain the existing position. Use known seasons rather than inventing months, list dated events newest first, and retain ongoing service below them. The region is keyboard focusable; print expands the complete list. Use shorter invitation wording without changing whether an event was invited or completed.

## Copy and venue labels

Use compact conference years such as EMNLP'25 and BiAlign@NeurIPS'26 throughout publication labels. Omit Findings in the Home research overview and selected list, while retaining it in All Research and CV. Keep canonical publication metadata intact; apply short labels only at rendering. Preserve readable sentence gaps at linked text boundaries. Omit Dr. and Prof. in the homepage biography while retaining every mentor name and link.

## Research classification corrections

Interactive Adaptation belongs to Information Seeking & Human–AI Interaction. FaR belongs to Persuasion & Human–AI Alignment. Thrust appears under information seeking as “Thrust: When to Retrieve.” Both FaR and Thrust are explicitly selected works and must remain in Selected Research, ordered by year with the other entries.

## All Research numbering and links

Number publications from 1 within each All Research section, matching Legacy’s section-local numbering. Keep title links and anchors; put supplementary links inline after the venue as [Code], [Project], etc., allowing natural wrapping on mobile. Home lists remain unnumbered. SPHERE belongs in the Information Seeking & Human–AI Interaction overview.

The homepage uses Selected Honors and Awards, omitting Continuous Undergraduate Scholarship and First Class Honors / Dean’s List. Keep their complete records in the CV.

Academic Events uses an unnumbered list with literal whitespace between date and body spans, so copied text and simplified views remain readable without CSS.

Event dates use a single unbroken line, e.g. “Fall, 2026” or “Summer, 2025”, on desktop and mobile.

## October 2026 updates

The three high-level research questions live inside their matching direction blocks (as a `direction-question` line under each heading) instead of a separate list: information seeking ↔ proactive help with information and learning; planning and coding agents ↔ agents that learn, keep memory, and evolve; persuasion and alignment ↔ staying aligned with human goals under high automation. The bio names the two Google DeepMind stints separately (2024 with Azade Nova and Hanie Sedghi; 2026 with Azade Nova). The job-market line says 2026–27 industry job market with a flexible graduation date. Academic Events lists the FrontierIR @ AAAI 2027 general-chair role and marks ML-conference reviewing as ongoing.

Service (workshop chairing, area chairing, reviewing) is its own short bulleted section after Academic Events on both pages, so Academic Events holds only dated items.

Selected Research omits the real-time debate and ReSHAPE search-space manuscripts; within 2026, accepted papers (Intent-aware QA, Strategic Debate) lead before manuscripts.
