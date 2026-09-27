#!/usr/bin/env node
// Avskärmat besökarprov (användning 3): en förstagångsbesökare (modell i en egen session) löser en uppgift i en riktig
// webbläsare genom Playwright MCP, utan brief, kod, facit eller tidigare kritik. Verktyget avskärmar uppgiften, bygger
// MCP-konfigurationen (isolerad kontext, tillåtna ursprung, spår och session sparade, inga bilder utanför verktyget),
// lägger skyddsundantaget i en init-page-fil (0600) som bara sätter headern mot målets ursprung, startar utföraren
// (claude eller codex) med bara webbläsarverktygen, och efterkontrollerar spåret: alla begärda ursprung ska ligga inom
// gränsen (MCP:s allowlist är ingen säkerhetsgräns; efterkontrollen är). Bedömningen av besöket görs separat
// (kontrollant), inte här.
//   node besok.mjs --adress URL --uppgift UPPGIFT.md --ut DIR [--undantag-fil F] [--utforare claude|codex] [--modell M] [--torr]
//   node besok.mjs --efterkontroll SPAR.zip --adress URL --ut DIR
import { args, origin, sha256, nu, lasUndantag, skriv } from './gemensamt.mjs';
import { readFileSync, writeFileSync, chmodSync, mkdirSync, existsSync, readdirSync } from 'node:fs';
import { spawnSync, execFileSync } from 'node:child_process';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HAR = dirname(fileURLToPath(import.meta.url));
const a = args(process.argv.slice(2));
const AVSKARMAT = /(?<![a-zåäö])(brief|briefen|facit|facitet|kritik|kritiken|research|källkod|source)(?![a-zåäö])|PROJECT-BRIEF|\bsrc\/|\.(tsx?|jsx?|css|json)\b|node_modules|verktyg\//i;

function efterkontroll(sparZip, tillatna) {
  // spåret är en zip; nätverksfilerna (*.network) är JSON-rader med request.url
  let text = '';
  try { text = execFileSync('unzip', ['-p', sparZip, '*.network'], { encoding: 'utf8', maxBuffer: 200 * 1024 * 1024 }); } catch (e) { return { lasbart: false, fel: 'kunde inte läsa spåret: ' + e.message.slice(0, 100) }; }
  const ursprung = new Set(); let antal = 0;
  for (const rad of text.split('\n')) {
    if (!rad.trim()) continue;
    try { const j = JSON.parse(rad); const u = j?.snapshot?.request?.url || j?.request?.url || j?.url; if (u) { antal++; try { ursprung.add(origin(u)); } catch {} } } catch {}
  }
  const utanfor = [...ursprung].filter(o => !tillatna.has(o) && !o.startsWith('data:'));
  return { lasbart: true, antal_forfragningar: antal, ursprung: [...ursprung], ursprung_utanfor: utanfor, inom_gransen: utanfor.length === 0 };
}

if (a.efterkontroll) {
  if (!a.adress || !a.ut) { console.error('användning: --efterkontroll SPAR.zip --adress URL --ut DIR'); process.exit(2); }
  const till = new Set([origin(a.adress), ...(a.tillat ? String(a.tillat).split(';').map(origin) : [])]);
  const e = efterkontroll(a.efterkontroll, till);
  skriv(a.ut, 'EFTERKONTROLL.json', { schema: 1, spar: a.efterkontroll, tillatna_ursprung: [...till], tid: nu(), ...e });
  console.log(JSON.stringify({ inom_gransen: e.inom_gransen, ursprung_utanfor: e.ursprung_utanfor }));
  process.exit(e.inom_gransen ? 0 : 1);
}

