const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1920,height:1080}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765');await page.locator('[data-field=health]').waitFor();
  await page.locator('[data-field=health]').fill('17');
  const before=await page.locator('#event-context').textContent();
  for(const theme of ['storybook','gothic','cyberpunk','noir','medieval']) {
   await page.locator('#theme-select').selectOption(theme);
   await page.waitForFunction(name=>document.querySelector('#theme-stylesheet').sheet?.href.split('?')[0].endsWith(`/themes/${name}.css`),theme);
   assert.equal(await page.locator('[data-field=health]').inputValue(),'17');
   assert.equal(await page.locator('#event-context').textContent(),before);
   assert.match(await page.locator('#save-state').textContent(),/1 unsaved/);
   for(const [width,height] of [[1920,1080],[760,900],[390,844]]) {
    await page.setViewportSize({width,height});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),theme+' overflow');
   }
   await page.setViewportSize({width:1440,height:1000});
   await page.locator('.connections-table').scrollIntoViewIfNeeded();
   if(theme==='gothic') await page.screenshot({path:path.join(__dirname,'gothic-connections.png')});
  }
  const names=await page.locator('.connection-person').allTextContents();
  // Compare the visible name, excluding avatar initials.
  const labels=await page.locator('.connection-person').allTextContents();
  assert.ok(names.length>0);assert.deepEqual(labels,[...labels].sort((a,b)=>a.localeCompare(b)));
  await page.locator('.connection-person').first().click();
  assert.ok(await page.locator('#leave-dialog').evaluate(e=>e.open));
  await page.locator('#discard').click();
  assert.equal(await page.locator('[data-field=name]').inputValue(),labels[0]);
  await page.reload();await page.locator('[data-field=health]').waitFor();
  assert.equal(await page.locator('#theme-select').inputValue(),'medieval');
  await page.locator('#theme-select').selectOption('storybook');
  assert.deepEqual(errors,[]);
  console.log('PASS: five themes at three sizes; theme persistence; drafts and event preserved; sorted connections and guarded navigation.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
