#!/usr/bin/env node
// Private migration archive. Fresh browser contexts; GET/HEAD only, same origin, no logins.
import { args, oppna, origin, sha256, nu } from './gemensamt.mjs';
import { readFileSync, writeFileSync, mkdirSync, realpathSync, existsSync, chmodSync } from 'node:fs';
import { resolve, join, dirname, basename, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

process.umask(0o077);
const a = args(process.argv.slice(2));
const MAX_ADRESSER = 500, MAX_KARTOR = 20;
let out, report;
function inside(path, root) { return path === root || path.startsWith(root+sep); }
function address(value, base) {
  const u = new URL(value, base);
  if (u.username || u.password || !['https:', 'http:'].includes(u.protocol)) throw new Error('ogiltig publik http-adress');
  if (u.protocol === 'http:' && !(a['tillat-http'] && ['127.0.0.1', 'localhost', '[::1]'].includes(u.hostname))) throw new Error('https krävs; http bara för lokal fixtur');
  u.hash = ''; return u.href;
}
async function within(promise, ms=30000) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer=setTimeout(()=>reject(new Error('tidsgräns')), ms); })]); }
  finally { clearTimeout(timer); }
}
async function browser(base, extra={}) {
  const b = await oppna({ tillat: [origin(base)], mal: base, extra: { serviceWorkers: 'block', ...extra } });
  await b.ctx.route('**/*', route => {
    const request=route.request();
    if(['GET','HEAD'].includes(request.method()))return route.fallback();
    b.logg.blockerade.push({metod:request.method(),url:request.url(),skal:'bara GET/HEAD'});
    return route.abort();
  });
  await b.ctx.routeWebSocket('**/*', socket => {
    b.logg.blockerade.push({metod:'WebSocket',url:socket.url(),skal:'ingen WebSocket i arkivet'});
    return socket.close();
  });
  return b;
}
try {
  if (!a.adress || !a.kund || !a.ut || !a.intervju) throw new Error('--adress URL --kund KUNDMAPP --ut NY-KATALOG --intervju INTERVJU.json krävs');
  const base=address(a.adress), customer=realpathSync(a.kund), repo=realpathSync(fileURLToPath(new URL('../../', import.meta.url)));
  if (inside(customer, repo)) throw new Error('kundmappen får inte ligga i Digitalas repo');
  out=join(realpathSync(dirname(resolve(a.ut))), basename(a.ut));
  if (inside(out, repo)) throw new Error('arkivet får inte ligga i Digitalas repo');
  if (out === customer || !inside(out, customer) || existsSync(out)) throw new Error('ut ska vara en ny katalog inuti kundmappen');
  const interview=JSON.parse(readFileSync(a.intervju,'utf8'));
  mkdirSync(out, {mode:0o700});
  report={schema:1, verktyg:'arkivera', tid:nu(), adress:base, privat:true, sidor:[], kartor:[], insamlingsfel:[], klar:false,
    gransar:{adresser:MAX_ADRESSER,kartor:MAX_KARTOR}, not:'Kundmaterial: HTML, HAR och bilder är privata. Ingen inloggning; externa resurser, WebSockets och andra metoder än GET/HEAD blockeras. Blockerade resurser och fel redovisas; inget bevis för fullständig zon eller hela webbplatsens innehåll.'};
  const urls=new Map();
  function add(raw, source) {
    let url;
    try { url=address(raw,base); }
    catch { report.insamlingsfel.push({kalla:source, adress:String(raw), skal:'ogiltig adress'}); return; }
    if (!urls.has(url)) urls.set(url,new Set());
    urls.get(url).add(source);
  }
  const inputRows=[...(interview.svar||[]), ...(interview.fakta||[])].filter(r=>r.nyckel==='migrering_adresser' && !r.ersatt);
  if (interview.migrering_adresser !== undefined) inputRows.push({varde:interview.migrering_adresser});
  for (const r of inputRows) {
    const value=r.text ?? r.varde;
    if (r.vet_inte || r.status==='okänt') { report.insamlingsfel.push({kalla:'MIG1',skal:'migrering_adresser är okänt'}); continue; }
    const candidates=Array.isArray(value) ? value : String(value||'').split(/\r?\n/).map(x=>x.trim().replace(/^[-*]\s+/,''));
    for (const raw of candidates) {
      // A whole address per row: punctuation in a valid path must never be truncated.
      // Ambiguous prose/Markdown is an explicit collection failure, not a guessed URL.
      const url=typeof raw==='string' ? raw.trim() : '';
      if (!/^(?:https?:\/\/|\/)[^\s<>"\x00-\x1f]+$/.test(url)) {
        report.insamlingsfel.push({kalla:'MIG1',adress:raw,skal:'migrering_adresser behöver fullständig URL eller /sökväg per rad'}); continue;
      }
      add(url,'MIG1');
    }
  }
  const b=await browser(base, {javaScriptEnabled:false});
  let maps=0; const seen=new Set();
  async function sitemap(url, depth=0) {
    if (seen.has(url)) return; seen.add(url);
    const row={adress:url,lage:'misslyckad',skal:null};report.kartor.push(row);
    try {
      if (origin(url)!==origin(base) || depth>1 || maps>=MAX_KARTOR) throw new Error('kartans ursprung, djup eller antal ligger utanför gränsen');
      maps++;
      const response=await b.page.goto(url,{waitUntil:'domcontentloaded',timeout:30000});
      if (response?.status()!==200 || origin(b.page.url())!==origin(base)) throw new Error('sitemap gav inte eget svar 200');
      const xml=await within(response.text());
      if (Buffer.byteLength(xml)>2000000 || /<!DOCTYPE|<!ENTITY/i.test(xml)) throw new Error('sitemap för stor eller innehåller DTD/ENTITY');
      const parsed=await b.page.evaluate(text=>{
        const doc=new DOMParser().parseFromString(text,'text/xml');
        const root=doc.documentElement;
        if (doc.querySelector('parsererror') || !['urlset','sitemapindex'].includes(root.localName)) return null;
        const kind=root.localName==='urlset'?'url':'sitemap';
        const rows=[...root.children].filter(x=>x.localName===kind);
        if(rows.some(x=>[...x.children].filter(y=>y.localName==='loc').length!==1))return null;
        return {kind:root.localName,urls:rows.map(x=>[...x.children].find(y=>y.localName==='loc').textContent.trim())};
      },xml);
      if(!parsed)throw new Error('oläsbar sitemap');
      row.lage='ok';row.antal=parsed.urls.length;
      for(const raw of parsed.urls) {
        if(parsed.kind==='urlset')add(raw,'sitemap:'+url);
        else { try { await sitemap(address(raw,base),depth+1); } catch {report.insamlingsfel.push({kalla:url,adress:raw,skal:'ogiltig barnkarta'});} }
      }
    } catch(error) { row.skal=String(error.message).slice(0,500); }
  }
  try { await sitemap(address(a.sitemap || '/sitemap.xml',base)); }
  finally { await b.stang(); }
  let index=0;
  for(const [url,sources] of [...urls].sort((a,b)=>a[0].localeCompare(b[0]))) {
    const row={adress:url,kallor:[...sources].sort(),lage:'misslyckad',status:null,slutadress:null,skal:null,filer:[],blockerade:[]};report.sidor.push(row);
    let page;
    const stem=String(++index).padStart(4,'0');
    try {
      if(origin(url)!==origin(base))throw new Error('adress utanför gamla sajtens ursprung');
      if(index>MAX_ADRESSER)throw new Error('adress över körningens tak; kräver separat arkivering');
      page=await browser(base,{recordHar:{path:join(out,stem+'.har'),content:'embed',mode:'full'}});
      const response=await page.page.goto(url,{waitUntil:'load',timeout:30000});
      row.status=response?.status()??null;row.slutadress=page.page.url();
      if(row.status!==200 || origin(row.slutadress)!==origin(base))throw new Error('sidan gav inte eget svar 200');
      writeFileSync(join(out,stem+'.html'),await within(page.page.content()),{flag:'wx',mode:0o600});
      await within(page.page.screenshot({path:join(out,stem+'.png'),fullPage:true,timeout:30000}));
      row.lage='ok';
    } catch(error) { row.skal=String(error.message).slice(0,500); }
    finally {
      if(page) {
        row.blockerade=page.logg.blockerade;
        try {await page.stang();} catch {row.lage='misslyckad';row.skal='HAR kunde inte avslutas';}
      }
      for(const ext of ['html','har','png']) {
        const name=stem+'.'+ext,path=join(out,name);
        if(existsSync(path)){chmodSync(path,0o600);const raw=readFileSync(path);row.filer.push({fil:name,byte:raw.length,sha256:sha256(raw)});}
      }
      if(row.lage==='ok' && row.filer.length!==3){row.lage='misslyckad';row.skal='arkivfil saknas';}
    }
  }
  report.klar=report.sidor.length>0 && !report.insamlingsfel.length && report.kartor.every(x=>x.lage==='ok') && report.sidor.every(x=>x.lage==='ok' && !x.blockerade.length);
  writeFileSync(join(out,'MANIFEST.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx',mode:0o600});
  console.log(JSON.stringify({sidor:report.sidor.length,misslyckade:report.sidor.filter(x=>x.lage!=='ok').length,klar:report.klar}));
  process.exitCode=report.klar?0:1;
} catch(error) {
  if(out && report && existsSync(out) && !existsSync(join(out,'MANIFEST.json'))) {
    report.insamlingsfel.push({skal:String(error.message).slice(0,500)});
    writeFileSync(join(out,'MANIFEST.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx',mode:0o600});
  }
  console.error('arkivering vägrad eller avbruten: '+String(error.message).slice(0,300));process.exitCode=2;
}
