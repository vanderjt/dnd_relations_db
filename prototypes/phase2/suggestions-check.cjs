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
  await field('location').waitFor();
  assert.equal(await page.locator('[role=combobox]').count(),5);
  await field('location').focus();
  assert.equal(await field('location').getAttribute('aria-expanded'),'true');
  await field('location').press('Escape');
  await field('location').click();
  assert.equal(await field('location').getAttribute('aria-expanded'),'true');
  await field('location').press('Escape');
  await page.locator('[data-options-for=location]').click();
  assert.ok(await page.locator('[role=option]').count()>1);
  await field('location').fill('market');
  assert.ok((await page.locator('[role=option]').allTextContents()).every(v=>v.toLowerCase().includes('market')));
  await page.screenshot({path:path.join(__dirname,'searchable-location.png')});
  await field('location').press('ArrowDown');await field('location').press('Enter');
  assert.equal(await field('location').inputValue(),'Greyhaven Market');
  assert.equal(await field('location').getAttribute('aria-expanded'),'false');
  const custom='Moonlit Observatory';
  await field('location').fill(custom);
  await page.getByRole('option',{name:`Use “${custom}” (new)`,exact:true}).click();
  assert.equal(await field('location').inputValue(),custom);
  await page.locator('#review-button').click();await page.locator('#cancel-review').click();
  assert.equal(await field('location').inputValue(),custom);
  await page.locator('#review-button').click();await page.locator('[name=carry][value=location]').uncheck();await page.locator('#review-form button[type=submit]').click();
  await page.locator('#next-event').click();assert.notEqual(await field('location').inputValue(),custom);
  await page.reload();await field('location').waitFor();
  await page.locator('[data-options-for=location]').click();assert.equal(await page.getByRole('option',{name:custom,exact:true}).count(),1);
  await field('location').press('Escape');
  await field('location').fill('Temporary discarded place');
  await page.locator('#next-event').click();await page.locator('#discard').click();
  await page.locator('[data-options-for=location]').click();assert.equal(await page.getByRole('option',{name:'Temporary discarded place',exact:true}).count(),0);
  await field('location').fill(custom.toUpperCase());assert.equal(await page.locator('#field-options [role=option]').count(),1);
  await field('location').press('Escape');await field('location').press('Tab');assert.equal(await field('location').getAttribute('aria-expanded'),'false');
  for(const key of ['species','role','status','faction']) {
   await field(key).fill('Custom '+key);await field(key).press('ArrowDown');await field(key).press('Enter');
   assert.equal(await field(key).inputValue(),'Custom '+key);
  }
  await page.setViewportSize({width:390,height:844});
  await field('location').scrollIntoViewIfNeeded();await field('location').fill('Moon');
  const rect=await page.locator('.suggestion-panel').boundingBox();assert.ok(rect.x>=0&&rect.x+rect.width<=390&&rect.y>=0&&rect.y+rect.height<=844);
  assert.deepEqual(errors,[]);
  console.log('PASS: five pickers; filtering; keyboard and pointer selection; custom options; save/reload; event-only reuse; discarded drafts excluded; case deduplication; mobile popup bounds.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
