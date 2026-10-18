import xml.etree.ElementTree as ET
import json
import os

def main():
    # Definicija poti do map
    DATA_DIR = 'data'
    FILTERED_DIR = 'filtered'

    # Zagotovi, da izhodna mapa obstaja
    os.makedirs(FILTERED_DIR, exist_ok=True)

    # Pot do vhodnih datotek
    izvajalci_path = os.path.join(DATA_DIR, 'izvajalci.xml')
    skladbe_path = os.path.join(DATA_DIR, 'skladbe.xml')
    playliste_path = os.path.join(DATA_DIR, 'playliste.xml')

    # 1. Branje XML datotek in deserializacija
    tree_a = ET.parse(izvajalci_path)
    tree_s = ET.parse(skladbe_path)
    tree_p = ET.parse(playliste_path)

    artists = {node.attrib['id']: {c.tag: c.text for c in node} for node in tree_a.getroot()}
    tracks = {node.attrib['id']: {**node.attrib, **{c.tag: c.text for c in node}} for node in tree_s.getroot()}
    playlists = [{**node.attrib, **{c.tag: c.text for c in node}} for node in tree_p.getroot()]

    # 2. Povezovanje podatkov prek ID-jev (Relacije)
    full_data = []
    for p in playlists:
        track = tracks.get(p.get('trackId'), {})
        artist = artists.get(track.get('artistId'), {})
        
        full_data.append({
            'playlist_id': p.get('id'),
            'playlist_name': p.get('naziv'),
            'user': p.get('uporabnik'),
            'created_date': p.get('datumKreiranja'),
            'track_id': track.get('id'),
            'track_title': track.get('naslov'),
            'duration_sec': int(track.get('trajanjeSekunde', 0)) if track.get('trajanjeSekunde') else 0,
            'streams': int(track.get('stPredvajanj', 0)) if track.get('stPredvajanj') else 0,
            'release_date': track.get('datumIzdaje'),
            'note': track.get('opomba'),
            'artist_id': artist.get('artistId'),
            'artist_name': artist.get('ime'),
            'genre': artist.get('zvrst'),
            'country': artist.get('drzava')
        })

    # 3. Filtriranje (npr. skladbe izdane po 2015-01-01)
    filtered = [x for x in full_data if x['release_date'] and x['release_date'] > '2015-01-01']

    # Izpis v konzolo v obliki pregledne tabele
    print("\n" + "="*86)
    print(f"{'FILTRIRANI PODATKI (Skladbe izdane po 2015-01-01)':^86}")
    print("="*86)
    print(f"{'Playlista':<18} | {'Skladba':<18} | {'Izvajalci':<15} | {'Datum Izdaje':<12} | {'Število Predvajanj'}")
    print("-" * 86)
    for item in filtered:
        streams_fmt = f"{item['streams']:,}"
        print(f"{item['playlist_name']:<18} | {item['track_title']:<18} | {item['artist_name']:<15} | {item['release_date']:<12} | {streams_fmt}")
    print("-" * 86 + "\n")

    # 4. Izvoz v JSON
    json_output_path = os.path.join(FILTERED_DIR, 'filtrirano.json')
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=4)

    # 5. Izvoz v nov XML
    xml_output_path = os.path.join(FILTERED_DIR, 'filtrirano.xml')
    root_out = ET.Element('filtriraniPodatki')
    for item in filtered:
        node = ET.SubElement(root_out, 'zapis', id=item['playlist_id'])
        for k, v in item.items():
            child = ET.SubElement(node, k)
            child.text = str(v) if v is not None else ""

    ET.ElementTree(root_out).write(xml_output_path, encoding='utf-8', xml_declaration=True)
    print(f"✅ Uspešno izvoženo v '{json_output_path}' in '{xml_output_path}'!\n")


if __name__ == '__main__':
    main()