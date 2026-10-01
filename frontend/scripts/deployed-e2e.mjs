// Existing local Compose deployment; one authorized live consultation, no mock services.
import { chromium } from 'playwright'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import fs from 'node:fs/promises'
import path from 'node:path'
import crypto from 'node:crypto'
import assert from 'node:assert/strict'

const liveModel = process.argv.includes('--allow-real-model')
const storageOnly = process.argv.includes('--storage-only')
if (liveModel === storageOnly) throw new Error('Choose --allow-real-model or --storage-only explicitly.')
const root = fileURLToPath(new URL('../../', import.meta.url))
const base = process.env.LEGALMIND_DEPLOYED_URL || 'http://127.0.0.1:8080'
const url = new URL(base)
if (url.hostname !== '127.0.0.1' || url.protocol !== 'http:') throw new Error('Only the loopback acceptance deployment is allowed.')
const output = path.resolve(process.env.LEGALMIND_E2E_OUTPUT || path.join(root,'tmp',`deployed-browser-${crypto.randomUUID()}.json`))
const relative = path.relative(root, output)
if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('Report must stay inside the project.')
try { await fs.access(output); throw new Error('Choose a new report path.') } catch(error) { if(error.code !== 'ENOENT') throw error }
const report = { scope:'real_compose_browser_acceptance', real_redis:true, simulated_faults:false,
  live_model_requested:liveModel, legal_answer_quality_verified:false,
  consultation_requests:0, model_call_count:storageOnly ? 0 : null, tests:[], started_at:new Date().toISOString() }
const message = liveModel
  ? '我想了解以下一般规则：建立劳动关系应当订立书面劳动合同吗？不涉及具体事件。'
  : '取消任务'
