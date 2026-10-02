const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
const page=await browser.newPage({viewport:{width:1600,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8765/?v=15');await page.locator('[data-field=name]').waitFor();
await page.locator('[data-field=age]').fill('35');await page.locator('[data-page=world]').click();await page.locator('#leave-dialog').waitFor({state:'visible'});await page.locator('#discard').click();
await page.locator('#world-add').click();await page.locator('#world-entry-name').fill('Starfolk');await page.locator('#world-entry-description').fill('Readers of the night sky.');await page.locator('#world-entry-form [type=submit]').click();
assert.match(await page.locator('[data-world-entry=Starfolk]').textContent(),/Readers of the night sky/);
await page.reload();await page.locator('[data-page=world]').click();assert.equal(await page.locator('[data-world-entry=Starfolk]').count(),1);
await page.locator('[data-page=characters]').click();await page.locator('[data-options-for=species]').click();assert.ok(await page.getByRole('option',{name:'Starfolk',exact:true}).isVisible());await page.keyboard.press('Escape');
await page.locator('[data-page=world]').click();await page.locator('[data-world-category=language]').click();await page.locator('#world-add').click();await page.locator('#world-entry-name').fill('Old Harbor');await page.locator('#world-entry-form [type=submit]').click();await page.reload();await page.locator('[data-page=world]').click();await page.locator('[data-world-category=language]').click();assert.equal(await page.locator('[data-world-entry="Old Harbor"]').count(),1);
await page.locator('[data-world-category=species]').click();await page.screenshot({path:__dirname+'/world-desktop.png'});
await page.setViewportSize({width:390,height:844});await page.screenshot({path:__dirname+'/world-mobile.png'});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);console.log('World entries, persistence, profile options, navigation guard, and mobile checks passed.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
