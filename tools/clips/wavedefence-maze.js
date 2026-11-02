const { chromium } = require('playwright');
const S = process.argv[2];
const T = (c, r) => [196 + 40 * c + 20, 72 + 40 * r + 20];
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: S + '/vid', size: { width: 1280, height: 720 } } });
  const t0 = Date.now(); const mark = (n) => console.log('MARK', n, ((Date.now() - t0) / 1000).toFixed(2));
  const p = await ctx.newPage();
  await p.goto('http://127.0.0.1:8771/index.html'); await p.waitForTimeout(22000);
  await p.addStyleTag({ content: 'button { display:none !important }' });
  await p.mouse.click(735, 397); await p.waitForTimeout(1200);
  await p.mouse.click(835, 171); await p.waitForTimeout(1500);
  await p.mouse.click(735, 482); await p.waitForTimeout(4000);
  await p.mouse.click(60, 91); await p.waitForTimeout(800);
  mark('build_start');
  await p.mouse.click(95, 236); await p.waitForTimeout(300); // Wall
  const walls = [];
  for (let r = 0; r <= 11; r++) walls.push([5, r]);
  for (let r = 3; r <= 14; r++) walls.push([10, r]);
  for (let r = 0; r <= 11; r++) walls.push([15, r]);
  for (const [c, r] of walls) { const [x, y] = T(c, r); await p.mouse.click(x, y); await p.waitForTimeout(90); }
  await p.screenshot({ path: S + '/shots/wd-walls.png' });
  const towers = [[95, 272, [7, 12]], [95, 272, [12, 2]], [95, 416, [13, 12]], [95, 380, [17, 13]]];
  for (const [bx, by, [c, r]] of towers) { await p.mouse.click(60, 91); await p.waitForTimeout(250); await p.mouse.click(bx, by); await p.waitForTimeout(250); const [x, y] = T(c, r); await p.mouse.click(x, y); await p.waitForTimeout(400); }
  mark('build_end');
  await p.screenshot({ path: S + '/shots/wd-built.png' });
  await p.mouse.click(107, 126); // Start Round
  await p.waitForTimeout(700);
  await p.mouse.click(107, 153); // Skip Timer
  mark('wave_start');
  for (let i = 1; i <= 4; i++) { await p.waitForTimeout(5000); await p.screenshot({ path: S + '/shots/wd-wave' + i + '.png' }); }
  mark('wave_end');
  await ctx.close(); await b.close();
})();
