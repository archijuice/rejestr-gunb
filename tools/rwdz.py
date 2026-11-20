#!/usr/bin/env python3
"""Rejestr Wniosków, Decyzji i Zgłoszeń GUNB (RWDZ) → małe pliki dla arkusza „Działka” Normografu (G-01),
strony architriada.eu/dzialka (ta sama ramka) i Locusa. Przeglądarka pobiera plik gminy wprost z GitHuba
i rozpakowuje go sama – bez serwera.

Źródło: https://wyszukiwarka.gunb.gov.pl/pobranie.html — pliki aktualizowane co noc:
pozwolenia na budowę (wnioski i decyzje) od 2016 r. dla każdego województwa, zgłoszenia dla całego kraju.

Wynik (katalog podany w argumencie, domyślnie dane/):
  <jednostka>.json.gz            {"obręb": {"numer działki": [[rodzaj, wpływ, decyzja, kategoria, zamierzenie, opis, stan(, arkusz)], …]}}
                                 arkusz (8. pole) tylko dla działek w obrębach z arkuszami map
  <jednostka>.<obręb>.json.gz    to samo dla jednego obrębu, gdy jednostka jest duża (miasta)
  _stan.json                     data danych i liczby wpisów
Pliki są deterministyczne (posortowane, gzip bez znacznika czasu), więc wdrożenie FTP wgrywa tylko zmienione.
Nazwisk inwestorów i projektantów nie zapisujemy.

Użycie:  python3 tools/rwdz.py [katalog_wyjściowy] [--zrodla katalog_z_zipami] [--woj mazowieckie] [--bez-starych]
"""
import csv, datetime as dt, gzip, io, json, os, sys, urllib.request, zipfile
from collections import defaultdict

URL = 'https://wyszukiwarka.gunb.gov.pl/pliki_pobranie/'
WOJ = ['dolnoslaskie', 'kujawsko-pomorskie', 'lubelskie', 'lubuskie', 'lodzkie', 'malopolskie', 'mazowieckie',
       'opolskie', 'podkarpackie', 'podlaskie', 'pomorskie', 'slaskie', 'swietokrzyskie', 'warminsko-mazurskie',
       'wielkopolskie', 'zachodniopomorskie']
ZGL = ['zgloszenia_2016_2021', 'zgloszenia_2022_up']
DUZA = 1_500_000          # jednostka powyżej tylu bajtów (przed kompresją) dostaje też pliki per obręb
OPIS = 220                 # maks. długość opisu zamierzenia


def zrodlo(nazwa, katalog=None):
    if katalog and os.path.exists(os.path.join(katalog, f'wynik_{nazwa}.zip')):
        return open(os.path.join(katalog, f'wynik_{nazwa}.zip'), 'rb').read()
    req = urllib.request.Request(URL + f'wynik_{nazwa}.zip', headers={'User-Agent': 'Normograf/1.0 (+https://normograf.pl)'})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def wiersze(zb):
    csv.field_size_limit(10 ** 8)
    with zipfile.ZipFile(io.BytesIO(zb)) as z:
        n = next(x for x in z.namelist() if x.lower().endswith('.csv'))
        with z.open(n) as f:
            r = csv.reader(io.TextIOWrapper(f, encoding='utf-8-sig', newline=''), delimiter=';')
            nag = next(r); ix = {}
            for i, k in enumerate(nag):
                ix.setdefault(k.strip(), i)
            for w in r:
                if len(w) >= len(nag):
                    yield {k: w[i].strip() for k, i in ix.items()}


def d(v):
    return (v or '')[:10]


def ark(wpis, w):
    """Numer arkusza mapy jako 8. pole – tylko gdy jest (Locus buduje z niego identyfikator działki dla ULDK)."""
    a = w.get('numer_arkusza_dzialki', '').strip()
    return wpis + [a] if a else wpis


def main():
    a = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith('--') and sys.argv[i - 1] not in ('--zrodla', '--woj')]
    wyj = a[0] if a else 'dane'
    zr = sys.argv[sys.argv.index('--zrodla') + 1] if '--zrodla' in sys.argv else None
    dane = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    n = {'pozwolenia': 0, 'zgloszenia': 0}
    tylko = sys.argv[sys.argv.index('--woj') + 1].split(',') if '--woj' in sys.argv else WOJ   # do testów
    zgl = [z for z in ZGL if '--bez-starych' not in sys.argv or z != ZGL[0]]
    for woj in tylko:
        for w in wiersze(zrodlo(woj, zr)):
            j, o, dz = w.get('jednosta_numer_ew', ''), w.get('obreb_numer', ''), w.get('numer_dzialki', '').replace(' ', '')
            if not (j and o and dz):
                continue
            dane[j][o][dz].append(ark(['P', d(w.get('data_wplywu_wniosku')), d(w.get('data_wydania_decyzji')),
                                       w.get('kategoria', ''), w.get('nazwa_zamierzenia_bud', ''),
                                       w.get('nazwa_zam_budowlanego', '')[:OPIS], ''], w))
            n['pozwolenia'] += 1
        print(woj, n, flush=True)
    for z in zgl:
        for w in wiersze(zrodlo(z, zr)):
            j, o, dz = w.get('jednostki_numer', ''), w.get('obreb_numer', ''), w.get('numer_dzialki', '').replace(' ', '')
            if not (j and o and dz):
                continue
            dane[j][o][dz].append(ark(['Z', d(w.get('data_wplywu_wniosku_do_urzedu')), '', w.get('kategoria', ''),
                                       w.get('rodzaj_zam_budowlanego', ''), w.get('nazwa_zam_budowlanego', '')[:OPIS],
                                       w.get('stan', '')], w))
            n['zgloszenia'] += 1
        print(z, n, flush=True)

    os.makedirs(wyj, exist_ok=True)
    stare = {f for f in os.listdir(wyj) if f.endswith('.json.gz')}
    nowe = set()

    def zapisz(nazwa, obj):
        raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0, compresslevel=9) as g:
            g.write(raw)
        p = os.path.join(wyj, nazwa)
        b = buf.getvalue()
        if not (os.path.exists(p) and open(p, 'rb').read() == b):
            open(p, 'wb').write(b)
        nowe.add(nazwa)
        return len(raw)

    for j, obreby in dane.items():
        for o in obreby.values():
            for lst in o.values():
                lst.sort(key=lambda x: (x[1], x[0]), reverse=True)
        if not all(c.isalnum() or c in '_' for c in j):
            continue
        rozm = zapisz(f'{j}.json.gz', obreby)
        if rozm > DUZA:
            os.remove(os.path.join(wyj, f'{j}.json.gz')); nowe.discard(f'{j}.json.gz')
            for o, dz in obreby.items():
                if o.isalnum():
                    zapisz(f'{j}.{o}.json.gz', {o: dz})
            zapisz(f'{j}.json.gz', {'_podzial': sorted(o for o in obreby if o.isalnum())})
    for f in stare - nowe:
        os.remove(os.path.join(wyj, f))
    with open(os.path.join(wyj, '_stan.json'), 'w', encoding='utf-8') as f:
        json.dump({'data': dt.date.today().isoformat(), **n, 'pliki': len(nowe)}, f, ensure_ascii=False)
    print('gotowe:', n, 'plików', len(nowe))


if __name__ == '__main__':
    main()