const name = `browser_deploy_${crypto.randomBytes(6).toString('hex')}`, password = crypto.randomBytes(20).toString('hex')
let browser
async function check(name, run) {
  try { await run(); report.tests.push({name,passed:true}); console.log(`PASS ${name}`) }
  catch(error) { report.tests.push({name,passed:false,error:error.message}); throw error }
}
async function health() {
  for(let attempt=0;attempt<120;attempt++) {
    try { if((await fetch(`${base}/api/v1/health`)).ok) return } catch {}
    await new Promise(resolve=>setTimeout(resolve,500))
  }
  throw new Error('Deployment did not become healthy.')
}
try {
  await health()
  browser = await chromium.launch({headless:true,channel:process.env.LEGALMIND_E2E_BROWSER_CHANNEL || 'msedge'})
  const context = await browser.newContext({acceptDownloads:true,reducedMotion:'reduce'})
  const page = await context.newPage()
  let documentId, caseId
  await check(liveModel ? 'production browser: register, live SSE, source and history reload' : 'production browser: register, cancellation SSE and Redis history reload',async()=>{
    await page.goto(`${base}/auth?mode=register`)
    await page.locator('#username').fill(name);await page.locator('#email').fill(`${name}@example.com`);await page.locator('#password').fill(password)
    await page.getByRole('button',{name:'注册并登录',exact:true}).click();await page.locator('h1#chat-title').waitFor()
    await page.locator('#legal-question').fill(message)
    report.consultation_requests++
    await page.getByRole('button',{name:'发送咨询',exact:true}).click()
    if (liveModel) {
      await page.locator('section[aria-label="依据与提示"]').last().waitFor({timeout:80000})
      assert.match(await page.locator('main').innerText(),/参考材料|官方原文/)
    } else {
      await page.getByText('已取消当前任务。后续可重新提出问题或选择文书类型。',{exact:true}).waitFor()
    }
    await page.reload();await page.locator('h1#chat-title').waitFor()
    await page.getByText(message,{exact:true}).first().waitFor()
    if (liveModel) await page.locator('section[aria-label="依据与提示"]').last().waitFor()
    else await page.getByText('已取消当前任务。后续可重新提出问题或选择文书类型。',{exact:true}).waitFor()
  })
  await check('production browser: real case index and document confirmation/download',async()=>{
    await page.goto(`${base}/cases`);await page.getByLabel('关键事实').fill('劳动报酬');await page.getByRole('button',{name:'搜索案例'}).click()
    const link = page.locator('article h2 a').first();await link.waitFor();caseId = await link.getAttribute('href')
    await link.click();await page.getByRole('heading',{name:'基本事实'}).waitFor()
    await page.goto(`${base}/documents`)
    await page.locator('form textarea').first().waitFor()
    await page.locator('form textarea').evaluateAll(elements=>elements.forEach(element=>{
      element.value='部署浏览器验收提供的合成信息';element.dispatchEvent(new Event('input',{bubbles:true}))
    }))
    await page.getByRole('button',{name:'核对摘要',exact:true}).click()
    await page.getByRole('button',{name:'确认摘要并生成草稿',exact:true}).click()
    const actions=page.locator('[data-document-id]');await actions.waitFor();documentId=await actions.getAttribute('data-document-id')
    const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:'下载 Markdown',exact:true}).click()
    assert.match((await downloaded).suggestedFilename(),/\.md$/)
  })
  await check('restart: previous account, Redis history, document and index survive',async()=>{
    const docker=process.env.LEGALMIND_DOCKER_CLI
    if(!docker) throw new Error('LEGALMIND_DOCKER_CLI is required for the isolated restart check.')
    const command=spawnSync(docker,['compose','--env-file','deployment/.env','-f','compose.yml','-p','legalmind-clean-20261001','restart'],{cwd:root,windowsHide:true,encoding:'utf8'})
    if(command.status !== 0) throw new Error('Dedicated Compose restart failed.')
    await health()
    await page.goto(`${base}/chat`);await page.locator('h1#chat-title').waitFor()
    await page.getByText(message,{exact:true}).first().waitFor()
    if (liveModel) await page.locator('section[aria-label="依据与提示"]').last().waitFor()
    else await page.getByText('已取消当前任务。后续可重新提出问题或选择文书类型。',{exact:true}).waitFor()
    const token=await page.evaluate(()=>sessionStorage.getItem('legalmind_access_token'))
    const download=await context.request.get(`${base}/api/v1/documents/${documentId}/download?format=txt`,{headers:{Authorization:`Bearer ${token}`}})
    assert.equal(download.status(),200);assert.match(await download.text(),/部署浏览器验收/)
    await page.goto(`${base}${caseId}`);await page.getByRole('heading',{name:'基本事实'}).waitFor()
    await page.locator('header summary').click()
    await page.getByRole('button',{name:'退出登录',exact:true}).click()
    await page.goto(`${base}/auth`);await page.locator('#login').fill(name);await page.locator('#password').fill(password)
    await page.locator('form').getByRole('button',{name:'登录',exact:true}).click();await page.locator('h1#chat-title').waitFor()
  })
  await check('production browser: navigation and layout at 320px, 390px and 640px',async()=>{
    for(const width of [320,390,640]) {
      await page.setViewportSize({width,height:844});await page.goto(`${base}/chat`);await page.locator('h1#chat-title').waitFor()
      assert(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth))
      assert(await page.locator('header nav').evaluate(nav=>nav.getBoundingClientRect().right <= nav.nextElementSibling.getBoundingClientRect().left + 1),'Navigation must not overlap account controls.')
      await page.screenshot({path:`${output}.${width}.png`,fullPage:true,animations:'disabled'})
    }
  })
  report.passed=true
} catch(error) { report.passed=false;report.error=error.message;process.exitCode=1 }
finally {
  await browser?.close();report.completed_at=new Date().toISOString()
  await fs.mkdir(path.dirname(output),{recursive:true});await fs.writeFile(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'})
  console.log(`Report: ${output}`)
}
