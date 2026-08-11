#!/usr/bin/env node
// Build a ready-to-send email draft as a standard .eml file, with a file attached
// (the tailored résumé PDF). Double-clicking the .eml opens it as a draft in Apple
// Mail / Outlook / most clients — no API, no login. Review and hit Send.
//
//   node mkdraft.mjs --to <addr> --subject <text> --body-file <body.txt> \
//                    --attach <resume.pdf> --out <draft.eml> [--from <addr>] [--cc <addr>]
//
// --body may be passed inline instead of --body-file. If --to is unknown, pass a
// placeholder like "RECRUITER_EMAIL_HERE" — you'll fill it in when you review.

import { readFileSync, writeFileSync } from "node:fs";
import { resolve, basename } from "node:path";

function parse(argv) {
  const a = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k.startsWith("--")) a[k.slice(2)] = argv[++i];
  }
  return a;
}

const args = parse(process.argv.slice(2));
if (!args.subject || !args.attach || !args.out || (!args.body && !args["body-file"])) {
  console.error(
    "Usage: node mkdraft.mjs --to <addr> --subject <text> (--body <text> | --body-file <file>) --attach <file> --out <draft.eml> [--from <addr>] [--cc <addr>]"
  );
  process.exit(1);
}

const to = args.to || "RECRUITER_EMAIL_HERE";
const subject = args.subject;
const body = args["body-file"] ? readFileSync(args["body-file"], "utf8") : args.body;
const attachPath = args.attach;
const attachName = basename(attachPath);
const attachB64 = readFileSync(attachPath).toString("base64").replace(/(.{76})/g, "$1\r\n");

// MIME type from extension (PDF by default).
const ext = attachName.toLowerCase().split(".").pop();
const mime =
  ext === "pdf"
    ? "application/pdf"
    : ext === "docx"
      ? "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      : ext === "html"
        ? "text/html"
        : "application/octet-stream";

const boundary = `tailorwright_${Date.now().toString(36)}_${Math.floor(Math.random() * 1e9).toString(36)}`;
const CRLF = "\r\n";

const headers = [
  args.from ? `From: ${args.from}` : null,
  `To: ${to}`,
  args.cc ? `Cc: ${args.cc}` : null,
  `Subject: ${subject}`,
  "X-Unsent: 1", // tells Outlook (and others) to open this as an editable draft
  "MIME-Version: 1.0",
  `Content-Type: multipart/mixed; boundary="${boundary}"`,
].filter(Boolean);

const eml =
  headers.join(CRLF) +
  CRLF +
  CRLF +
  `--${boundary}` + CRLF +
  `Content-Type: text/plain; charset="utf-8"` + CRLF +
  `Content-Transfer-Encoding: 8bit` + CRLF +
  CRLF +
  body.replace(/\r?\n/g, CRLF) + CRLF +
  CRLF +
  `--${boundary}` + CRLF +
  `Content-Type: ${mime}; name="${attachName}"` + CRLF +
  `Content-Transfer-Encoding: base64` + CRLF +
  `Content-Disposition: attachment; filename="${attachName}"` + CRLF +
  CRLF +
  attachB64 + CRLF +
  `--${boundary}--` + CRLF;

writeFileSync(args.out, eml);
console.log(`Saved email draft to: ${resolve(args.out)}`);
console.log(`  → To: ${to}${args.cc ? `  Cc: ${args.cc}` : ""}`);
console.log(`  → Attached: ${attachName}`);
console.log("  Open it (double-click) to review in your mail app, then Send.");
