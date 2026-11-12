// Render a local HTML file (e.g. a Plotly figure) to PNG at 2x scale.
// Usage: node scripts/html_to_png.cjs input.html output.png [width] [height]
const { chromium } = require("playwright");
const { resolve } = require("node:path");

(async () => {
  const [input, output, width = "1500", height = "520"] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: Number(width), height: Number(height) },
    deviceScaleFactor: 2,
  });
  await page.goto("file://" + resolve(input), { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: output });
  await browser.close();
  console.log(output);
})();
