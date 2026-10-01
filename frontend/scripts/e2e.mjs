// Real browser + loopback HTTP. The backend fixture lives exclusively under tmp.
import { chromium } from 'playwright'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import fs from 'node:fs/promises'
import assert from 'node:assert/strict'
import crypto from 'node:crypto'
const root = fileURLToPath(new URL('../../', import.meta.url))
const workspace = path.join(root,'tmp',`browser-${crypto.randomUUID()}`)
const output = path.resolve(process.env.LEGALMIND_E2E_OUTPUT || path.join(workspace,'report.json'))
const relativeOutput = path.relative(root, output)
if (relativeOutput.startsWith('..') || path.isAbsolute(relativeOutput)) throw new Error('E2E reports must remain inside the project workspace.')
try { await fs.access(output); throw new Error('Choose a new E2E report path; prior runs must be preserved.') }
catch(error) { if(error.code !== 'ENOENT') throw error }
const backendPort = 8011, frontendPort = 5173
const processes = [], results = [], logs = []
let browser
const report = { scope:'isolated_browser_e2e', workspace, real_model_calls:0, real_redis:false, embedding:'deterministic_hash', tests:results }
async function waitFor(url) {
  for (let i=0;i<150;i++) { try { if ((await fetch(url)).ok) return } catch {} await new Promise(r=>setTimeout(r,200)) }
  throw new Error(`Service did not start: ${url}`)
}
function start(exe,args,cwd,env={}) {
  const child=spawn(exe,args,{cwd,env:{...process.env,...env},windowsHide:true,stdio:['ignore','pipe','pipe']})
  child.stdout.on('data',b=>logs.push(b.toString()));child.stderr.on('data',b=>logs.push(b.toString()));processes.push(child);return child
}
async function check(name, run) {
  const started=Date.now()
  try { await run(); results.push({name,passed:true,elapsed_ms:Date.now()-started}); console.log(`PASS ${name}`) }
  catch(e) { results.push({name,passed:false,error:e.message}); throw e }
}
async function ready(page) { await page.locator('h1#chat-title').waitFor() }
async function send(page,text) { await page.locator('#legal-question').fill(text); await page.getByRole('button',{name:'发送咨询',exact:true}).click() }
async function completed(page) { await page.locator('section[aria-label="依据与提示"]').last().waitFor({timeout:10000}) }
try {
  // Refuse to reuse an existing listener, which could be the user's normal application.
  for (const port of [backendPort,frontendPort]) { let occupied=false;try{await fetch(`http://127.0.0.1:${port}`);occupied=true}catch{}if(occupied)throw new Error(`Port ${port} is occupied; stop that service or change the fixture ports.`) }
  const python=process.env.LEGALMIND_E2E_PYTHON || path.join(root,'backend','.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python')
  start(python,['-m','scripts.serve_e2e','--workspace',workspace,'--port',String(backendPort)],path.join(root,'backend'))
  start(process.execPath,[path.join(root,'frontend','node_modules','vite','bin','vite.js'),'--port',String(frontendPort)],path.join(root,'frontend'),{LEGALMIND_DEV_API_TARGET:`http://127.0.0.1:${backendPort}`})
  await waitFor(`http://127.0.0.1:${backendPort}/api/v1/health`);await waitFor(`http://127.0.0.1:${frontendPort}`)
  browser=await chromium.launch({headless:true,...(process.env.LEGALMIND_E2E_BROWSER_CHANNEL ? {channel:process.env.LEGALMIND_E2E_BROWSER_CHANNEL} : {})})
  const context=await browser.newContext({acceptDownloads:true,reducedMotion:'reduce'})
  const page=await context.newPage(), base=`http://127.0.0.1:${frontendPort}`
  const suffix=crypto.randomBytes(4).toString('hex'), password=crypto.randomBytes(16).toString('hex')
  await check('normal: register, SSE, source, reload, follow-up',async()=>{
    await page.goto(`${base}/auth?mode=register`);await page.locator('#username').fill(`browser_${suffix}`);await page.locator('#email').fill(`browser_${suffix}@example.com`);await page.locator('#password').fill(password);await page.getByRole('button',{name:'注册并登录',exact:true}).click();await ready(page)
    await send(page,'公司拖欠工资，如何整理已有资料？');await completed(page)
    assert.match(await page.locator('section[aria-label="依据与提示"]').innerText(),/演示/)
    await page.reload();await ready(page);await page.getByText('可按演示场景整理已有材料[S1]。',{exact:false}).waitFor()
    await send(page,'还有哪些材料需要核对？');await completed(page)
  })
  await check('cases: search, domain filter, detail',async()=>{
    await page.goto(`${base}/cases`);await page.getByLabel('关键事实').fill('劳动报酬');await page.getByLabel('领域',{exact:true}).selectOption('labor_dispute');await page.getByRole('button',{name:'搜索案例'}).click();await page.locator('article h2 a').first().waitFor();await page.locator('article h2 a').first().click();await page.getByRole('heading',{name:'基本事实'}).waitFor();assert.match(await page.locator('main').innerText(),/不是真实判例/)
  })
  await check('empty results: no fabricated cases',async()=>{
    await page.goto(`${base}/cases`);await page.getByLabel('关键事实').fill('无匹配演示');await page.getByRole('button',{name:'搜索案例'}).click();await page.getByText('没有匹配的案例，请调整关键词或领域。').waitFor()
  })
  await check('documents: three templates, review, copy, MD and TXT',async()=>{
    await context.grantPermissions(['clipboard-read','clipboard-write'])
    await page.goto(`${base}/documents`)
    await page.getByLabel('文书类型').waitFor()
    for (const kind of ['civil_complaint','civil_defense','general_contract']) {
      await page.getByLabel('文书类型').selectOption(kind)
      for (const textarea of await page.locator('fieldset textarea[required]').all()) await textarea.fill('用户提供的演示内容')
      await page.getByRole('button',{name:'核对摘要',exact:true}).click()
      const generated=page.waitForResponse(r=>r.url().endsWith('/documents/generate') && r.status()===200)
      await page.getByRole('button',{name:'确认摘要并生成草稿',exact:true}).click()
      const generatedBody=await (await generated).json()
      await page.locator(`[data-document-id="${generatedBody.data.document_id}"]`).waitFor()
      await page.locator('[aria-label="文书草稿"]').waitFor()
      await page.getByRole('button',{name:'复制草稿',exact:true}).click();assert.match(await page.evaluate(()=>navigator.clipboard.readText()),/草稿/)
      for (const format of ['Markdown','TXT']) {
        const download=page.waitForEvent('download');await page.getByRole('button',{name:`下载 ${format}`,exact:true}).click();const file=await download;const destination=path.join(workspace,file.suggestedFilename());await file.saveAs(destination);assert.match(await fs.readFile(destination,'utf8'),/用户提供的演示内容/)
      }
    }
  })
  await check('timeout: unfinished content and safe retry',async()=>{
    await page.goto(`${base}/chat`);await ready(page);await page.getByRole('button',{name:'新建咨询',exact:true}).first().click();await send(page,'超时演示，整理劳动资料');await page.locator('[data-testid="chat-error"]').waitFor();assert.match(await page.locator('main').innerText(),/未完成/);assert.equal(await page.locator('section[aria-label="依据与提示"]').count(),0)
  })
  await check('disconnect: stop and recover without committing partial content',async()=>{
    await page.getByRole('button',{name:'新建咨询',exact:true}).first().click();await send(page,'断流演示，整理劳动资料');await page.getByText('可按演示场景整理已有材料[S1]。',{exact:false}).waitFor();await page.getByRole('button',{name:'停止生成',exact:true}).click();await page.locator('[data-testid="chat-error"]').waitFor();assert.equal(await page.locator('section[aria-label="依据与提示"]').count(),0)
  })
  await check('security: cross-user history and document access denied',async()=>{
    const ownerToken=await page.evaluate(()=>sessionStorage.getItem('legalmind_access_token'))
    const headers={Authorization:`Bearer ${ownerToken}`}
    const list=await fetch(`http://127.0.0.1:${backendPort}/api/v1/chat/conversations`,{headers}).then(r=>r.json())
    assert.ok(list.data.items.length)
    const other=`other_${suffix}`
    await fetch(`http://127.0.0.1:${backendPort}/api/v1/auth/register`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:other,email:`${other}@example.com`,password})})
    const login=await fetch(`http://127.0.0.1:${backendPort}/api/v1/auth/login`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({login:other,password})}).then(r=>r.json())
    const denied=await fetch(`http://127.0.0.1:${backendPort}/api/v1/chat/history/${list.data.items[0].session_id}`,{headers:{Authorization:`Bearer ${login.data.access_token}`}})
    assert.equal(denied.status,404)
    const files=await fs.readdir(workspace);const file=files.find(f=>f.startsWith('legalmind-')&&f.endsWith('.md'));assert.ok(file)
    const documentId=file.slice(10,-3)
    assert.equal((await fetch(`http://127.0.0.1:${backendPort}/api/v1/documents/${documentId}/download`,{headers:{Authorization:`Bearer ${login.data.access_token}`}})).status,404)
  })
  await check('invalid token: clears session and prompts login',async()=>{
    await page.evaluate(()=>sessionStorage.setItem('legalmind_access_token','invalid-token'));await page.reload();await page.waitForURL('**/auth?**');assert.equal(await page.evaluate(()=>sessionStorage.getItem('legalmind_access_token')),null)
  })
  await check('responsive: no horizontal overflow at 320px and 390px',async()=>{
    for(const width of [320,390]) {
      await page.setViewportSize({width,height:844});await page.goto(base);await page.getByRole('heading',{name:'从你要完成的事情开始'}).waitFor()
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth),`Overflow at ${width}px`)
      await page.screenshot({path:path.join(workspace,`mobile-${width}.png`),fullPage:true,animations:'disabled'})
    }
  })
  report.passed=results.every(r=>r.passed)
} catch(error) { report.passed=false;report.failure=error.message;console.error(error.message);process.exitCode=1 }
finally {
  await browser?.close()
  for(const child of processes.reverse()) { child.kill(); }
  await fs.mkdir(path.dirname(output),{recursive:true});await fs.writeFile(output,JSON.stringify(report,null,2),{flag:'wx'});await fs.writeFile(`${output}.runtime.log`,logs.join(''),{flag:'wx'});console.log(`Report: ${output}`)
}
