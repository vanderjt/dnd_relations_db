const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765');await page.locator('[data-field=name]').waitFor();
 await page.locator('[data-page=relationships]').click();assert.equal(await page.locator('svg .graph-node').count(),18);
 await page.screenshot({path:path.join(__dirname,'graph-full.png')});
 await page.locator('#graph-scope-toggle').click();const direct=await page.locator('svg .graph-node').count();assert.ok(direct>1&&direct<18);
 await page.locator('#graph-scope-toggle').click();assert.equal(await page.locator('svg .graph-node').count(),18);
 await page.getByRole('button',{name:'Zoom to fit'}).click();assert.ok(Number((await page.locator('#relationship-graph').getAttribute('viewBox')).split(' ')[2])>500);
 await page.locator('svg [data-graph-edge="legacy-1"]').focus();await page.keyboard.press('Enter');
 await page.locator('#connection-type').selectOption('ally:forward');await page.locator('#connection-form button[type=submit]').click();
 assert.match(await page.locator('[data-edit-connection="legacy-1"]').textContent(),/Ally/);
 await page.locator('[data-page=characters]').click();assert.ok(await page.locator('#leave-dialog').evaluate(e=>e.open));await page.locator('#stay').click();
 await page.locator('#review-button').click();await page.locator('[name=carry][value="connection:legacy-1"]').uncheck();await page.locator('#review-form button[type=submit]').click();
 await page.locator('#next-event').click();assert.match(await page.locator('[data-edit-connection="legacy-1"]').textContent(),/Friend/);
 await page.locator('#previous-event').click();assert.match(await page.locator('[data-edit-connection="legacy-1"]').textContent(),/Ally/);
 await page.locator('[data-open-profile]').click();assert.equal(await page.locator('[data-field=name]').inputValue(),'Mira Vale');assert.match(await page.locator('[data-edit-connection="legacy-1"]').textContent(),/Ally/);
 await page.locator('.cast-row').filter({hasText:'Thorne Blackwood'}).click({button:'right'});await page.locator('#cast-direct').click();
 assert.equal(await page.locator('#graph-scope-toggle').getAttribute('aria-checked'),'true');assert.equal(await page.locator('#graph-character option:checked').textContent(),'Thorne Blackwood');
 await page.locator('[data-open-profile]').click();
 await page.locator('.cast-menu-button').first().click();await page.locator('#cast-open-profile').click();assert.equal(await page.locator('[data-field=name]').inputValue(),'Ada Moss');
 await page.locator('[data-page=relationships]').click();assert.equal(await page.locator('svg .graph-node').count(),18);
 await page.locator('#graph-character').selectOption({label:'Mira Vale'});await page.locator('#graph-scope-toggle').click();await page.screenshot({path:path.join(__dirname,'graph-direct.png')});
 for(const [width,height] of [[760,900],[390,844]]){await page.setViewportSize({width,height});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 await page.locator('[data-add-connection]').click();assert.ok(await page.locator('#connection-dialog').evaluate(e=>e.open));await page.keyboard.press('Escape');
 assert.deepEqual(errors,[]);console.log('PASS: full/direct graph; zoom/fit; keyboard edge editing; dirty-page guard; event-only review; profile consistency; right-click/menu shortcuts; graph selection; mobile.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
