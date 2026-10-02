// Set PLAYWRIGHT_MODULE when Playwright is provided outside this repository.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765');
  const field=k=>page.locator(`[data-field="${k}"]`);
  await field('health').waitFor();
  assert.equal(await page.locator('.cast-row').count(),18);
  assert.equal(await field('summary').getAttribute('aria-label'),'Short Summary');
  assert.equal(await field('summary').getAttribute('placeholder'),'Write a sentence describing who Mira Vale is and what they want');
  assert.equal(await page.locator('#bottom-review-button').isDisabled(),true);
  assert.equal(await page.locator('.timeline-heading .eyebrow').textContent(),'Story Time Line');
  assert.equal(await page.locator('.relationship-kind[data-tone=hostile]').filter({hasText:'Enemy'}).count(),1);
  assert.equal(await page.locator('.relationship-kind[data-tone=wary]').filter({hasText:'Distrust'}).count(),1);
  assert.ok(await page.locator('.relationship-kind[data-tone=friendly]').count()>0);

  await page.locator('#cast-search').fill('Mira'); assert.equal(await page.locator('.cast-row').count(),1);
  await page.locator('#cast-search').fill('');
  await field('health').fill('12');await field('inventory').fill('A silver lantern');
  await page.locator('#bottom-review-button').click();assert.equal(await page.locator('[name=carry]').count(),2);
  await page.locator('#deselect-all').click();assert.equal(await page.locator('[name=carry]:checked').count(),0);
  await page.locator('#select-all').click();assert.equal(await page.locator('[name=carry]:checked').count(),2);
  await page.locator('#cancel-review').click();assert.equal(await field('health').inputValue(),'12');
  await page.locator('#review-button').click();await page.locator('[name=carry][value=health]').uncheck();
  await page.screenshot({path:path.join(__dirname,'save-review.png')});
  await page.locator('#review-form button[type=submit]').click();
  await page.locator('#next-event').click();assert.equal(await field('health').inputValue(),'');assert.equal(await field('inventory').inputValue(),'A silver lantern');
  await page.locator('#previous-event').click();assert.equal(await field('health').inputValue(),'12');
  await page.locator('[data-event="6"]').click();await field('inventory').fill('Later decision');await page.locator('#review-button').click();await page.locator('#review-form button[type=submit]').click();
  await page.locator('[data-event="3"]').click();await field('inventory').fill('Earlier decision');await page.locator('#review-button').click();await page.locator('#review-form button[type=submit]').click();
  await page.locator('[data-event="6"]').click();assert.equal(await field('inventory').inputValue(),'Later decision');
  await field('health').fill('99');await page.locator('#next-event').click();assert.equal(await page.locator('#leave-dialog').evaluate(e=>e.open),true);await page.locator('#stay').click();assert.equal(await field('health').inputValue(),'99');
  await page.locator('#next-event').click();await page.locator('#discard').click();assert.equal(await field('health').inputValue(),'');
  await page.reload();await field('health').waitFor();await page.locator('[data-event="6"]').click();assert.equal(await field('inventory').inputValue(),'Later decision');
  await page.locator('#context-button').click();assert.ok((await page.locator('#context-description').textContent()).length>20);await page.keyboard.press('Escape');
  await page.locator('#about-button').click();await page.locator('#reset-button').click();await page.locator('#confirm-reset').click();assert.notEqual(await field('inventory').inputValue(),'Later decision');
  await page.locator('[data-event="4"]').click();
  for(const [name,width,height] of [['desktop',1440,1000],['tablet',760,900],['mobile',390,844]]){
   await page.setViewportSize({width,height});await page.screenshot({path:path.join(__dirname,name+'.png')});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),name+' horizontal overflow');
  }
  await page.evaluate(()=>{Storage.prototype.setItem=function(){throw new DOMException('Test quota exceeded','QuotaExceededError');};});
  await field('health').fill('8');await page.locator('#review-button').click();await page.locator('#review-form button[type=submit]').click();
  assert.match(await page.locator('#save-state').textContent(),/Session only/);
  assert.equal(await page.evaluate(()=>{const e=new Event('beforeunload',{cancelable:true});window.dispatchEvent(e);return e.defaultPrevented;}),true);
  await page.locator('#about-button').click();await page.locator('#reset-button').click();await page.locator('#confirm-reset').click();assert.match(await page.locator('#toast').textContent(),/session only/);
  assert.deepEqual(errors,[]);console.log('PASS: cast search; review/cancel/select all; per-field scope; later decisions; dirty navigation; reload/reset; storage failure status and unload guard; event context; three viewport layouts; no runtime errors.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