if (!a.adress || !a.uppgift || !a.ut) { console.error('användning: --adress URL --uppgift UPPGIFT.md --ut DIR [...]'); process.exit(2); }
const uppgift = readFileSync(a.uppgift, 'utf8');
const traff = uppgift.match(AVSKARMAT);
if (traff) { console.log(JSON.stringify({ vagrad: 'uppgiften är inte avskärmad: bär "' + traff[0] + '" (brief, facit, kritik, research, kod eller filnamn får inte nå besökaren)' })); process.exit(2); }
if (!/uppgift/i.test(uppgift) || uppgift.length > 2500) { console.log(JSON.stringify({ vagrad: 'uppgiften ska ha en rad "Uppgift:" och vara kort (högst 2500 tecken)' })); process.exit(2); }
mkdirSync(a.ut, { recursive: true });
const mal = origin(a.adress);
const tillat = [mal, ...(a.tillat ? String(a.tillat).split(';').filter(Boolean).map(origin) : [])];
const undantag = lasUndantag(a['undantag-fil']);
const mcpUt = resolve(a.ut, 'mcp-ut'); mkdirSync(mcpUt, { recursive: true });
const cli = resolve(HAR, 'node_modules/@playwright/mcp/cli.js');
const mcpArgs = [cli, '--isolated', '--headless', '--allowed-origins', tillat.join(';'), '--save-trace', '--save-session', '--output-dir', mcpUt, '--console-level', 'error', '--image-responses', 'allow', '--no-webmcp', '--block-service-workers', '--caps', 'vision', '--idle-timeout', '600000'];
let initFil = null;
if (undantag) {
  initFil = resolve(a.ut, 'init-undantag.ts');
  writeFileSync(initFil, `// privat: skyddsundantaget som header bara mot ${mal}; filen har rättighet 0600 och delas aldrig\nexport default async ({ page }) => {\n  await page.route('**/*', (route) => {\n    let o = null; try { o = new URL(route.request().url()).origin; } catch {}\n    if (o === ${JSON.stringify(mal)}) return route.continue({ headers: { ...route.request().headers(), 'x-vercel-protection-bypass': ${JSON.stringify(undantag)} } });\n    return route.continue();\n  });\n};\n`, { mode: 0o600 });
  chmodSync(initFil, 0o600);
  mcpArgs.push('--init-page', initFil);
}
const mcp = { mcpServers: { webblasare: { command: 'node', args: mcpArgs } } };
writeFileSync(join(a.ut, 'mcp.json'), JSON.stringify(mcp, null, 1) + '\n');
const prompt = `Du är en förstagångsbesökare på en webbplats. Du har bara webbläsarverktygen (webblasare). Du får inte veta något om vem som byggt sidan, inte läsa kod eller andra filer, och inte lämna webbplatsen ${mal}.
Regler: använd bara de testuppgifter som uppgiften ger (namn, e-post); skriv aldrig riktiga personuppgifter; köp inget, logga inte in, skicka inga meddelanden utöver det uppgiften säger; om något blockeras eller inte går, beskriv det i stället för att försöka runt.
Börja på ${a.adress}. Arbeta som en verklig besökare: läs, klicka, skriv, gå tillbaka om du fastnar. Ta en skärmbild när du tror att du är klar.
${uppgift.trim()}

När uppgiften är löst eller omöjlig: svara med exakt ett JSON-objekt {"utfall": "lost" | "omojlig" | "avbruten", "steg": [korta steg i ordning], "hinder": [vad som var svårt eller gick fel], "sista_adress": "url", "tid_sek": tal} och inget mer.
`;
writeFileSync(join(a.ut, 'BESOKARE.md'), prompt);
const rapport = { schema: 1, verktyg: 'besok', adress: a.adress, tillatna_ursprung: tillat, uppgift_sha256: sha256(Buffer.from(uppgift)), utforare: a.utforare || 'claude', modell: a.modell || null, torr: !!a.torr, undantag: !!undantag, tid: nu(), mcp: 'mcp.json', prompt: 'BESOKARE.md', svar: null, efterkontroll: null,
  not: 'avskärmad besökare: uppgiften utan brief, kod, facit eller kritik; MCP:s allowlist är ingen säkerhetsgräns — efterkontrollen av spåret är; bedömningen görs av kontrollanten separat; en modellbaserad besökare är inte en människa' };
if (!a.torr) {
  const ut = a.utforare || 'claude';
  let res;
  if (ut === 'claude') {
    const env = { PATH: process.env.PATH, HOME: process.env.HOME, LANG: 'sv_SE.UTF-8', TMPDIR: process.env.TMPDIR || '/tmp' };
    res = spawnSync('claude', ['-p', '--output-format', 'json', '--mcp-config', join(a.ut, 'mcp.json'), '--allowedTools', 'mcp__webblasare__*', '--setting-sources', 'user', '--max-turns', '60', ...(a.modell ? ['--model', a.modell] : [])], { input: prompt, encoding: 'utf8', env, cwd: a.ut, maxBuffer: 50 * 1024 * 1024, timeout: 25 * 60 * 1000 });
  } else {
    const cfg = ['-c', 'mcp_servers.webblasare.command="node"', '-c', 'mcp_servers.webblasare.args=' + JSON.stringify(mcpArgs)];
    res = spawnSync('codex', ['exec', '--sandbox', 'read-only', ...cfg, ...(a.modell ? ['--model', a.modell] : []), '-'], { input: prompt, encoding: 'utf8', cwd: a.ut, maxBuffer: 50 * 1024 * 1024, timeout: 25 * 60 * 1000 });
  }
  writeFileSync(join(a.ut, 'BESOK-stdout.txt'), (res.stdout || '') + '\n--- stderr ---\n' + (res.stderr || '').slice(-4000));
  rapport.utforare_status = res.status; rapport.svar_rad = (res.stdout || '').trim().slice(-6000);
  try { const j = JSON.parse(res.stdout); rapport.svar = j; const inre = typeof j.result === 'string' ? j.result.match(/\{[\s\S]*\}/) : null; rapport.besok = inre ? JSON.parse(inre[0]) : null; } catch { rapport.besok = null; }
  const spar = existsSync(mcpUt) ? readdirSync(mcpUt).filter(f => f.endsWith('.zip') || f.includes('trace')).map(f => join(mcpUt, f)) : [];
  rapport.spar = spar;
  const till = new Set(tillat);
  rapport.efterkontroll = spar.length ? spar.map(s => ({ spar: s, ...efterkontroll(s, till) })) : [{ lasbart: false, fel: 'inget spår sparat' }];
  rapport.inom_gransen = rapport.efterkontroll.every(e => e.inom_gransen === true);
}
skriv(a.ut, 'BESOK.json', rapport);
console.log(JSON.stringify({ ut: a.ut, torr: rapport.torr, utforare: rapport.utforare, inom_gransen: rapport.inom_gransen ?? null }));
