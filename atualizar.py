#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jornal Helena - coletor anti-bloqueio.

Uso:
    python3 atualizar.py              # uma rodada e sai (é o que o GitHub Actions faz a cada 5 min)
    python3 atualizar.py --loop       # roda sozinho, uma rodada a cada 5 minutos
    python3 atualizar.py --tudo       # atualiza as 25 cidades de uma vez (para encher o JSON na 1a vez)
    python3 atualizar.py --bloco 2    # força um bloco (0 a 4) em vez de usar o relógio

Só usa a biblioteca padrão do Python 3 (nada para instalar).

RODÍZIO SEQUENCIAL (sem aleatório):
    bloco = (minuto_atual // 5) % 5
    Cada rodada atualiza só 5 cidades: bloco 0 = cidades 0-4, bloco 1 = cidades 5-9, ...
    As outras 20 cidades continuam como estavam no noticias.json.
    Por rodada: 6 pedidos nacionais + 5 de notícias + 5 de vagas + 1 do PCI Concursos.

ANTI-BLOQUEIO:
    User-Agent Mozilla/5.0, 3 s entre pedidos, timeout de 15 s e a rodada para se der
    3 erros seguidos. Se parar, o que já estava salvo é mantido.

O noticias.json é lido e regravado por inteiro: a chave "ofertas" (seus links de
afiliado) e qualquer outra chave que você acrescentar nunca são apagadas.
Todas as datas são salvas em ISO UTC.
"""

import argparse
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "noticias.json")

POR_FONTE = 5          # notícias por órgão / por cidade / vagas por cidade
PAUSA = 3              # segundos entre pedidos
TIMEOUT = 15           # segundos de espera por resposta
ERROS_SEGUIDOS = 3     # erros seguidos que param a rodada
BLOCOS = 5             # o rodízio tem 5 blocos...
POR_BLOCO = 5          # ...de 5 cidades cada (5 x 5 = 25 cidades)

GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
PCI_URL = "https://www.pciconcursos.com.br/rss/sudeste.xml"
SITES_VAGAS = "site:indeed.com.br OR site:gupy.io OR site:vagas.com.br"
FALLBACK_VAGAS = ["Juiz de Fora", "Ubá"]   # cidades cujas vagas são replicadas quando a cidade não tem nenhuma

# Capa nacional. "rss": feeds oficiais, tentados em ordem. "site": plano B (Google News só desse site).
# Se um endereço oficial mudar, ajuste aqui.
ORGAOS = [
    {"nome": "Câmara dos Deputados",
     "rss": ["https://www.camara.leg.br/rss/noticias",
             "https://www.camara.leg.br/noticias/rss/ultimas-noticias"],
     "site": "camara.leg.br"},
    {"nome": "Senado Federal",
     "rss": ["https://www12.senado.leg.br/noticias/rss"],
     "site": "senado.leg.br"},
    {"nome": "STF",
     "rss": ["https://noticias.stf.jus.br/feed/"],
     "site": "stf.jus.br"},
    {"nome": "TSE",
     "rss": ["https://www.tse.jus.br/comunicacao/noticias/rss"],
     "site": "tse.jus.br"},
    {"nome": "Itamaraty",
     "rss": ["https://www.gov.br/mre/pt-br/assuntos/noticias/RSS"],
     "site": "gov.br/mre"},
    {"nome": "Agência Brasil",
     "rss": ["https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml"],
     "site": "agenciabrasil.ebc.com.br"},
]

# As 25 cidades NA ORDEM DO RODÍZIO (índices 0 a 24). Não mude a ordem sem querer:
# o bloco 0 pega as cidades 0-4, o bloco 1 as 5-9, e assim por diante.
CIDADES = [
    "Juiz de Fora", "Ubá", "Muriaé", "Cataguases", "Leopoldina",
    "Viçosa", "Barbacena", "São João del Rei", "Conselheiro Lafaiete", "Santos Dumont",
    "Visconde do Rio Branco", "Ponte Nova", "Manhuaçu", "Caratinga", "Além Paraíba",
    "Astolfo Dutra", "Recreio", "Miraí", "Laranjal", "Guidoval",
    "Rodeiro", "Argirita", "Palma", "Pirapetinga", "Descoberto",
]


class Bloqueio(Exception):
    """O servidor recusou o pedido (limite, captcha ou erro de servidor)."""


class Abortar(Exception):
    """3 erros seguidos: a etapa para e os dados antigos ficam."""


# ---------------------------------------------------------------- utilidades

def agora():
    return datetime.now(timezone.utc)


def iso(d=None):
    return (d or agora()).isoformat(timespec="seconds")


def log(*partes):
    print(agora().strftime("[%H:%M:%S UTC]"), *partes, flush=True)


def sem_acento(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def limpar(texto):
    texto = html.unescape(texto or "")
    texto = re.sub(r"<[^>]+>", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def parse_data(texto):
    """Converte data de RSS (RFC 822) ou Atom (ISO 8601) para ISO em UTC."""
    if not texto:
        return None
    texto = texto.strip()
    try:
        d = parsedate_to_datetime(texto)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return iso(d.astimezone(timezone.utc))


def baixar(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (403, 429, 503):
            raise Bloqueio("HTTP %d" % e.code)
        raise


def tag(el):
    return el.tag.rsplit("}", 1)[-1].lower()


def filho(el, nome):
    for f in el:
        if tag(f) == nome:
            return f
    return None


def ler_feed(conteudo):
    """Lê RSS 2.0 ou Atom e devolve lista de dicts: titulo, link, data, fonte."""
    if isinstance(conteudo, bytes) and b"<html" in conteudo[:500].lower():
        raise Bloqueio("resposta em HTML (captcha ou página de erro)")
    raiz = ET.fromstring(conteudo)
    itens = []
    for el in raiz.iter():
        if tag(el) not in ("item", "entry"):
            continue
        t = filho(el, "title")
        titulo = limpar(t.text if t is not None else "")
        link = ""
        l = filho(el, "link")
        if l is not None:
            link = (l.get("href") or l.text or "").strip()
        d = None
        for nome in ("pubdate", "published", "updated", "date"):
            d = filho(el, nome)   # sem "or": elemento sem filhos conta como falso
            if d is not None:
                break
        data = parse_data(d.text if d is not None else "")
        s = filho(el, "source")
        fonte = limpar(s.text) if s is not None and s.text else ""
        if titulo and link.startswith(("http://", "https://")):
            itens.append({"titulo": titulo, "link": link, "data": data, "fonte": fonte})
    return itens


def tirar_fonte_do_titulo(titulo, fonte):
    """O Google News termina os títulos com ' - Nome da Fonte'. Remove isso."""
    if fonte and titulo.endswith(" - " + fonte):
        return titulo[: -len(fonte) - 3].strip()
    if " - " in titulo:
        corpo, _, resto = titulo.rpartition(" - ")
        if corpo and len(resto) <= 40:
            return corpo.strip()
    return titulo


def melhores(itens, limite=POR_FONTE):
    """Remove repetidos e fica com os mais recentes."""
    vistos, unicos = set(), []
    for it in itens:
        chave = re.sub(r"\W+", "", it["titulo"].lower())[:80]
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(it)
    unicos.sort(key=lambda i: i.get("data") or "", reverse=True)
    return unicos[:limite]


# ---------------------------------------------------------- pedidos e pausas

class Sessao:
    """Faz os pedidos com pausa de 3 s e para depois de 3 erros seguidos."""

    _ultimo = 0.0   # compartilhado: a pausa vale entre quaisquer dois pedidos

    def __init__(self, nome):
        self.nome = nome
        self.seguidos = 0

    def pedir(self, url):
        espera = PAUSA - (time.time() - Sessao._ultimo)
        if espera > 0:
            time.sleep(espera)
        Sessao._ultimo = time.time()
        try:
            itens = ler_feed(baixar(url))
        except Exception as e:
            self.seguidos += 1
            log("   erro (%d/%d) em %s: %s" % (self.seguidos, ERROS_SEGUIDOS, self.nome, e))
            if self.seguidos >= ERROS_SEGUIDOS:
                raise Abortar(self.nome)
            return None   # None = erro; [] = o feed respondeu, mas sem itens
        self.seguidos = 0
        return itens


# ------------------------------------------------------------- consultas

def url_cidade(cidade):
    # "Ubá" MG  (só a cidade entre aspas)
    return GOOGLE_NEWS.format(q=quote_plus('"%s" MG' % cidade))


def url_vagas(cidade):
    # site:indeed.com.br OR site:gupy.io OR site:vagas.com.br ("Ubá" MG)
    # A cidade fica entre aspas e o MG FORA das aspas: assim pega "Ubá - MG" e "Ubá, MG".
    return GOOGLE_NEWS.format(q=quote_plus('%s ("%s" MG)' % (SITES_VAGAS, cidade)))


def url_site(site):
    return GOOGLE_NEWS.format(q=quote_plus("site:%s" % site))


# ------------------------------------------------------------------- coleta

def coletar_nacional(sessao, itens):
    for orgao in ORGAOS:
        brutos = None
        for url in orgao["rss"]:
            brutos = sessao.pedir(url)
            if brutos:
                break
        if not brutos:
            log("   %s: feed oficial sem resposta, tentando plano B (Google News)" % orgao["nome"])
            brutos = sessao.pedir(url_site(orgao["site"]))
        novos = [{
            "tipo": "nacional", "orgao": orgao["nome"], "titulo": b["titulo"],
            "fonte": orgao["nome"], "data": b["data"], "data_coleta": iso(), "link": b["link"],
        } for b in melhores(brutos or [])]
        if novos:
            itens = trocar(itens, "nacional", "orgao", orgao["nome"], novos)
            log("  %s: %d notícias" % (orgao["nome"], len(novos)))
        else:
            log("  %s: sem novidades, mantendo as antigas" % orgao["nome"])
    return itens


def itens_google(brutos, tipo, cidade):
    saida = []
    for b in melhores(brutos or []):
        fonte = b["fonte"] or "Google Notícias"
        titulo = tirar_fonte_do_titulo(b["titulo"], b["fonte"])
        item = {"tipo": tipo, "cidade": cidade, "titulo": titulo, "fonte": fonte,
                "data": b["data"], "data_coleta": iso(), "link": b["link"]}
        if tipo == "vaga":
            item["cargo"] = titulo
        saida.append(item)
    return saida


def vagas_pci(pci, cidade):
    """Segunda fonte: RSS do PCI Concursos Sudeste, filtrando pelo nome da cidade sem acento."""
    padrao = re.compile(r"\b%s\b" % re.escape(sem_acento(cidade)))
    return [{"tipo": "vaga", "cidade": cidade, "cargo": p["titulo"], "titulo": p["titulo"],
             "fonte": "PCI Concursos", "data": p["data"], "data_coleta": iso(), "link": p["link"]}
            for p in pci if padrao.search(sem_acento(p["titulo"]))]


def vagas_da_regiao(itens, cidade):
    """Fallback: copia as vagas de Juiz de Fora e Ubá, marcadas como 'Vagas na região'."""
    origem = [i for i in itens if i.get("tipo") == "vaga" and i.get("cidade") in FALLBACK_VAGAS
              and not i.get("regiao")]
    return [dict(i, cidade=cidade, regiao=True, cidade_origem=i["cidade"])
            for i in melhores(origem)]


def coletar_cidades(sessao, itens, cidades):
    pci = sessao.pedir(PCI_URL)
    if pci is None:
        log("   PCI Concursos indisponível nesta rodada")
    for cid in cidades:
        log("  %s" % cid)
        noticias = sessao.pedir(url_cidade(cid))
        novas = itens_google(noticias, "cidade", cid)
        if novas:
            itens = trocar(itens, "cidade", "cidade", cid, novas)

        brutas = sessao.pedir(url_vagas(cid))
        vagas = itens_google(brutas, "vaga", cid) + vagas_pci(pci or [], cid)
        vagas = melhores(vagas)
        if brutas is not None:   # None = o Google deu erro: não troca nada
            if not vagas and cid not in FALLBACK_VAGAS:
                vagas = vagas_da_regiao(itens, cid)
        if vagas:
            itens = trocar(itens, "vaga", "cidade", cid, vagas)
        log("     %d notícias, %d vagas%s" % (len(novas), len(vagas),
            " (vagas na região)" if vagas and vagas[0].get("regiao") else ""))
    return itens


def trocar(itens, tipo, chave, valor, novos):
    """Troca os itens de um grupo (tipo + órgão/cidade) pelos novos, mantendo o resto."""
    resto = [i for i in itens if not (i.get("tipo") == tipo and i.get(chave) == valor)]
    return resto + novos


# ------------------------------------------------------------------ arquivo

def carregar(caminho):
    """Lê o noticias.json. Se ele existir mas estiver quebrado (vírgula sobrando numa
    edição à mão, por exemplo), PARA, em vez de sobrescrever e perder suas ofertas."""
    if not os.path.exists(caminho):
        return {"atualizado_em": None, "cidades": CIDADES, "ofertas": [], "itens": []}
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        if not isinstance(dados, dict) or not isinstance(dados.get("itens"), list):
            raise ValueError('falta a lista "itens"')
        return dados
    except ValueError as e:
        log("ERRO: noticias.json está com defeito (%s). Nada foi alterado. "
            "Corrija o arquivo (veja o README) e rode de novo." % e)
        sys.exit(1)


def salvar(caminho, dados):
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, caminho)   # troca atômica: o site nunca lê o arquivo pela metade


# ------------------------------------------------------------------- rodada

def bloco_atual():
    return (agora().minute // 5) % BLOCOS


def cidades_do_bloco(bloco):
    return CIDADES[bloco * POR_BLOCO:(bloco + 1) * POR_BLOCO]


def rodada(caminho, bloco=None, tudo=False):
    dados = carregar(caminho)
    itens = [i for i in dados["itens"]
             if i.get("tipo") not in ("cidade", "vaga") or i.get("cidade") in CIDADES]

    # 1) capa nacional: sempre (erros aqui não impedem a coleta das cidades)
    log("Capa nacional...")
    try:
        itens = coletar_nacional(Sessao("nacional"), itens)
    except Abortar:
        log("3 erros seguidos na capa nacional: parando só esta etapa, dados antigos mantidos.")

    # 2) cidades do bloco (ou todas, com --tudo)
    if tudo:
        escolhidas, rotulo = CIDADES, "todas as cidades"
    else:
        b = bloco_atual() if bloco is None else bloco
        escolhidas, rotulo = cidades_do_bloco(b), "bloco %d (cidades %d-%d)" % (b, b * POR_BLOCO, b * POR_BLOCO + POR_BLOCO - 1)
        dados["ultimo_bloco"] = b
    log("Cidades: %s -> %s" % (rotulo, ", ".join(escolhidas)))
    try:
        itens = coletar_cidades(Sessao("cidades"), itens, escolhidas)
    except Abortar:
        log("3 erros seguidos: rodada de cidades interrompida, dados antigos mantidos.")

    # 3) salva (sempre, para o "atualizado_em" provar que o coletor está vivo)
    dados["itens"] = itens
    dados["cidades"] = CIDADES
    dados["orgaos"] = [o["nome"] for o in ORGAOS]
    dados["atualizado_em"] = iso()
    salvar(caminho, dados)
    log("noticias.json salvo (%d itens, %d ofertas preservadas)." % (len(itens), len(dados.get("ofertas", []))))


def main():
    p = argparse.ArgumentParser(description="Coletor do Jornal Helena")
    p.add_argument("--loop", action="store_true", help="roda para sempre (uma rodada a cada --intervalo s)")
    p.add_argument("--intervalo", type=int, default=300, help="segundos entre rodadas no --loop (padrão 300)")
    p.add_argument("--tudo", action="store_true", help="atualiza as 25 cidades de uma vez")
    p.add_argument("--bloco", type=int, choices=range(BLOCOS), help="força um bloco de 0 a 4")
    p.add_argument("--saida", default=ARQUIVO, help="caminho do noticias.json")
    a = p.parse_args()
    try:
        while True:
            rodada(a.saida, a.bloco, a.tudo)
            if not a.loop:
                break
            log("Próxima rodada em %d s (Ctrl+C para parar)." % a.intervalo)
            time.sleep(a.intervalo)
    except KeyboardInterrupt:
        log("Parado pelo usuário.")


if __name__ == "__main__":
    main()
