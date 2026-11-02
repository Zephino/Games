const { chromium } = require('playwright');
const S = process.argv[2];
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: S + '/vid', size: { width: 1280, height: 720 } } });
  const t0 = Date.now(); const mark = (n) => console.log('MARK', n, ((Date.now() - t0) / 1000).toFixed(2));
  const p = await ctx.newPage();
  await p.goto('http://127.0.0.1:8771/index.html'); await p.waitForTimeout(22000);
  await p.addStyleTag({ content: 'body > button, button { display:none !important }' });
  await p.mouse.click(735, 397); await p.waitForTimeout(1200);
  await p.mouse.click(444, 327); await p.waitForTimeout(1200);
  await p.screenshot({ path: S + '/shots/wdc-1.png' });
  await p.mouse.click(835, 171); await p.waitForTimeout(1500);
  await p.mouse.click(799, 345); await p.waitForTimeout(600);
  await p.mouse.click(831, 512); await p.waitForTimeout(5000);
  const T = (c, r) => [196 + 40 * c + 20, 72 + 40 * r + 20];
  for (const [c, r] of [[2, 4], [4, 8], [2, 12]]) { await p.mouse.click(46, 91); await p.waitForTimeout(300); await p.mouse.click(95, 272); await p.waitForTimeout(300); const [x, y] = T(c, r); await p.mouse.click(x, y); await p.waitForTimeout(400); }
  await p.mouse.click(112, 126); await p.waitForTimeout(700);
  await p.mouse.click(112, 153);
  mark('clash_start');
  for (let i = 1; i <= 4; i++) { await p.waitForTimeout(4000); await p.screenshot({ path: S + '/shots/wdc-run' + i + '.png' }); }
  mark('clash_end');
  await ctx.close(); await b.close();
})();
