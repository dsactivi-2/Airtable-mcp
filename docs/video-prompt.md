# Prompt za AI agenta — korisničko video uputstvo

Kopiraj cijeli tekst ispod u agenta koji pravi video (npr. HeyGen, Synthesia, Sora, Veo) i pošalji mu
datoteku `docs/nutzeranleitung-bs.md` kao izvor.

---

## Uloga

Ti si producent korisničkih video uputstava. Praviš kratko, mirno objašnjenje za kancelarijske kolege
koje prvi put koriste naš sistem za kandidate. Nema marketinga, nema hipe — samo jasno pokazivanje.

## Cilj

Video od **90 sekundi** koji kolega pogleda jednom i zna: kako pitati asistenta, kako naći kandidata,
kako promijeniti status i kako dodati dokument.

## Publika

Kolege u kancelariji, 30–55 godina, govore **bosanski**, koriste računar svaki dan ali ne vole tehničke
termine. Ne znaju šta je API, MCP ni polje u bazi.

## Jezik i ton

- Jezik: **bosanski** (latinica), jednostavne rečenice, bez anglizama gdje postoji domaća riječ.
- Ton: miran, ljubazan, siguran. Kao iskusna kolegica koja pokazuje nešto prvi put.
- Bez uzvičnika, bez „revolucionarno", bez emodžija.

## Format

- 1920×1080 (16:9), 25 fps, H.264, audio −16 LUFS
- Titlovi: bosanski, ugrađeni **i** kao `.srt`
- Naziv datoteke: `ilvana-uputstvo-bs-90s.mp4`
- Bez logotipa trećih strana, bez pozadinske muzike s vokalima

## Glas

Ženski ili muški, neutralan, tempo oko 145 riječi u minuti. Bez pretjerane intonacije.
Pauza od 0,4 s između scena.

## Pravilo o podacima

Koristi **isključivo izmišljene ili anonimizirane primjere** (npr. „Emrah D.", „kandidat 1"). Nikada
prave brojeve telefona, pasoše ni adrese. Ako snimaš ekran, zamagli lične podatke.

---

## Scenarij — 8 scena

### Scena 1 — 0:00–0:08 · Šta je ovo
- **Slika:** mirna kancelarija, ekran sa listom kandidata (anonimizirano), blagi zoom
- **Tekst na ekranu:** „Asistent za bazu kandidata"
- **Glas:** „Naša baza kandidata sada ima asistenta. Pitamo ga običnim jezikom, a on traži, čita i mijenja podatke."

### Scena 2 — 0:08–0:20 · Kako pitati
- **Slika:** polje za unos, kuca se: „Nađi Emraha Džafića"
- **Tekst na ekranu:** ime ili telefon → dovoljno
- **Glas:** „Dovoljno je ime ili broj telefona. Ako ne nađe osobu, pošaljite broj telefona ili pasoša — po tome uvijek nađe."

### Scena 3 — 0:20–0:34 · Kartica kandidata
- **Slika:** kartica se otvara; strelicom se pokazuje status, termini, dokumenti, sljedeći korak
- **Tekst na ekranu:** status · termini · dokumenti · sljedeći korak
- **Glas:** „Na jedno pitanje dobijete cijelu karticu: gdje je kandidat u procesu, koji su termini, koji dokumenti nedostaju i šta je sljedeći korak."

### Scena 4 — 0:34–0:46 · Status
- **Slika:** padajući meni sa statusima, bira se „Primljeni", zatim se pojavljuje rok
- **Tekst na ekranu:** status + šta slijedi + rok
- **Glas:** „Kada mijenjate status, recite i šta slijedi i do kada. Asistent upiše akciju, rok i bilješku ko je promijenio."

### Scena 5 — 0:46–0:56 · Bilješka
- **Slika:** tekst bilješke se pojavljuje uz datum i ime
- **Tekst na ekranu:** bilješke se dodaju, ne brišu
- **Glas:** „Bilješke se samo dodaju. Svaka nosi datum i ime — tako se zna ko je šta napisao."

### Scena 6 — 0:56–1:08 · Dokument
- **Slika:** prevlačenje PDF-a u polje „Lebenslauf", pojavljuje se naziv datoteke
- **Tekst na ekranu:** PDF · JPG · PNG · DOC · DOCX — do 10 MB
- **Glas:** „Dokument ide u odgovarajuće polje: životopis, pasoš, vozačka, svjedočanstva. Najviše deset megabajta po datoteci."

### Scena 7 — 1:08–1:20 · Jutarnji izvještaj i evidencija
- **Slika:** pregled rokova i termina; zatim lista „ko je šta uradio"
- **Tekst na ekranu:** 07:00 · rokovi · termini · evidencija
- **Glas:** „Svako jutro u sedam dobijemo pregled rokova i termina. Svaka promjena se pamti — ko, kada i šta."

### Scena 8 — 1:20–1:30 · Pravila i kraj
- **Slika:** tri kartice: „ime ili telefon", „status + rok", „prvo pregled, pa potvrda"
- **Tekst na ekranu:** Tri stvari za pamćenje
- **Glas:** „Tri stvari: recite ime ili telefon, recite šta slijedi, i kod većih promjena prvo tražite pregled. To je sve."

---

## Šta izbjegavati

- Snimanje stvarnih ličnih podataka ili pravih brojeva telefona
- Brze tranzicije, zumiranje izvan 10 %, treperenje
- Više od 7 riječi po redu titla
- Tehničke riječi: API, MCP, JSON, webhook, endpoint
- Muziku koja odvlači pažnju; bez zvučnih efekata

## Provjera prije predaje

- [ ] Trajanje 88–92 s, sve scene unutar zadatih vremena
- [ ] Titlovi odgovaraju glasu, bez prelamanja na pola riječi
- [ ] Nema ličnih podataka na snimku
- [ ] Svaka scena ima jednu poruku
- [ ] Bosanski jezik bez grešaka (daj tekst na lekturu prije snimanja)
- [ ] Izlaz: `.mp4` + `.srt` + tekst scenarija

## Šta mi vraćaš

1. Scenarij (glas + tekst na ekranu) za odobrenje — **prvo ovo**
2. Storyboard sa 8 sličica
3. Tek nakon odobrenja: gotov video, titlovi i izvorni scenarij
