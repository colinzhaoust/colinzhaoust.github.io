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

ReSHAPE search-space and planning-specification titles refer to versions of one work. Keep a single current-title record and acknowledge the earlier BiAlign NeurIPS 2026 Oral version; preserve the old page anchor as an alias.
