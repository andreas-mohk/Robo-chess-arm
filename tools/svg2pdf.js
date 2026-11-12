// Combine SVG sheets into one PDF, one sheet per page.
// usage: node tools/svg2pdf.js out.pdf <width_mm> <height_mm> a.svg b.svg ...
const {chromium} = require('playwright');
const fs = require('fs'); const path = require('path');
(async () => {
  const [out, w, h, ...files] = process.argv.slice(2);
  const html = `<!doctype html><meta charset="utf-8"><style>@page{size:${w}mm ${h}mm;margin:0}
  body{margin:0}img{display:block;width:${w}mm;height:${h}mm;page-break-after:always}</style>` +
    files.map(f => `<img src="file://${path.resolve(f)}">`).join('');
  const tmp = path.join(path.dirname(path.resolve(out)), '_print.html');
  fs.writeFileSync(tmp, html);
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + tmp, {waitUntil: 'load', timeout: 600000});
  await p.waitForTimeout(1500);
  await p.pdf({path: out, width: `${w}mm`, height: `${h}mm`, printBackground: true, timeout: 600000});
  await b.close(); fs.unlinkSync(tmp);
  console.log('wrote', out, files.length, 'pages');
})();
