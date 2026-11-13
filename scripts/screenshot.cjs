// Capture screenshots of the running app (design review and README images).
//
// Usage:
//   streamlit run streamlit_app.py &
//   node scripts/screenshot.cjs --out docs/images --pages home,pricer --theme light --mode pro
//
// Streamlit scrolls inside its own container, so the viewport is resized to the
// content height to capture the whole page. Streamlit exceptions are printed and
// make the script exit non-zero. Requires the `playwright` npm package.
const { chromium } = require("playwright");
const { mkdirSync } = require("node:fs");
const { join } = require("node:path");

const PATHS = { pricer: "", greeks: "greeks", payoff: "payoff",
  surface: "surface", validation: "validation", methods: "methods" };

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith("--")) acc.push([a.slice(2), arr[i + 1]]);
  return acc;
}, []));
const url = args.url ?? "http://localhost:8501";
const out = args.out ?? "docs/images";
const pages = (args.pages ?? Object.keys(PATHS).join(",")).split(",");
const theme = args.theme ?? "light";
const mode = args.mode ?? "plain";
const width = Number(args.width ?? 1440);
const fixedHeight = Number(args.height ?? 0);
const scale = Number(args.scale ?? 1);
const suffix = args.suffix ?? "";
const extraQuery = args.query ? `&${args.query}` : "";
const waitMs = Number(args.wait ?? 2500);

(async () => {
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width, height: fixedHeight || 1000 }, deviceScaleFactor: scale, colorScheme: theme,
});
const page = await context.newPage();
let failed = false;
for (const name of pages) {
  const query = mode === "pro" ? `?mode=Pro${extraQuery}` : (extraQuery ? `?${extraQuery.slice(1)}` : "");
  await page.goto(`${url}/${PATHS[name]}${query}`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="stApp"]', { timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.waitForFunction(() => !document.querySelector('[data-testid="stStatusWidget"]'), null, { timeout: 120000 });
  await page.waitForTimeout(waitMs);
  if (!fixedHeight) {
    const h = await page.evaluate(() => {
      const m = document.querySelector('[data-testid="stMain"]');
      return m ? m.scrollHeight : 2000;
    });
    await page.setViewportSize({ width, height: Math.min(h + 40, 12000) });
    await page.waitForTimeout(1500);
  }
  const errors = page.locator('[data-testid="stException"]');
  const n = await errors.count();
  for (let i = 0; i < n; i++) {
    failed = true;
    console.error(`[${name}] EXCEPTION:\n${(await errors.nth(i).innerText()).slice(0, 2500)}`);
  }
  const path = join(out, `${name}-${mode}-${theme}${suffix}.png`);
  await page.screenshot({ path });
  console.log(path);
  if (!fixedHeight) await page.setViewportSize({ width, height: 1000 });
}
await browser.close();
process.exit(failed ? 1 : 0);
})();
