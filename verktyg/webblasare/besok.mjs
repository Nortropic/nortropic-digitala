#!/usr/bin/env node
// Avskärmat besökarprov (användning 3): en förstagångsbesökare (modell i en egen session) löser en uppgift i en riktig
// webbläsare genom Playwright MCP, utan brief, kod, facit eller tidigare kritik. Verktyget avskärmar uppgiften, bygger
// MCP-konfigurationen (isolerad kontext, tillåtna ursprung, spår och session sparade, inga bilder utanför verktyget),
// verkställer gränsen i webbläsaren genom en init-page-fil (Playwright MCP:s --init-page): en route-hanterare på
// kontexten avbryter varje förfrågan utanför tillåtna ursprung, loggar alla förfrågningar (redigerade) till natverk.jsonl
// och sätter skyddsundantaget bara mot målets ursprung (då är filen privat, 0600, utanför fallet). Utföraren (claude
// eller codex) startas med bara webbläsarverktygen i en tom arbetskatalog. Efterkontrollen läser natverk.jsonl: alla
// begärda ursprung ska ligga inom gränsen och inga blockeringar får ha skett tyst (MCP:s egen allowlist är ingen
// säkerhetsgräns; route-hanteraren och loggen är). Bedömningen av besöket görs separat (kontrollant), inte här.
//   node besok.mjs --adress URL --uppgift UPPGIFT.md --ut DIR [--undantag-fil F] [--utforare claude|codex] [--modell M] [--torr]
//   node besok.mjs --efterkontroll NATVERK.jsonl --adress URL --ut DIR
//   node besok.mjs --qa --adress URL --ut DIR [--undantag-fil F]      # bara mcp.json för en sessions fria QA (ingen avskärmning, ingen uppgift)
import { args, origin, sha256, nu, lasUndantag, skriv } from './gemensamt.mjs';
import { readFileSync, writeFileSync, chmodSync, mkdirSync, existsSync, readdirSync, mkdtempSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { homedir, tmpdir } from 'node:os';
import { spawnSync, execFileSync } from 'node:child_process';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HAR = dirname(fileURLToPath(import.meta.url));
const arKorningsfil = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
const a = arKorningsfil ? args(process.argv.slice(2)) : { _: [] };
const AVSKARMAT = /(?<![a-zåäö])(brief|briefen|facit|facitet|kritik|kritiken|research|källkod|source)(?![a-zåäö])|PROJECT-BRIEF|\bsrc\/|\.(tsx?|jsx?|css|json)\b|node_modules|verktyg\//i;

function efterkontroll(loggFil, tillatna) {
  // natverk.jsonl skrivs av init-page-hanteraren: en JSON-rad per förfrågan {tid, metod, url (redigerad), ursprung, blockerad}
  let text = '';
  try { text = readFileSync(loggFil, 'utf8'); } catch (e) { return { lasbart: false, fel: 'kunde inte läsa nätverksloggen: ' + e.message.slice(0, 100) }; }
  const ursprung = new Set(); let antal = 0; let blockerade = 0; const utanfor = new Set();
  for (const rad of text.split('\n')) {
    if (!rad.trim()) continue;
    try { const j = JSON.parse(rad); antal++; if (j.ursprung) ursprung.add(j.ursprung); if (j.blockerad) { blockerade++; utanfor.add(j.ursprung); } else if (j.ursprung && !tillatna.has(j.ursprung)) utanfor.add(j.ursprung); } catch {}
  }
  return { lasbart: true, antal_forfragningar: antal, blockerade, ursprung: [...ursprung], ursprung_utanfor: [...utanfor], inom_gransen: utanfor.size === 0 };
}

export function initFilText(mal, tillat, loggFil, undantag) {
  // Körs av Playwright MCP på varje sida (--init-page). En hanterare per kontext: gräns, logg, undantag bara mot målet.
  return `// Digitalas gräns för besökarprovet${undantag ? ' — PRIVAT: bär skyddsundantaget (0600), delas aldrig' : ''}
import { appendFileSync } from 'node:fs';
const TILLATNA = new Set(${JSON.stringify(tillat)});
const MAL = ${JSON.stringify(mal)};
const LOGG = ${JSON.stringify(loggFil)};
const HEMLIGA = /^(x-vercel-protection-bypass|x-vercel-set-bypass-cookie|token|key|api_key|apikey|secret|password)$/i;
function redigera(u) { try { const x = new URL(u); for (const k of [...x.searchParams.keys()]) if (HEMLIGA.test(k)) x.searchParams.set(k, 'REDIGERAT'); return x.toString(); } catch { return u; } }
export default async ({ page }) => {
  const ctx = page.context();
  if (ctx.__nortropicGrans) return;
  ctx.__nortropicGrans = true;
  await ctx.route('**/*', async (route) => {
    const req = route.request(); const u = req.url();
    if (u.startsWith('data:') || u.startsWith('blob:') || u.startsWith('about:')) return route.continue();
    let o = null; try { o = new URL(u).origin; } catch { return route.abort('blockedbyclient'); }
    const ok = TILLATNA.has(o);
    try { appendFileSync(LOGG, JSON.stringify({ tid: new Date().toISOString(), metod: req.method(), url: redigera(u), ursprung: o, typ: req.resourceType(), blockerad: !ok }) + '\\n'); } catch {}
    if (!ok) return route.abort('blockedbyclient');
    const headers = { ...req.headers() };${undantag ? `
    if (o === MAL) headers['x-vercel-protection-bypass'] = ${JSON.stringify(undantag)};` : ''}
    return route.continue({ headers });
  });
};
`;
}

if (arKorningsfil && a.efterkontroll) {
  if (!a.adress || !a.ut) { console.error('användning: --efterkontroll NATVERK.jsonl --adress URL --ut DIR'); process.exit(2); }
  const till = new Set([origin(a.adress), ...(a.tillat ? String(a.tillat).split(';').map(origin) : [])]);
  const e = efterkontroll(a.efterkontroll, till);
  skriv(a.ut, 'EFTERKONTROLL.json', { schema: 1, logg: a.efterkontroll, tillatna_ursprung: [...till], tid: nu(), ...e });
  console.log(JSON.stringify({ inom_gransen: e.inom_gransen, ursprung_utanfor: e.ursprung_utanfor }));
  process.exit(e.inom_gransen ? 0 : 1);
}

const qaLage = !!a.qa;
if (arKorningsfil && (!a.adress || !a.ut || (!qaLage && !a.uppgift))) { console.error('användning: --adress URL --uppgift UPPGIFT.md --ut DIR [...] eller --qa --adress URL --ut DIR'); process.exit(2); }
if (!arKorningsfil) { /* importerad som modul (prova_init.mjs): bara initFilText exporteras */ }
const uppgift = !arKorningsfil ? '' : (qaLage ? '' : readFileSync(a.uppgift, 'utf8'));
if (arKorningsfil) {
if (!qaLage) {
  const traff = uppgift.match(AVSKARMAT);
  if (traff) { console.log(JSON.stringify({ vagrad: 'uppgiften är inte avskärmad: bär "' + traff[0] + '" (brief, facit, kritik, research, kod eller filnamn får inte nå besökaren)' })); process.exit(2); }
  if (!/uppgift/i.test(uppgift) || uppgift.length > 2500) { console.log(JSON.stringify({ vagrad: 'uppgiften ska ha en rad "Uppgift:" och vara kort (högst 2500 tecken)' })); process.exit(2); }
}
mkdirSync(a.ut, { recursive: true });
const mal = origin(a.adress);
const tillat = [mal, ...(a.tillat ? String(a.tillat).split(';').filter(Boolean).map(origin) : [])];
const undantag = lasUndantag(a['undantag-fil']);
const mcpUt = resolve(a.ut, 'mcp-ut'); mkdirSync(mcpUt, { recursive: true });
const cli = resolve(HAR, 'node_modules/@playwright/mcp/cli.js');
const loggFil = join(mcpUt, 'natverk.jsonl');
const mcpArgs = [cli, '--isolated', '--headless', '--allowed-origins', tillat.join(';'), '--save-session', '--output-dir', mcpUt, '--console-level', 'error', '--image-responses', 'allow', '--no-webmcp', '--block-service-workers', '--caps', 'vision', '--idle-timeout', '600000'];
let initFil; let initKatalog = null;
if (undantag) {
  // hemligheten ligger aldrig i fallkatalogen: egen katalog 0700 under ~/.nortropic-hemligheter/webblasare-init/, fil 0600
  mkdirSync(join(homedir(), '.nortropic-hemligheter', 'webblasare-init'), { recursive: true, mode: 0o700 });
  initKatalog = mkdtempSync(join(homedir(), '.nortropic-hemligheter', 'webblasare-init', 'init-'));
  chmodSync(initKatalog, 0o700);
  initFil = join(initKatalog, 'init-grans-undantag.ts');
  writeFileSync(initFil, initFilText(mal, tillat, loggFil, undantag), { mode: 0o600 }); chmodSync(initFil, 0o600);
} else {
  initFil = join(a.ut, 'init-grans.ts');
  writeFileSync(initFil, initFilText(mal, tillat, loggFil, null));
}
mcpArgs.push('--init-page', initFil);
const mcp = { mcpServers: { webblasare: { command: 'node', args: mcpArgs } } };
writeFileSync(join(a.ut, 'mcp.json'), JSON.stringify(mcp, null, 1) + '\n');
const prompt = `Du är en förstagångsbesökare på en webbplats. Du har bara webbläsarverktygen (webblasare). Du får inte veta något om vem som byggt sidan, inte läsa kod eller andra filer, och inte lämna webbplatsen ${mal}.
Regler: använd bara de testuppgifter som uppgiften ger (namn, e-post); skriv aldrig riktiga personuppgifter; köp inget, logga inte in, skicka inga meddelanden utöver det uppgiften säger; om något blockeras eller inte går, beskriv det i stället för att försöka runt.
Börja på ${a.adress}. Arbeta som en verklig besökare: läs, klicka, skriv, gå tillbaka om du fastnar. Ta en skärmbild när du tror att du är klar.
${uppgift.trim()}

När uppgiften är löst eller omöjlig: svara med exakt ett JSON-objekt {"utfall": "lost" | "omojlig" | "avbruten", "steg": [korta steg i ordning], "hinder": [vad som var svårt eller gick fel], "sista_adress": "url", "tid_sek": tal} och inget mer.
`;
if (!qaLage) writeFileSync(join(a.ut, 'BESOKARE.md'), prompt);
const rapport = { schema: 1, verktyg: 'besok', lage: qaLage ? 'qa' : 'besok', adress: a.adress, tillatna_ursprung: tillat, uppgift_sha256: qaLage ? null : sha256(Buffer.from(uppgift)), utforare: a.utforare || 'claude', modell: a.modell || null, torr: !!a.torr || qaLage, undantag: !!undantag, spar_privat: !!undantag, init_katalog: initKatalog ? '(privat, utanför fallet)' : null, tid: nu(), mcp: 'mcp.json', prompt: qaLage ? null : 'BESOKARE.md', svar: null, efterkontroll: null,
  not: 'avskärmad besökare: uppgiften utan brief, kod, facit eller kritik; MCP:s allowlist är ingen säkerhetsgräns — efterkontrollen av spåret är; bedömningen görs av kontrollanten separat; en modellbaserad besökare är inte en människa' };
if (!a.torr && !qaLage) {
  const ut = a.utforare || 'claude';
  // tom arbetskatalog för utföraren: varken fallet, initfilen eller repot är läsbara som cwd
  const arbets = mkdtempSync(join(tmpdir(), 'besok-'));
  let res;
  if (ut === 'claude') {
    // samma rena miljö som Runtimes Claude-profil (PATH, HOME, USER, LOGNAME, LANG, TMPDIR): inloggningen bor i nyckelringen, inga nycklar ärvs
    const env = { PATH: process.env.PATH, HOME: process.env.HOME, USER: process.env.USER, LOGNAME: process.env.LOGNAME, LANG: 'sv_SE.UTF-8', TMPDIR: process.env.TMPDIR || '/tmp' };
    res = spawnSync('claude', ['-p', '--output-format', 'json', '--mcp-config', join(a.ut, 'mcp.json'), '--strict-mcp-config', '--allowedTools', 'mcp__webblasare__*', '--disallowedTools', 'Bash,Read,Write,Edit,MultiEdit,NotebookEdit,Glob,Grep,LS,WebFetch,WebSearch,Agent,Task,TodoWrite,Skill', '--setting-sources', 'user', '--max-turns', '60', ...(a.modell ? ['--model', a.modell] : [])], { input: prompt, encoding: 'utf8', env, cwd: arbets, maxBuffer: 50 * 1024 * 1024, timeout: 25 * 60 * 1000 });
  } else {
    const cfg = ['-c', 'mcp_servers.webblasare.command="node"', '-c', 'mcp_servers.webblasare.args=' + JSON.stringify(mcpArgs)];
    res = spawnSync('codex', ['exec', '--sandbox', 'read-only', ...cfg, ...(a.modell ? ['--model', a.modell] : []), '-'], { input: prompt, encoding: 'utf8', cwd: arbets, maxBuffer: 50 * 1024 * 1024, timeout: 25 * 60 * 1000 });
  }
  rapport.utforarargument = ut === 'claude' ? ['--strict-mcp-config', '--allowedTools mcp__webblasare__*', '--disallowedTools (fil-, skal-, sök- och agentverktyg)', 'cwd: tom katalog'] : ['codex exec --sandbox read-only', 'cwd: tom katalog'];
  writeFileSync(join(a.ut, 'BESOK-stdout.txt'), (res.stdout || '') + '\n--- stderr ---\n' + (res.stderr || '').slice(-4000));
  rapport.utforare_status = res.status; rapport.svar_rad = (res.stdout || '').trim().slice(-6000);
  try { const j = JSON.parse(res.stdout); rapport.svar = j; const inre = typeof j.result === 'string' ? j.result.match(/\{[\s\S]*\}/) : null; rapport.besok = inre ? JSON.parse(inre[0]) : null; } catch { rapport.besok = null; }
  rapport.session = existsSync(mcpUt) ? readdirSync(mcpUt) : [];
  rapport.natverkslogg = loggFil;
  rapport.efterkontroll = efterkontroll(loggFil, new Set(tillat));
  rapport.inom_gransen = rapport.efterkontroll.inom_gransen === true;
}
skriv(a.ut, 'BESOK.json', rapport);
console.log(JSON.stringify({ ut: a.ut, torr: rapport.torr, utforare: rapport.utforare, inom_gransen: rapport.inom_gransen ?? null }));
}
