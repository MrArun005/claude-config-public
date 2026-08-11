#!/usr/bin/env node
// Convert a rendered résumé HTML file to PDF, if a headless browser engine is
// available. Tries Playwright, then Puppeteer. If neither is installed, prints
// instructions to print-to-PDF manually (the HTML is already print-ready).
//
//   node topdf.mjs "<input.html>" "<output.pdf>"
//
// Blocks all network/file:// loads while rendering (the résumé HTML is fully
// self-contained), so there is no SSRF surface.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const [, , htmlPath, pdfPath] = process.argv;
if (!htmlPath || !pdfPath) {
  console.error('Usage: node topdf.mjs "<input.html>" "<output.pdf>"');
  process.exit(1);
}

async function loadEngine() {
  try {
    const { chromium } = await import("playwright");
    return { kind: "playwright", chromium };
  } catch {}
  try {
    const puppeteer = (await import("puppeteer")).default;
    return { kind: "puppeteer", puppeteer };
  } catch {}
  return null;
}

const html = readFileSync(htmlPath, "utf8");
const engine = await loadEngine();

if (!engine) {
  console.log(
    "No headless browser found (playwright/puppeteer). The HTML is print-ready —\n" +
      `open ${resolve(htmlPath)} in a browser and Print → Save as PDF (margins are baked in).`
  );
  process.exit(0);
}

if (engine.kind === "playwright") {
  const browser = await engine.chromium.launch();
  const page = await browser.newPage();
  await page.route("**/*", (r) => {
    const u = r.request().url();
    return u.startsWith("data:") || u.startsWith("about:") ? r.continue() : r.abort();
  });
  await page.setContent(html, { waitUntil: "load" });
  await page.pdf({ path: pdfPath, format: "Letter", printBackground: true, preferCSSPageSize: true });
  await browser.close();
} else {
  const browser = await engine.puppeteer.launch();
  const page = await browser.newPage();
  await page.setRequestInterception(true);
  page.on("request", (req) => {
    const u = req.url();
    u.startsWith("data:") || u.startsWith("about:") ? req.continue() : req.abort();
  });
  await page.setContent(html, { waitUntil: "load" });
  await page.pdf({ path: pdfPath, printBackground: true, preferCSSPageSize: true, format: "Letter" });
  await browser.close();
}

console.log(`Saved PDF to: ${resolve(pdfPath)}`);
