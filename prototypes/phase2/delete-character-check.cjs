const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765');await page.locator('[data-field=name]').waitFor();
  assert.equal(await page.locator('[data-delete-character]').count(),2);
  const search=await page.locator('#cast-search').boundingBox(),create=await page.locator('#new-character-button').boundingBox();assert.ok(create.y>search.y);
  await page.locator('[data-field=health]').fill('19');
  await page.locator('.sheet-actions [data-delete-character]').click();await page.locator('#cancel-delete-character').click();
  assert.equal(await page.locator('[data-field=health]').inputValue(),'19');
  await page.locator('.workspace-toolbar [data-delete-character]').click();await page.locator('#confirm-delete-character').click();
  assert.equal(await page.locator('.cast-row').count(),17);
  await page.reload();await page.locator('[data-field=name]').waitFor();assert.equal(await page.locator('.cast-row').count(),17);
  await page.locator('.cast-row').filter({hasText:'Thorne Blackwood'}).click();
  assert.equal(await page.locator('.connection-person').filter({hasText:'Mira Vale'}).count(),0);
  await page.locator('[data-event="0"]').click();assert.equal(await page.locator('.connection-person').filter({hasText:'Mira Vale'}).count(),0);
  // The final deletion must leave a usable empty state and allow creation.
  for(let remaining=17;remaining>0;remaining--){await page.locator('.workspace-toolbar [data-delete-character]').click();await page.locator('#confirm-delete-character').click();}
  assert.equal(await page.locator('.cast-row').count(),0);assert.ok(await page.locator('.empty-profile').isVisible());
  await page.reload();await page.locator('.empty-profile').waitFor();
  await page.locator('#new-character-button').click();await page.locator('#new-character-name').fill('New beginning');await page.locator('#new-character-form button[type=submit]').click();
  assert.equal(await page.locator('[data-field=name]').inputValue(),'New beginning');
  await page.reload();await page.locator('[data-field=name]').waitFor();assert.equal(await page.locator('.cast-row').count(),1);
  await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('.workspace-toolbar [data-delete-character]').click();await page.locator('#confirm-delete-character').click();assert.ok(await page.locator('.empty-profile').isVisible());
  await page.locator('#about-button').click();await page.locator('#reset-button').click();await page.locator('#confirm-reset').click();assert.equal(await page.locator('.cast-row').count(),18);
  assert.deepEqual(errors,[]);console.log('PASS: button placement; cancel preserves edits; deletion/reload; connections removed across events; empty cast; ID-safe recreation; mobile; reset.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
