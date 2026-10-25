import os
import json
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# Nastavitev map za shranjevanje
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# 1. Nov, stabilen URL
URL = "https://en.wikipedia.org/wiki/List_of_most-streamed_songs_on_Spotify"

# Zahtevane glave z ustreznim User-Agentom
headers = {
    "User-Agent": "SpotifySpremljevalecStudentProject/1.0 (jovan.obrenovic@student.um.si)"
}

print(f"Pridobivanje podatkov s strani: {URL}...")
response = requests.get(URL, headers=headers)

if response.status_code == 200:
    print("Stran uspešno prenesena!")
else:
    print(f"Napaka pri prenosu: {response.status_code}")
    exit()

# 2. Razčlenjevanje HTML vsebine z BeautifulSoup
soup = BeautifulSoup(response.text, "html.parser")

# Na tej strani je glavna tabela tista z razredom 'wikitable sortable'
table = soup.find("table", {"class": "wikitable"})

songs_data = []

if table:
    rows = table.find_all("tr")[1:]  # Preskočimo glavo tabele
    
    for idx, row in enumerate(rows, 1):
        cols = row.find_all(["th", "td"])
        
        # Preverimo, ali ima vrstica dovolj stolpcev
        if len(cols) >= 3:
            naslov = cols[0].get_text(strip=True).replace('"', '')
            izvajalec = cols[1].get_text(strip=True)
            predvajanja = cols[2].get_text(strip=True)
            
            songs_data.append({
                "id": f"SPOTIFY_TOP_{idx}",
                "naslov": naslov,
                "izvajalec": izvajalec,
                "stPredvajanj": predvajanja
            })

print(f"Uspešno razčlenjenih {len(songs_data)} zapisov.")

# 3. Shranjevanje v JSON datoteko
json_path = os.path.join(DATA_DIR, "scraped_spotify_top.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(songs_data, f, ensure_ascii=False, indent=4)
print(f"Shranjeno v JSON: '{json_path}'")

# 4. Shranjevanje v XML datoteko
root = ET.Element("topSpotifySkladbe")
for song in songs_data:
    item = ET.SubElement(root, "skladba", id=song["id"])
    for key, val in song.items():
        if key != "id":
            child = ET.SubElement(item, key)
            child.text = val

xml_path = os.path.join(DATA_DIR, "scraped_spotify_top.xml")
tree = ET.ElementTree(root)
ET.indent(tree, space="    ")
tree.write(xml_path, encoding="utf-8", xml_declaration=True)
print(f"Shranjeno v XML: '{xml_path}'")