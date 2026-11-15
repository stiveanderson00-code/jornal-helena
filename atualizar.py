import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import re

FEEDS = [
    ("https://g1.globo.com/rss/g1/zona-da-mata/", "G1 Zona da Mata"),
    ("https://g1.globo.com/rss/g1/minas-gerais/", "G1 Minas"),
]

def limpar(text):
    return re.sub(r'<[^>]+>', '', text)[:250]

def detectar_cidade(texto):
    t = texto.lower()
    if "juiz de fora" in t: return "Juiz de Fora"
    if "uba" in t or "ubá" in t: return "Ubá"
    if "muria" in t: return "Muriaé"
    if "leopoldina" in t: return "Leopoldina"
    if "cataguases" in t: return "Cataguases"
    if "vicosa" in t or "viçosa" in t: return "Viçosa"
    return "Juiz de Fora"

noticias = []

for url, fonte in FEEDS:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        for item in root.findall('.//item')[:12]:
            title = item.findtext('title') or ""
            link = item.findtext('link') or ""
            desc = item.findtext('description') or ""
            resumo = limpar(desc)
            cidade = detectar_cidade(title + " " + resumo)
            noticias.append({
                "titulo": title,
                "link": link,
                "resumo": resumo,
                "fonte": fonte,
                "cidade": cidade,
                "horario": datetime.now().isoformat(),
                "categoria": "Zona da Mata"
            })
    except Exception as e:
        print(f"Erro {url}: {e}")

vistos=set()
final=[]
for n in noticias:
    if n["titulo"] not in vistos:
        vistos.add(n["titulo"])
        final.append(n)

with open("noticias.json","w",encoding="utf-8") as f:
    json.dump(final[:20], f, ensure_ascii=False, indent=2)
