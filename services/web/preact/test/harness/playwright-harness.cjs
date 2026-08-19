#!/usr/bin/env node
/**
 * Generalized Playwright render-test harness for Hermes frontend verification.
 *
 * Instead of copy-pasting a custom .cjs script for every component test, this
 * harness reads a JSON config file that declares:
 *   - url:           the page to load
 *   - selectors:     named CSS selectors to count (e.g. ".react-flow__node" → "nodes")
 *   - evaluate:      a JavaScript expression to run in-page for structured output
 *   - screenshot:     optional path to save a full-page screenshot
 *   - wait_for:      optional selector to wait for before evaluating (default: networkidle)
 *   - timeout:       navigation timeout in ms (default 15000)
 *
 * Usage:
 *   node playwright-harness.cjs <config.json>
 *   # or with a custom URL override:
 *   node playwright-harness.cjs tests/pedalboard-dag.json --url http://localhost:4322/my-page
 *
 * The harness exits non-zero if any assertion fails, making it suitable for CI
 * and cron-job integration.
 *
 * Pre-requisites:
 *   - Run inside a host-networked container with Playwright Chromium installed
 *     (see the `render-verify` skill for the canonical container setup).
 *   - The target URL must be reachable from the container (host network or
 *     port-forwarded).
 */
'use strict';

const { chromium } = require('playwright');
const path = require('path');

// ── Parse arguments ─────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const urlOverride = args.find(a => a.startsWith('--url='))?.split('=')[1];
const configPath = args.find(a => !a.startsWith('--'));

if (!configPath) {
  console.error('Usage: node playwright-harness.cjs <config.json> [--url=http://...]');
  process.exit(2);
}

let config;
try {
  config = require(path.resolve(configPath));
} catch (e) {
  console.error('Failed to load config:', e.message);
  process.exit(2);
}

const URL = urlOverride || config.url;
if (!URL) {
  console.error('No URL specified in config or --url override.');
  process.exit(2);
}

const waitForSelector = config.wait_for;     // optional — wait for DOM element
const timeout = config.timeout || 15000;
const screenshotPath = config.screenshot;     // optional

(async () => {
  const browser = await chromium.launch({
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--ignore-certificate-errors',   // needed for self-signed Traefik TLS
    ],
  });

  const page = await browser.newPage();
  const errors = [];
  const consoleMessages = [];

  // Capture console messages and page errors
  page.on('console', msg => {
    consoleMessages.push(`${msg.type()}: ${msg.text()}`);
    if (msg.type() === 'error') errors.push(`CONSOLE: ${msg.text()}`);
  });
  page.on('pageerror', err => errors.push(`PAGEERR: ${err.message}`));

  // ── Navigate ─────────────────────────────────────────────────────────────
  try {
    if (waitForSelector) {
      await page.goto(URL, { waitUntil: 'domcontentloaded', timeout });
      await page.waitForSelector(waitForSelector, { timeout: config.wait_timeout || 10000 });
    } else {
      await page.goto(URL, { waitUntil: 'networkidle', timeout });
    }
  } catch (e) {
    errors.push(`NAV: ${e.message}`);
  }

  // Give components time to finish rendering / data fetching
  if (config.settle_ms) {
    await new Promise(r => setTimeout(r, config.settle_ms));
  } else if (!waitForSelector) {
    await new Promise(r => setTimeout(r, 3000));
  }

  // ── Run assertions ───────────────────────────────────────────────────────
  const results = {};

  // Count selectors
  if (config.selectors) {
    for (const [label, selector] of Object.entries(config.selectors)) {
      results[label] = await page.$$eval(selector, els => els.length);
    }
  }

  // Structured in-page evaluation — config.evaluate is a string expression
  // that runs in the browser context. We wrap it in parentheses so the
  // parser treats `{ ... }` as an object literal, not a block statement.
  if (config.evaluate) {
    results.evaluated = await page.evaluate(`(${config.evaluate})`);
  }

  // ── Screenshot (optional) ────────────────────────────────────────────────
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true });
    results.screenshot = screenshotPath;
  }

  // ── Assert expectations ──────────────────────────────────────────────────
  let passed = true;
  const assertions = config.assert || {};

  for (const [label, expected] of Object.entries(assertions)) {
    const actual = results[label];
    if (actual !== expected) {
      passed = false;
      console.error(`ASSERT FAIL: ${label} — expected ${expected}, got ${actual}`);
    }
  }

  // ── Report ───────────────────────────────────────────────────────────────
  console.log('=== TEST RESULTS ===');
  console.log('URL:', URL);
  if (results.evaluated) {
    console.log('Evaluated:', JSON.stringify(results.evaluated, null, 2));
  }
  for (const [label, count] of Object.entries(results)) {
    if (label !== 'evaluated' && label !== 'screenshot') {
      console.log(`${label}: ${count}`);
    }
  }
  if (screenshotPath) console.log('Screenshot:', screenshotPath);
  console.log('Errors:', errors.length > 0 ? errors.join('\n') : 'none');
  console.log('=== Console messages ===');
  consoleMessages.forEach(m => console.log(m));
  console.log('=== VERDICT ===');
  console.log(passed && errors.length === 0 ? 'PASS' : 'FAIL');

  await browser.close();
  process.exit(passed && errors.length === 0 ? 0 : 1);
})().catch(e => {
  console.error('Harness crashed:', e.message);
  process.exit(1);
});
