# 🎵 Spotify Companion - XML/JSON Data Processor (Podatkovni Obdelovalnik)

Ta projekt je del naloge za obdelavo relacijskih podatkov v obliki XML in JSON za spletno aplikacijo **Spotify Spremljevalec / Zvokopis**. 

Aplikacija v jeziku Python naloži tri med seboj povezane XML datoteke (`izvajalci.xml`, `skladbe.xml`, `playliste.xml`), jih deserializira v objekte, poveže preko ID atributov, filtrira po kriteriju datuma izdaje ter rezultate izvozi v formatu JSON in XML.

---

## 📁 Struktura Projekta (Project Structure)

Pred zagonom preverite, da imate ustvarjeni mapi `data` in `filtered` ter ustrezno razporejene datoteke:

```text
spotify-xml-processor/
│
├── data/                       # Vhodne XML datoteke
│   ├── izvajalci.xml           # Podatki o izvajalcih (id)
│   ├── skladbe.xml             # Podatki o skladbah (id, artistId)
│   └── playliste.xml           # Podatki o seznamih predvajanja (id, trackId)
│
├── filtered/                   # Izhodne filtrirane datoteke (samodejno ustvarjene)
│   ├── filtrirano.json         # Filtrirani podatki v JSON formatu
│   └── filtrirano.xml          # Filtrirani podatki v novostrukturiranem XML formatu
│
├── app.py                      # Glavna Python aplikacija
└── README.md                   # Dokumentacija projekta
```

---

## ⚙️ Zahteve (Requirements)

Za zagon skripte potrebujete zgolj **Python 3.8+**. Uporabljene so zgolj standardne knjižnice (`xml.etree.ElementTree`, `json`, `os`), zato dodatne `pip` namestitve niso potrebne.

---

## 🚀 Zagon Aplikacije (How to Run)

1. **Premaknite se v korensko mapo projekta:**
   ```bash
   cd spotify-xml-processor
   ```

2. **Poženite Python skripto:**
   ```bash
   python app.py
   ```

---

## 🔍 Delovanje Aplikacije (Application Workflow)

1. **Branje in Deserializacija:**
   Skripta prebere XML datoteke iz mape `data/` in pretvori njihove elemente ter atribute v Python slovarje.
   
2. **Povezovanje Podatkov (Relacije):**
   Preko atributov `artistId` in `trackId` poveže posamezno playlisto s pripadajočo skladbo in njenim izvajalcem.

3. **Filtriranje Podatkov:**
   Filtrira vse relacije, kjer je datum izdaje skladbe novejši od `2015-01-01`.

4. **Izkpis v Konzolo:**
   Filtrirane rezultate oblikuje v pregledno tabelo in jih izpiše v terminal.

5. **Izvoz v JSON in XML:**
   Rezultate shrani v mapo `filtered/`:
   * `filtered/filtrirano.json` (strukturiran seznam objektov)
   * `filtered/filtrirano.xml` (nov XML dokument s filtriranimi zapisi)

---

## 📊 Primer Izpisa v Konzoli (Console Output Example)

```text
======================================================================================
                  FILTRIRANI PODATKI (Skladbe izdane po 2015-01-01)                  
======================================================================================
Playlista          | Skladba            | Izvajalec       | Datum Izdaje | Število Predvajanj
--------------------------------------------------------------------------------------
Top Pop 2020       | Blinding Lights    | The Weeknd      | 2019-11-29    | 3,800,000,000
Workout Mix        | Levitating         | Dua Lipa        | 2020-03-27    | 2,100,000,000
Alternative Vibes  | Bad Guy            | Billie Eilish   | 2019-03-29    | 2,500,000,000
Rock Anthems       | Believer           | Imagine Dragons | 2017-02-01    | 2,900,000,000
Top Pop 2020       | Shape of You       | Ed Sheeran      | 2017-01-06    | 3,600,000,000
Workout Mix        | Circles            | Post Malone     | 2019-08-30    | 2,200,000,000
Pop Hits           | Anti-Hero          | Taylor Swift    | 2022-10-21    | 1,100,000,000
--------------------------------------------------------------------------------------
Uspešno izvoženo v filtered/filtrirano.json in filtered/filtrirano.xml!
```