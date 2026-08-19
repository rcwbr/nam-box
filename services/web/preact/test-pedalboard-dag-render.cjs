const { chromium } = require('playwright');

const URL = process.argv[2] || 'http://localhost:4322/test-pedalboard-dag';

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  const errors = [];
  const consoleMessages = [];

  page.on('console', msg => {
    consoleMessages.push(msg.type() + ': ' + msg.text());
    if (msg.type() === 'error') errors.push('CONSOLE: ' + msg.text());
  });
  page.on('pageerror', err => errors.push('PAGEERR: ' + err.message));

  try {
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 15000 });
  } catch(e) {
    errors.push('NAV: ' + e.message);
  }

  await new Promise(r => setTimeout(r, 3000));

  const flowCanvas = await page.$('.react-flow');
  const nodes = await page.$$('.react-flow__node');
  const edges = await page.$$('.react-flow__edge');
  const handles = await page.$$('.react-flow__handle');

  console.log('=== RESULTS ===');
  console.log('URL: ' + URL);
  console.log('React Flow canvas:', flowCanvas ? 'found' : 'NOT FOUND');
  console.log('Nodes:', nodes.length);
  console.log('Edges:', edges.length);
  console.log('Handles:', handles.length);
  console.log('Errors:', errors.length > 0 ? errors.join('\n') : 'none');
  console.log('=== Console messages ===');
  consoleMessages.forEach(m => console.log(m));

  await browser.close();
  process.exit(errors.length > 0 ? 1 : 0);
})().catch(e => {
  console.error('Test failed:', e.message);
  process.exit(1);
});
