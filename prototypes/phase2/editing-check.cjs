const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765');
  const field=k=>page.locator(`[data-field="${k}"]`);
  await field('health').waitFor();
  const original=await field('notes').inputValue();
  const shortHeight=await field('notes').evaluate(e=>e.offsetHeight);
  const paragraph='Mira follows the dockside fever through Greyhaven. She keeps detailed records of every patient and compares their symptoms with the shipments arriving at the market.';
  await field('notes').fill(Array(12).fill(paragraph).join('\n\n'));
  assert.equal(await page.locator('#state-notes').textContent(),'Unsaved');
  assert.ok(await field('notes').evaluate(e=>e.offsetHeight>100&&e.offsetHeight<=240&&e.scrollHeight>e.clientHeight));
  await field('notes').fill(original);
  assert.equal(await page.locator('#state-notes').textContent(),'');
  assert.equal(await page.locator('#review-button').isDisabled(),true);
  assert.equal(await field('notes').evaluate(e=>e.offsetHeight),shortHeight);
  await field('backstory').fill(paragraph+' '+paragraph);
  await field('notes').fill('Ask Elias about the ledger.\nCheck the market supply records.\nSpeak to Liora before the next council meeting.');
  await field('goals').fill('Find the source of the fever and protect the dock workers.');
  await field('traits').fill('Patient and observant, but impatient with political delays.');
  await field('health').fill('12');
  await field('inventory').fill('A silver lantern, a healer’s kit, and the shipping ledger.');
  await field('age').fill('32');
  await field('armor').fill('10');
  await field('mana').fill('8');
  await field('skills').fill('Herbal medicine; investigation; first aid; reading shipping records.');
  await page.locator('#sheet-scroll').evaluate(e=>{e.style.scrollBehavior='auto';e.scrollTop=0;});
  await page.screenshot({path:path.join(__dirname,'editing-desktop.png')});
  await field('backstory').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(__dirname,'editing-details.png')});
  await page.locator('#review-button').click();
  await page.locator('[name=carry][value=health]').uncheck();
  await page.locator('#cancel-review').click();
  assert.equal(await page.locator('#state-health').textContent(),'Unsaved');
  await page.locator('#review-button').click();
  await page.locator('[name=carry][value=health]').uncheck();
  await page.locator('#review-form button[type=submit]').click();
  assert.equal(await page.locator('#state-health').textContent(),'');
  assert.match(await field('health').locator('xpath=ancestor::label').textContent(),/This event only/);
  await page.setViewportSize({width:2247,height:1244});
  const boxes={};for(const key of ['species','role','age','status','location','faction'])boxes[key]=await field(key).boundingBox();
  for(const row of [['species','role','age'],['status','location','faction']])for(const key of row)assert.equal(boxes[key].y,boxes[row[0]].y,'Controls align despite mixed history badges');
  for(const [a,b] of [['species','status'],['role','location'],['age','faction']]){assert.equal(boxes[a].x,boxes[b].x);assert.equal(boxes[a].width,boxes[b].width);}
  assert.equal(await page.locator('.field-state').filter({hasText:/^Edit/}).count(),0);
  await page.locator('#sheet-scroll').evaluate(e=>{e.style.scrollBehavior='auto';e.scrollTop=0;});
  await page.screenshot({path:path.join(__dirname,'aligned-identity.png')});
  await page.locator('#next-event').click();
  assert.equal(await field('health').inputValue(),'');
  assert.match(await field('inventory').inputValue(),/silver lantern/);
  assert.match(await field('inventory').locator('xpath=ancestor::label').textContent(),/From event 5/);
  for(const theme of ['storybook','gothic','cyberpunk','noir','medieval']) {
   await page.locator('#theme-select').selectOption(theme);
   await page.waitForFunction(name=>document.querySelector('#theme-stylesheet').sheet?.href.split('?')[0].endsWith(`/themes/${name}.css`),theme);
   for(const [width,height] of [[1440,1000],[760,900],[390,844]]) {
    await page.setViewportSize({width,height});
    await field('backstory').scrollIntoViewIfNeeded();
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    assert.ok(await field('backstory').evaluate(e=>e.offsetHeight<=240));
   }
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: growing/shrinking long text; field change/revert cues; populated layout at three sizes in five themes; review cancellation; saved badges; mixed carry-forward workflow.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
