# Rejestr GUNB (RWDZ) – pliki dla Normografu

Kopia Rejestru Wniosków, Decyzji i Zgłoszeń w sprawach budowlanych (GUNB) podzielona na małe pliki per gmina:
pozwolenia na budowę (wnioski i decyzje) od 2016 r. oraz zgłoszenia. Bez nazwisk inwestorów i projektantów.

- Źródło: https://wyszukiwarka.gunb.gov.pl/pobranie.html (dane publiczne, aktualizowane przez GUNB co noc).
- Aktualizacja: workflow `aktualizacja.yml` codziennie o 04:23 UTC, razem ze strażnikiem przepisów Normografu.
  Historia jest nadpisywana – w repozytorium zawsze jest tylko bieżący stan.
- Użycie: arkusz „Działka” w Normografie (G-01), strona architriada.eu/dzialka i Locus (analiza działek, promień 200 m) pobierają
  `dane/<jednostka ewidencyjna>.json.gz` wprost z GitHuba (raw.githubusercontent.com) i rozpakowują go w przeglądarce.
  Dla dużych jednostek plik zawiera `{"_podzial": [...]}` i dane leżą w `dane/<jednostka>.<obręb>.json.gz`.

Format: `{"<obręb>": {"<numer działki>": [[rodzaj P|Z, data wpływu, data decyzji, kategoria, zamierzenie, opis, stan zgłoszenia(, arkusz mapy)], …]}}`.
Arkusz (8. pole) jest tylko przy działkach w obrębach z arkuszami map – Locus składa z niego identyfikator działki dla ULDK.

Ręcznie: `python3 tools/rwdz.py dane [--woj mazowieckie] [--zrodla katalog_z_zipami]`.
