// Renders guia-demo-iiot.html to guia-demo-iiot.pdf (A4) and, optionally, PNG previews.
// Usage: node docs/demo/render-pdf.cjs [previewDir]
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const html = path.join(__dirname, "guia-demo-iiot.html");
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: 2 });
  await page.goto("file://" + html, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: path.join(__dirname, "guia-demo-iiot.pdf"),
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true,
  });
  const previewDir = process.argv[2];
  if (previewDir) {
    const pages = await page.$$("section.page");
    for (let i = 0; i < pages.length; i++) {
      await pages[i].screenshot({ path: path.join(previewDir, `p${i + 1}.png`) });
    }
  }
  await browser.close();
})();
