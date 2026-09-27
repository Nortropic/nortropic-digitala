#!/usr/bin/env python3
"""Maskinell publiceringsväg för Digitala-repot (HELHET-20260927, avsnitt 8): en kandidatgren integreras i main genom
PR-vägen under rulesetet main-skydd (pull request krävs, inga direkta push) utan manuellt PR-godkännande av ägaren —
men aldrig utan (1) en godkänd separat granskning bunden till exakt den commit som publiceras, (2) grön provsvit och
oförändrade pinnar på samma commit, (3) rent arbetsträd. Verktyget vägrar annars. Ingen kandidat kan ändra sin egen
granskning: granskningskatalogen ligger utanför repot och läses, aldrig skrivs.

    python3 -B verktyg/publicera.py --gren helhet/x --granskning GRANSKNINGSKATALOG --titel "…" --kropp KROPP.md [--torr] [--rot DIR]

Kontroller före push: git status rent; HEAD = grenens spets; granskningens review.json har verdict approved och dess
underlag.json namnger HEAD:s korta sha (kandidaten som granskades); sviten grön; pinnarna stämmer. Sedan: push, gh pr
create, gh pr merge --squash --delete-branch, main hämtas. --torr gör alla kontroller och skriver planen utan push.
Kvitto: PUBLICERING-<tid>.json i granskningskatalogens förälder (utanför repot).
"""
import argparse
import json
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
    if c:
        if not (isinstance(c, str) and len(c) >= 7 and head.startswith(c)):
            raise Vagrad('granskningens underlag är bundet till commit %s, inte HEAD %s: granskningen gäller en annan version' % (str(c)[:12], kort))
        bindning = 'commit-fält'
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


def publicera(rot, gren, granskning, titel, kropp, torr=False):
    k = kontrollera(rot, gren, granskning)
    plan = [['git', 'push', '-u', 'origin', gren], ['gh', 'pr', 'create', '--base', 'main', '--head', gren, '--title', titel, '--body-file', str(kropp)], ['gh', 'pr', 'merge', '--squash', '--delete-branch', '--subject', titel], ['git', 'checkout', 'main'], ['git', 'pull', '--ff-only']]
    kvitto = {'schema': 1, 'tid': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'gren': gren, 'kontroller': k, 'torr': torr, 'plan': [' '.join(p) for p in plan], 'utfall': []}
    if not torr:
        for cmd in plan:
            p = subprocess.run(cmd, cwd=rot, capture_output=True, text=True)
            kvitto['utfall'].append({'kommando': ' '.join(cmd[:3]), 'status': p.returncode, 'ut': (p.stdout or p.stderr).strip()[-400:]})
            if p.returncode != 0:
                kvitto['avbrutet'] = ' '.join(cmd[:3]); break
        else:
            kvitto['main'] = git(rot, 'rev-parse', 'HEAD')
    ut = Path(granskning).resolve().parent / ('PUBLICERING-%s.json' % kvitto['tid'].replace(':', '').replace('-', ''))
    ut.write_text(json.dumps(kvitto, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    kvitto['kvitto'] = str(ut)
    return kvitto


def main(argv=None):
    p = argparse.ArgumentParser(prog='publicera', description=__doc__.split('\n\n')[0])
    p.add_argument('--gren', required=True); p.add_argument('--granskning', required=True); p.add_argument('--titel', required=True); p.add_argument('--kropp', required=True); p.add_argument('--torr', action='store_true'); p.add_argument('--rot', default=str(ROT))
    a = p.parse_args(argv)
    try:
        k = publicera(a.rot, a.gren, a.granskning, a.titel, Path(a.kropp).resolve(), a.torr)
    except (Vagrad, subprocess.CalledProcessError) as e:
        print(json.dumps({'vagrad': str(e.args[0]) if e.args else str(e)}, ensure_ascii=False)); return 2
    print(json.dumps({'gren': a.gren, 'torr': a.torr, 'head': k['kontroller']['head'][:7], 'main': k.get('main', None) and k['main'][:7], 'avbrutet': k.get('avbrutet'), 'kvitto': k['kvitto']}, ensure_ascii=False))
    return 0 if not k.get('avbrutet') else 1


if __name__ == '__main__':
    sys.exit(main())
