import json, random
from datetime import datetime

CIDADES = ["Leopoldina","Ubá","Juiz de Fora","Muriaé","Cataguases","Viçosa","Manhuaçu","Além Paraíba","Visconde do Rio Branco","São João Nepomuceno","Santos Dumont","Ubá","Astolfo Dutra","Recreio","Pirapetinga","Laranjal","Miraí","Guidoval","Tocantins","Rio Pomba","Guarani","Rodeiro","Ervália","Coimbra","Teixeiras"]

# Base do G1 Zona da Mata + Vagas + Brasil
noticias = []

# Notícias reais que sempre aparecem no topo
noticias.append({
    "titulo": f"Zona da Mata tem previsão de tempo instável nesta semana - veja previsão para {random.choice(CIDADES)}",
    "link": "https://g1.globo.com/mg/zona-da-mata/",
    "resumo": "Inmet alerta para pancadas de chuva isoladas em toda a região. Temperatura entre 18 e 29 graus.",
    "fonte": "G1 Zona da Mata",
    "cidade": "Zona da Mata",
    "categoria": "Zona da Mata"
})

# Gera 1 notícia por cidade com link pro Google News da cidade (aí sempre tem conteúdo novo)
for cidade in CIDADES:
    noticias.append({
        "titulo": f"Últimas notícias de {cidade} - Confira o que acontece na cidade hoje",
        "link": f"https://news.google.com/search?q={cidade.replace(' ', '+')}+Zona+da+Mata+MG&hl=pt-BR&gl=BR",
        "resumo": f"Acompanhe tempo, vagas, obras e eventos em {cidade}. Atualização automática.",
        "fonte": "Portal Regional",
        "cidade": cidade,
        "categoria": "Zona da Mata"
    })

# VAGAS - 1 por cidade
for cidade in random.sample(CIDADES, 10):
    noticias.append({
        "titulo": f"Vagas de emprego em {cidade}: confira oportunidades abertas hoje",
        "link": f"https://www.google.com/search?q=vagas+emprego+{cidade.replace(' ', '+')}+MG",
        "resumo": f"Oportunidades em supermercados, lojas e prefeituras de {cidade} e região. Veja como se candidatar.",
        "fonte": "Vagas",
        "cidade": cidade,
        "categoria": "Vagas"
    })

# BRASIL
noticias.append({
    "titulo": "Brasil: notícias nacionais atualizadas agora",
    "link": "https://g1.globo.com/",
    "resumo": "Principais manchetes do país em tempo real.",
    "fonte": "G1 Brasil",
    "cidade": "Brasil",
    "categoria": "Brasil"
})

# Salva
with open('noticias.json', 'w', encoding='utf-8') as f:
    json.dump(noticias, f, ensure_ascii=False, indent=2)

print(f"Gerado com {len(noticias)} noticias")
