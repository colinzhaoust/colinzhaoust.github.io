# Design

## Direction and scene

User-approved: Rulin Shao's left-text/right-portrait layout and top navigation with the current homepage's understated academic style. Industry researchers read in a normally lit office and need legible evidence quickly: light canvas, dark text, restrained blue links.

## Layout and typography

Approximately 860px reading column. Compact navigation. Two-column bio on desktop; compact name and portrait row followed by full-width biography on mobile. Retain Lato from the existing site with system fallbacks and font-display: swap. Load fonts separately so legacy CSS cannot override the new layout or keyboard focus styles. Plain links, bold titles, smaller author and venue metadata, fine horizontal dividers.

## Architecture

Research: short biography, job-market line, three research directions with links, selected papers. All Research: complete publication list with Large-scale Collaborations immediately before Academic Events. CV and Legacy links in navigation. Original projects and personal sections remain in Legacy.

## States and interaction

Real page and anchor links, no required JavaScript or loading state. Navigation wraps on phones. Visible focus and hover treatments. Distinguish manuscripts, peer-reviewed papers, workshops, and collaborations while preserving venue labels.

## Visual assets

Generated probes and mockups skipped: the user explicitly selected an existing layout and asked for less embellishment. Reuse the existing portrait and avoid invented paper figures.

## Editorial order

Lead with Information Seeking & Human–AI Interaction, followed by Reasoning, Planning & Coding Agents, then Persuasion & Human–AI Alignment. Representative links open public papers directly; work without a public destination points to its local All Research entry.
