#!/usr/bin/env node
// Self-contained résumé renderer — no dependencies, runs with plain Node.
// Usage: node render.mjs <content.json> [template] [out.html]
//   template ∈ classic | modern | compact   (default: classic)
// Produces a complete, print-ready HTML document (1.25cm @page margins on every
// page; long entries flow across page breaks; a single bullet never splits).
// Get a PDF by opening the HTML and printing to PDF — margins are baked in.
//
// NOTE: the page/template CSS here is kept in sync with the web app's
// lib/templates/. If you change one, mirror it in the other.

import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const pageCss = `
@page { size: Letter; margin: 1.25cm; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { width: 100%; margin: 0; padding: 0; }
.rt-sec-title { break-after: avoid; page-break-after: avoid; }
.rt-entry-head { break-inside: avoid; page-break-inside: avoid; break-after: avoid; page-break-after: avoid; }
.rt-bullets li { break-inside: avoid; page-break-inside: avoid; }
.rt-text, .rt-bullets li { orphans: 2; widows: 2; }
`.trim();

function renderBody(c) {
  const parts = [];
  parts.push(`<header class="rt-head">`);
  if (c.name) parts.push(`<h1 class="rt-name">${escapeHtml(c.name)}</h1>`);
  if (c.headline) parts.push(`<div class="rt-headline">${escapeHtml(c.headline)}</div>`);
  if (Array.isArray(c.contact) && c.contact.length) {
    parts.push(
      `<div class="rt-contact">${c.contact.map(escapeHtml).join('<span class="rt-sep"> · </span>')}</div>`
    );
  }
  parts.push(`</header>`);

  for (const s of c.sections ?? []) {
    parts.push(`<section class="rt-sec">`);
    if (s.title) parts.push(`<h2 class="rt-sec-title">${escapeHtml(s.title)}</h2>`);
    for (const b of s.blocks ?? []) {
      parts.push(`<div class="rt-entry">`);
      if (b.heading || b.subheading) {
        parts.push(`<div class="rt-entry-head">`);
        if (b.heading) parts.push(`<span class="rt-heading">${escapeHtml(b.heading)}</span>`);
        if (b.subheading) parts.push(`<span class="rt-sub">${escapeHtml(b.subheading)}</span>`);
        parts.push(`</div>`);
      }
      if (b.text) parts.push(`<p class="rt-text">${escapeHtml(b.text)}</p>`);
      if (Array.isArray(b.bullets) && b.bullets.length) {
        parts.push(`<ul class="rt-bullets">`);
        for (const bullet of b.bullets) parts.push(`<li>${escapeHtml(bullet)}</li>`);
        parts.push(`</ul>`);
      }
      parts.push(`</div>`);
    }
    parts.push(`</section>`);
  }
  return parts.join("\n");
}

const TEMPLATES = {
  classic: `
body { font-family: Georgia, 'Times New Roman', serif; color: #1a1a1a; font-size: 11pt; line-height: 1.4; }
.rt-head { text-align: center; margin-bottom: 10pt; }
.rt-name { font-size: 20pt; font-weight: 700; margin: 0; letter-spacing: .02em; }
.rt-headline { font-style: italic; color: #444; margin-top: 2pt; }
.rt-contact { font-size: 9.5pt; color: #444; margin-top: 4pt; }
.rt-sec { margin-top: 12pt; }
.rt-sec-title { font-size: 12pt; text-transform: uppercase; letter-spacing: .08em; text-align: center; border-bottom: 1px solid #000; padding-bottom: 2pt; margin: 0 0 6pt; }
.rt-entry { margin-bottom: 8pt; }
.rt-entry-head { display: flex; justify-content: space-between; gap: 8pt; align-items: baseline; }
.rt-heading { font-weight: 700; }
.rt-sub { color: #555; font-style: italic; white-space: nowrap; }
.rt-text { margin: 2pt 0; }
.rt-bullets { margin: 3pt 0 0; padding-left: 16pt; }
.rt-bullets li { margin: 1.5pt 0; }`.trim(),

  modern: `
body { font-family: Helvetica, Arial, sans-serif; color: #1f2937; font-size: 10.5pt; line-height: 1.45; }
.rt-head { margin-bottom: 12pt; }
.rt-name { font-size: 22pt; font-weight: 700; margin: 0; color: #1f3a5f; }
.rt-headline { color: #374151; margin-top: 2pt; font-size: 11pt; }
.rt-contact { font-size: 9.5pt; color: #4b5563; margin-top: 5pt; }
.rt-sec { margin-top: 13pt; }
.rt-sec-title { font-size: 11pt; text-transform: uppercase; letter-spacing: .1em; color: #1f3a5f; border-bottom: 2px solid #1f3a5f; padding-bottom: 2pt; margin: 0 0 6pt; }
.rt-entry { margin-bottom: 9pt; }
.rt-entry-head { display: flex; justify-content: space-between; gap: 8pt; align-items: baseline; }
.rt-heading { font-weight: 700; }
.rt-sub { color: #6b7280; white-space: nowrap; font-size: 9.5pt; }
.rt-text { margin: 2pt 0; }
.rt-bullets { margin: 3pt 0 0; padding-left: 16pt; }
.rt-bullets li { margin: 2pt 0; }`.trim(),

  compact: `
body { font-family: Helvetica, Arial, sans-serif; color: #111827; font-size: 9.5pt; line-height: 1.3; }
.rt-head { margin-bottom: 7pt; }
.rt-name { font-size: 16pt; font-weight: 700; margin: 0; }
.rt-headline { color: #374151; margin-top: 1pt; font-size: 10pt; }
.rt-contact { font-size: 8.5pt; color: #4b5563; margin-top: 2pt; }
.rt-sec { margin-top: 8pt; }
.rt-sec-title { font-size: 10pt; text-transform: uppercase; letter-spacing: .06em; border-bottom: 1px solid #9ca3af; padding-bottom: 1pt; margin: 0 0 4pt; }
.rt-entry { margin-bottom: 5pt; }
.rt-entry-head { display: flex; justify-content: space-between; gap: 6pt; align-items: baseline; }
.rt-heading { font-weight: 700; }
.rt-sub { color: #6b7280; white-space: nowrap; font-size: 8.5pt; }
.rt-text { margin: 1pt 0; }
.rt-bullets { margin: 2pt 0 0; padding-left: 14pt; }
.rt-bullets li { margin: 1pt 0; }`.trim(),
};

function documentShell(bodyCss, bodyHtml) {
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
${pageCss}
${bodyCss}
</style>
</head>
<body>
<div class="page">
${bodyHtml}
</div>
</body>
</html>`;
}

const [, , contentPath, templateArg = "classic", outPath = "resume.html"] = process.argv;
if (!contentPath) {
  console.error("Usage: node render.mjs <content.json> [classic|modern|compact] [out.html]");
  process.exit(1);
}
const templateId = TEMPLATES[templateArg] ? templateArg : "classic";
const content = JSON.parse(readFileSync(contentPath, "utf8"));
const html = documentShell(TEMPLATES[templateId], renderBody(content));
writeFileSync(outPath, html);
console.log(`Saved résumé to: ${resolve(outPath)}  (template: ${templateId})`);
