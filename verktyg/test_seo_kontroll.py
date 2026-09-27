import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seo_kontroll as sk  # noqa: E402
from test_verksamhetsuppgifter import exempel  # noqa: E402

SIDA = '''<!doctype html><html lang="sv"><head><title>{title}</title><meta name="description" content="Anläggning och skötsel i Provstad.">
{robots}<link rel="canonical" href="https://provfirma.se{path}"></head><body><h1>{h1}</h1><a href="/tjanster/">Tjänster</a><a href="{dead}">x</a>
<img src="/a.jpg" alt="Trädgård"><img src="/b.jpg">
<script type="application/ld+json">{ld}</script></body></html>'''


def skriv(d, path, **kw):
    f = d / path.lstrip('/') / 'index.html' if path.endswith('/') else d / path.lstrip('/')
    f.parent.mkdir(parents=True, exist_ok=True)
    ld = kw.pop('ld', json.dumps({'@context': 'https://schema.org', '@type': 'LocalBusiness', 'name': 'Testfirma Nord', 'telephone': '+46701234567',
                                  'address': {'@type': 'PostalAddress', 'streetAddress': 'Provgatan 1', 'postalCode': '123 45', 'addressLocality': 'Provstad', 'addressCountry': 'SE'}}))
    f.write_text(SIDA.format(title=kw.get('title', 'Trädgård i Provstad | Testfirma'), robots=kw.get('robots', ''), path=path, h1=kw.get('h1', 'Trädgård i Provstad'), dead=kw.get('dead', '/tjanster/'), ld=ld), encoding='utf-8')


class Rapport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)
        self.v = self.d / 'VERKSAMHET.json'; self.v.write_text(json.dumps(exempel(fiktiv=False, webb={'doman': 'provfirma.se'})))
        skriv(self.d, '/', robots='<meta name="robots" content="noindex">')
        skriv(self.d, '/tjanster/', robots='<meta name="robots" content="noindex">', dead='/finns-inte/', h1='Tjänster', title='Tjänster | Testfirma')
        (self.d / 'sitemap.xml').write_text('<urlset><url><loc>https://provfirma.se/</loc></url></urlset>')
        (self.d / 'robots.txt').write_text('User-agent: *\nDisallow: /\nSitemap: https://provfirma.se/sitemap.xml\n')

    def tearDown(self):
        self.tmp.cleanup()

    def typer(self, r):
        return sorted({x['typ'].split(' (')[0].split(':')[0] for p in r['per_sida'] for x in p['fynd']} | {x['typ'] for x in r['sajt']})

    def test_forhandsvisning_ren_utom_dod_lank_och_alt(self):
        r = sk.rapport(str(self.d), 'forhandsvisning', str(self.v))
        self.assertEqual(r['sidor'], 2)
        self.assertEqual(self.typer(r), ['img utan alt', 'intern länk löser inte'])
        self.assertEqual(r['doman'], 'provfirma.se')

    def test_lansering_krav_och_noindex_kvar(self):
        r = sk.rapport(str(self.d), 'lansering', str(self.v))
        t = self.typer(r)
        self.assertIn('noindex kvar vid lansering', t)
        self.assertIn('robots blockerar allt vid lansering', t)

    def test_schema_provas_mot_verksamheten(self):
        skriv(self.d, '/kontakt/', robots='<meta name="robots" content="noindex">', ld=json.dumps({'@type': 'LocalBusiness', 'name': 'Annat Namn AB', 'telephone': '070-123 45 67',
              'address': {'@type': 'PostalAddress', 'postalCode': '12345'}, 'aggregateRating': {'ratingValue': 4.9}}))
        r = sk.rapport(str(self.d), 'forhandsvisning', str(self.v))
        kontakt = next(p for p in r['per_sida'] if p['sida'] == '/kontakt/')
        typer = [x['typ'] for x in kontakt['fynd']]
        for t in ('schema name ≠ verksamhetens namn', 'schema telephone ≠ E.164 ur verksamheten', 'postalCode-form', 'aggregateRating utan källa'):
            self.assertIn(t, typer, t)
        dold = exempel(fiktiv=False, adress={'gata': 'Hemgatan 2', 'postnummer': '123 45', 'ort': 'Provstad', 'publik': False, 'roll': 'hemvist'})
        self.v.write_text(json.dumps(dold))
        r = sk.rapport(str(self.d), 'forhandsvisning', str(self.v))
        self.assertTrue(any(x['typ'] == 'schema bär adress fast adressen inte är publik' for p in r['per_sida'] for x in p['fynd']))

    def test_dubbla_titlar_omdirigeringar_och_cli(self):
        skriv(self.d, '/om/', robots='<meta name="robots" content="noindex">', title='Trädgård i Provstad | Testfirma')
        red = self.d / 'RED.json'; red.write_text(json.dumps({'gamla': [{'fran': '/gammal', 'till': '/tjanster/', 'status': 301}, {'fran': '/borta', 'till': '/saknas/', 'status': 301}, {'fran': '/x', 'till': '/', 'status': 302}]}))
        ut = self.d / 'R.json'; md = self.d / 'R.md'
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sk.main(['--bygge', str(self.d), '--lage', 'forhandsvisning', '--verksamhet', str(self.v), '--omdirigeringar', str(red), '--ut', str(ut), '--md', str(md)]), 0)
        r = json.loads(ut.read_text())
        self.assertTrue(any(x['typ'] == 'title dubblett' for p in r['per_sida'] for x in p['fynd']))
        self.assertEqual(sorted(x['typ'] for x in r['sajt']), ['omdirigering utan 301/308', 'omdirigeringsmål saknas'])
        self.assertIn('# SEO-kontroll', md.read_text())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sk.main(['--bygge', str(self.d / 'finns-inte'), '--lage', 'lansering', '--ut', str(ut)]), 2)


if __name__ == '__main__':
    unittest.main()
