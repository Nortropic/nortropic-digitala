#!/usr/bin/env node
// Provhjälp: kör en init-page-fil (som Playwright MCP gör) i en riktig Playwright-sida och hämtar adresser; visar att
// gränsen verkställs, loggen skrivs och undantaget bara går till målet. Används av verktyg/test_webblasare.py.
//   node prova_init.mjs --init FIL --adresser URL,URL --ut LOGG.json
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import { writeFileSync } from 'node:fs';
import { args } from './gemensamt.mjs';
const a = args(process.argv.slice(2));
const mod = await import(pathToFileURL(a.init).href);
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext();
const page = await ctx.newPage();
await mod.default({ page });
const page2 = await ctx.newPage(); await mod.default({ page: page2 });  // andra sidan: hanteraren registreras inte en gång till
const ut = [];
for (const u of String(a.adresser).split(',')) { try { const r = await page.goto(u, { waitUntil: 'load', timeout: 20000 }); ut.push({ url: u, status: r ? r.status() : null }); } catch (e) { ut.push({ url: u, fel: e.message.split('\n')[0].slice(0, 120) }); } }
await browser.close();
writeFileSync(a.ut, JSON.stringify(ut, null, 1));
console.log(JSON.stringify(ut));
