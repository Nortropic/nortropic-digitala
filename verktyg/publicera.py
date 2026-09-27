#!/usr/bin/env python3
"""Maskinell publiceringsväg för Digitala-repot (HELHET-20260927, avsnitt 8): en kandidatgren integreras i main genom
PR-vägen under rulesetet main-skydd (pull request krävs, inga direkta push) utan manuellt PR-godkännande av ägaren —
men aldrig utan (1) en godkänd separat granskning bunden till exakt den commit som publiceras, (2) grön provsvit och
oförändrade pinnar på samma commit, (3) rent arbetsträd. Verktyget vägrar annars. Ingen kandidat kan ändra sin egen
granskning: granskningskatalogen ligger utanför repot och läses, aldrig skrivs.

    python3 -B verktyg/publicera.py --gren helhet/x --granskning GRANSKNINGSKATALOG --titel "…" --kropp KROPP.md [--torr] [--rot DIR] [--ingang DIR]

Kontroller före push: git status rent; HEAD = grenens spets; granskningens review.json har verdict approved och dess
underlag.json är bundet till HEAD (fältet commit, eller en commit med identiskt träd); sviten grön; pinnarna stämmer.
Sedan: git push, gh pr create (en befintlig PR återanvänds), gh pr merge --squash, gh pr view (MERGED + mergeCommit
avgör utfallet, inte gh:s exitkod), git fetch origin main. --torr gör alla kontroller och skriver planen utan push.
Kvitto: PUBLICERING-<tid>.json i granskningskatalogens förälder (utanför repot).

Körs från en klon eller worktree på kandidatgrenen; main hämtas med fetch utan checkout, så den får vara utcheckad i
primärutcheckningen (--ingang snabbspolar den om den står ren). Mergeläget verifieras med gh pr view, inte med gh:s
exitkod (fynd 2026-09-27: gh:s efterarbete föll i en worktree fast mergen skett).

Bindningen till granskningen: underlag.json:s fält 'commit' ska vara HEAD (eller en commit med exakt samma träd, dvs.
samma innehåll efter rebase på identisk bas); som reserv godtas att varje post i underlaget namnger HEAD:s korta sha.
Kvittot anger vilken bindning som gällde.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROT = HERE.parent


class Vagrad(Exception):
    pass


def git(rot, *a):
    return subprocess.run(['git', *a], cwd=rot, capture_output=True, text=True, check=True).stdout.strip()


def kontrollera(rot, gren, granskning):
    rot = Path(rot).resolve(); g = Path(granskning).resolve()
    if g.is_relative_to(rot):
        raise Vagrad('granskningskatalogen ska ligga utanför repot')
    if git(rot, 'status', '--porcelain'):
        raise Vagrad('arbetsträdet är inte rent')
    if git(rot, 'branch', '--show-current') != gren:
        raise Vagrad('utcheckad gren är inte ' + gren)
    head = git(rot, 'rev-parse', 'HEAD'); kort = head[:7]
    rev = g / 'review.json'
    if not rev.is_file():
        raise Vagrad('ingen review.json i granskningskatalogen')
    r = json.loads(rev.read_text(encoding='utf-8')); ans = r.get('answer') or {}
    if ans.get('verdict') != 'approved':
        raise Vagrad('granskningen är inte godkänd: verdict=%s' % ans.get('verdict'))
    und = g / 'underlag.json'
    if not und.is_file():
        raise Vagrad('ingen underlag.json i granskningskatalogen')
    try:
        u = json.loads(und.read_text(encoding='utf-8'))
    except ValueError:
        raise Vagrad('underlag.json är inte giltig JSON')
    c = u.get('commit')
    if c is not None and not (isinstance(c, str) and re.fullmatch(r'[0-9a-f]{7,40}', c)):
        raise Vagrad('granskningens underlag har ett commit-fält som inte är en sha (minst 7 hexsiffror): %r' % str(c)[:40])
    if c:
        if head.startswith(c):
            bindning = 'commit-fält'
        else:
            # samma innehåll efter rebase på en identisk bas: granskningen gäller trädet, inte commit-id:t
            tr = subprocess.run(['git', '-C', str(rot), 'rev-parse', '%s^{tree}' % c, 'HEAD^{tree}'], capture_output=True, text=True)
            trad = tr.stdout.split() if tr.returncode == 0 else []
            if len(trad) == 2 and trad[0] == trad[1]:
                bindning = 'commit-fält (samma träd som %s efter rebase)' % str(c)[:7]
            else:
                raise Vagrad('granskningens underlag är bundet till commit %s, inte HEAD %s (och träden skiljer sig): granskningen gäller en annan version' % (str(c)[:12], kort))
    else:
        poster = u.get('filer') or []
        if not poster or not all(isinstance(p, list) and len(p) >= 3 and kort in str(p[2]) for p in poster):
            raise Vagrad('granskningens underlag namnger inte HEAD %s (fältet commit saknas och inte varje post namnger revisionen): granskningen gäller en annan version' % kort)
        bindning = 'per-post'
    prov = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'verktyg', '-p', 'test_*.py'], cwd=rot, capture_output=True, text=True)
    sista = [l for l in (prov.stderr + prov.stdout).splitlines() if l.strip()]
    if prov.returncode != 0 or not any(l.startswith('OK') for l in sista):
        raise Vagrad('provsviten är inte grön: ' + ' | '.join(sista[-3:]))
    pin = subprocess.run([sys.executable, '-B', 'verktyg/pinna.py'], cwd=rot, capture_output=True, text=True)
    if pin.returncode != 0 or 'inga skillnader' not in pin.stdout:
        raise Vagrad('pinnarna stämmer inte: ' + (pin.stdout + pin.stderr).strip()[-200:])
    return {'head': head, 'granskning': str(g), 'verdict': 'approved', 'bindning': bindning, 'prov': [l for l in sista if l.startswith(('Ran', 'OK'))], 'pinnar': pin.stdout.strip()}


def publicera(rot, gren, granskning, titel, kropp, torr=False, ingang=None):
    """Push, PR, squash-merge, verifiering av mergeläget, hämtning av main utan checkout (fungerar i en worktree där main
    är utcheckad någon annanstans); ingången (--ingang) snabbspolas bara om den står ren på main."""
    k = kontrollera(rot, gren, granskning)
    plan = [['git', 'push', '-u', 'origin', gren], ['gh', 'pr', 'create', '--base', 'main', '--head', gren, '--title', titel, '--body-file', str(kropp)],
            ['gh', 'pr', 'merge', gren, '--squash', '--subject', titel], ['gh', 'pr', 'view', gren, '--json', 'state,mergeCommit,number,url'], ['git', 'fetch', 'origin', 'main']]
    kvitto = {'schema': 2, 'tid': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'gren': gren, 'kontroller': k, 'torr': torr, 'plan': [' '.join(p) for p in plan], 'utfall': [], 'main': None}
    if not torr:
        for cmd in plan:
            p = subprocess.run(cmd, cwd=rot, capture_output=True, text=True)
            kvitto['utfall'].append({'kommando': ' '.join(cmd[:3]), 'status': p.returncode, 'ut': (p.stdout or p.stderr).strip()[-400:]})
            if cmd[:3] == ['gh', 'pr', 'create'] and p.returncode != 0 and 'already exists' in (p.stderr + p.stdout):
                kvitto['utfall'][-1]['not'] = 'PR fanns redan för grenen: fortsätter med den'; continue
            if cmd[:3] == ['gh', 'pr', 'merge']:
                # gh:s exitkod avgör inte (efterarbetet kan falla fast servern mergat): pr view nedan avgör
                if p.returncode != 0:
                    kvitto['utfall'][-1]['not'] = 'exitkod %d bokförd; mergeläget avgörs av gh pr view' % p.returncode
                continue
            if cmd[:3] == ['gh', 'pr', 'view']:
                try:
                    v = json.loads(p.stdout) if p.returncode == 0 else {}
                except ValueError:
                    v = {}
                kvitto['pr'] = {'nummer': v.get('number'), 'url': v.get('url'), 'state': v.get('state')}
                if v.get('state') == 'MERGED' and (v.get('mergeCommit') or {}).get('oid'):
                    kvitto['main'] = v['mergeCommit']['oid']
                else:
                    kvitto['avbrutet'] = 'PR inte mergad (state %s)' % (v.get('state') or 'okänt: gh pr view gav %s' % ('inget giltigt svar' if p.returncode == 0 else 'exitkod %d' % p.returncode)); break
                continue
            if p.returncode != 0:
                kvitto['avbrutet'] = ' '.join(cmd[:3]); break
        if kvitto.get('main'):
            # fjärrgrenen tas bort bäst-möjligt (den lokala grenen är utcheckad här och lämnas); ingången snabbspolas bara om den står ren på main
            d = subprocess.run(['git', 'push', 'origin', '--delete', gren], cwd=rot, capture_output=True, text=True)
            kvitto['fjarrgren_borttagen'] = d.returncode == 0
            if ingang:
                ig = Path(ingang)
                ren = subprocess.run(['git', '-C', str(ig), 'status', '--porcelain'], capture_output=True, text=True)
                gr = subprocess.run(['git', '-C', str(ig), 'branch', '--show-current'], capture_output=True, text=True)
                if ren.returncode == 0 and ren.stdout.strip() == '' and gr.stdout.strip() == 'main':
                    f = subprocess.run(['git', '-C', str(ig), 'pull', '--ff-only'], capture_output=True, text=True)
                    kvitto['ingang'] = {'snabbspolad': f.returncode == 0, 'ut': (f.stdout or f.stderr).strip()[-200:]}
                else:
                    kvitto['ingang'] = {'snabbspolad': False, 'ut': 'ingången är inte ren på main: lämnad orörd'}
    ut = Path(granskning).resolve().parent / ('PUBLICERING-%s.json' % kvitto['tid'].replace(':', '').replace('-', ''))
    hem = str(Path.home())
    ut.write_text(json.dumps(kvitto, ensure_ascii=False, indent=1).replace(hem, '~') + '\n', encoding='utf-8')  # inga privata absoluta sökvägar i kvittot
    kvitto['kvitto'] = str(ut)
    return kvitto


def main(argv=None):
    p = argparse.ArgumentParser(prog='publicera', description=__doc__.split('\n\n')[0])
    p.add_argument('--gren', required=True); p.add_argument('--granskning', required=True); p.add_argument('--titel', required=True); p.add_argument('--kropp', required=True); p.add_argument('--torr', action='store_true'); p.add_argument('--ingang', help='primärutcheckningen på main som snabbspolas efter mergen om den står ren'); p.add_argument('--rot', default=str(ROT))
    a = p.parse_args(argv)
    try:
        k = publicera(a.rot, a.gren, a.granskning, a.titel, Path(a.kropp).resolve(), a.torr, a.ingang)
    except (Vagrad, subprocess.CalledProcessError) as e:
        print(json.dumps({'vagrad': str(e.args[0]) if e.args else str(e)}, ensure_ascii=False)); return 2
    print(json.dumps({'gren': a.gren, 'torr': a.torr, 'head': k['kontroller']['head'][:7], 'main': k.get('main', None) and k['main'][:7], 'avbrutet': k.get('avbrutet'), 'kvitto': k['kvitto']}, ensure_ascii=False))
    return 0 if not k.get('avbrutet') else 1


if __name__ == '__main__':
    sys.exit(main())
