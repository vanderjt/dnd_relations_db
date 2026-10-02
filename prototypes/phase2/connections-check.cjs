const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765');await page.locator('[data-field=name]').waitFor();
  const tag=page.locator('[data-edit-connection="legacy-1"]');
  await tag.click();await page.locator('#connection-type').selectOption('mentor:reverse');
  assert.match(await page.locator('#connection-preview').textContent(),/Thorne Blackwood mentors Mira Vale/);
  await page.locator('#connection-notes').fill('Teaching Mira swordplay.');
  await page.screenshot({path:path.join(__dirname,'connection-editor.png')});
  await page.locator('#connection-form button[type=submit]').click();assert.match(await tag.textContent(),/Student/);
  await page.locator('[data-field=health]').fill('13');
  await page.locator('#bottom-review-button').click();assert.equal(await page.locator('[name=carry]').count(),2);
  assert.match(await page.locator('#change-list').textContent(),/Connection with Thorne/);
  await page.locator('[name=carry][value="connection:legacy-1"]').uncheck();
  await page.locator('#review-form button[type=submit]').click();
  await page.locator('#next-event').click();assert.match(await tag.textContent(),/Friend/);
  await page.locator('#previous-event').click();assert.match(await tag.textContent(),/Student/);
  await page.locator('.connection-person').filter({hasText:'Thorne Blackwood'}).click();
  assert.match(await tag.textContent(),/Mentor/);
  await page.locator('[data-delete-connection="legacy-1"]').click();assert.equal(await tag.count(),0);
  await page.locator('[data-undo-connection="legacy-1"]').click();assert.match(await tag.textContent(),/Mentor/);
  await page.locator('[data-delete-connection="legacy-1"]').click();await page.locator('#bottom-review-button').click();
  await page.locator('#review-form button[type=submit]').click();assert.equal(await page.locator('[data-undo-connection]').count(),0);
  await page.reload();await page.locator('[data-field=name]').waitFor();assert.equal(await tag.count(),0);
  // Reconnect through the same legacy identity; no duplicate pair is introduced.
  await page.locator('[data-add-connection]').click();
  await page.locator('#connection-person').selectOption({label:'Thorne Blackwood'});
  await page.locator('#connection-type').selectOption('ally:forward');
  await page.locator('#connection-form button[type=submit]').click();
  await page.locator('#bottom-review-button').click();await page.locator('#review-form button[type=submit]').click();
  assert.match(await tag.textContent(),/Ally/);
  await page.locator('[data-add-connection]').click();assert.equal(await page.locator('#connection-person option').filter({hasText:'Thorne Blackwood'}).count(),0);
  await page.locator('#connection-person').selectOption({label:'Ada Moss'});
  await page.locator('#connection-form button[type=submit]').click();
  await page.locator('#next-event').click();assert.ok(await page.locator('#leave-dialog').evaluate(e=>e.open));
  await page.locator('#discard').click();assert.equal(await page.locator('.connection-person').filter({hasText:'Ada Moss'}).count(),0);
  await page.setViewportSize({width:390,height:844});await page.locator('[data-add-connection]').click();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.keyboard.press('Escape');
  assert.deepEqual(errors,[]);
  console.log('PASS: inverse tag edit; notes; mixed review; event-only scope; both profiles; delete/undo/save/reload; reconnect; duplicate prevention; discarded additions; mobile dialog.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
