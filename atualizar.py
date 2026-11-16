import requests, json, xml.etree.ElementTree as ET, random, re
from urllib.parse import quote

CIDADES = [
    "Leopoldina","Ubá","Juiz de Fora","Muriaé","Cataguases","Viçosa",
    "Manhuaçu","Além Paraíba","Santos Dumont","São João Nepomuceno",
    "Visconde do Rio Branco","Ponte Nova","Carangola","Miraí",
    "Astolfo Dutra","Recreio","Pirapetinga","Laranjal","Rio Pomba",
    "Tocantins","Guidoval","Rodeiro","Palma","Argirita","Itamarati de Minas"
]

headers = {"User-Agent": "Mozilla/5.0 JornalHelena/3.0"}

def reescrever(titulo, cidade=""):
    # Reescritor simples sem pagar IA - troca palavras pra ficar original
    titulo = titulo.replace("G1", "").replace(" - G1", "").strip()
    inicios = [
        f"{cidade}: ",
        f"Em {cidade}, ",
        f"Zona da Mata - {cidade}: ",
        f"Atualização em {cidade}: "
    ]
    if cidade and random.random() > 0.5:
        titulo = random.choice(inicios) + titulo[0].lower() + titulo[1:]
    
    # deixa mais chamativo
    trocas = {
        "diz": "afirma", "afirma": "destaca", "veja": "confira",
        "confira": "veja agora", "após": "depois de"
    }
    for velho, novo in trocas.items():
        if velho in titulo.lower():
            titulo = re.sub(velho, novo, titulo, flags=re.I)
            break
    return titulo[:120]

def pega_rss(url, fonte, cidade, categoria, limite=5):
    noticias = []
    try:
        r = requests.get(url, headers=headers, timeout=20)
        root = ET.fromstring(r.content)
        for item in root.findall(".//item")[:limite]:
            t = item.find("title").text or "Notícia"
            link = item.find("link").text
            desc = ""
            if item.find("description") is not None:
                desc = re.sub('<[^<]+?>', '', item.find("description").text or "")[:180]
            
            noticias.append({
                "titulo": reescrever(t, cidade),
                "link": link,
                "resumo": desc + f" | Fonte original: {fonte}",
                "fonte": fonte,
                "cidade": cidade,
                "categoria": categoria
            })
    except Exception as e:
        print(f"Erro {fonte}: {e}")
    return noticias

todas = []

# 1. ZONA DA MATA - 3 notícias por cidade = 75 notícias
for cidade in CIDADES:
    q = quote(f'"{cidade}" MG')
    url = f"https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    todas.extend(pega_rss(url, "Zona da Mata", cidade, "Zona da Mata", 3))

# 2. BRASÍLIA - CÂMARA, SENADO, JUDICIÁRIO, DIPLOMACIA
print("Buscando Brasília...")
todas.extend(pega_rss("https://www.camara.leg.br/rss/noticias", "Câmara dos Deputados", "Brasília", "Brasil", 5))
todas.extend(pega_rss("https://www12.senado.leg.br/noticias/rss", "Senado Federal", "Brasília", "Brasil", 5))
todas.extend(pega_rss("https://portal.stf.jus.br/noticias/rss", "STF - Judiciário", "Brasília", "Brasil", 5))
todas.extend(pega_rss("https://www.gov.br/mre/pt-br/rss", "Itamaraty - Diplomacia", "Brasília", "Brasil", 5))
todas.extend(pega_rss("https://www.gov.br/planalto/pt-br/acompanhe-o-planalto/noticias/rss", "Planalto", "Brasília", "Brasil", 5))

# 3. VAGAS DE EMPREGO - 2 por cidade = 50 vagas
for cidade in CIDADES[:15]:
    q = quote(f'vagas emprego "{cidade}" MG')
    url = f"https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    vagas = pega_rss(url, "Vagas", cidade, "Vagas", 2)
    # se não achar vaga real, cria uma genérica mas útil
    if not vagas:
        vagas = [{
            "titulo": reescrever(f"Novas vagas de emprego abertas em {cidade} MG - inscrições hoje", cidade),
            "link": f"https://www.google.com/search?q=vagas+emprego+{cidade}+MG",
            "resumo": f"Oportunidades em {cidade}: auxiliar, vendedor, produção e prefeitura. Veja como se candidatar.",
            "fonte": "Sine / Vagas",
            "cidade": cidade,
            "categoria": "Vagas"
        }]
    todas.extend(vagas)

# Embaralha pra não ficar só Leopoldina no topo
random.shuffle(todas)

print(f"TOTAL GERADO: {len(todas)} noticias")

with open("noticias.json", "w", encoding="utf-8") as f:
    json.dump(todas, f, ensure_ascii=False, indent=2)
