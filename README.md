# Jornal Helena - Zona da Mata em Tempo Real

25 cidades da Zona da Mata em um só lugar, com 4 abas:

- **ZONA DA MATA**: notícias por cidade (5 por cidade).
- **VAGAS**: vagas por cidade (5 por cidade). Quando uma cidade não tem vaga própria, aparecem as de Juiz de Fora e Ubá com a tag **"Vagas na região"**.
- **BRASIL**: 5 notícias de cada fonte oficial (Câmara, Senado, STF, TSE, Itamaraty, Agência Brasil).
- **OFERTAS**: cartões de produtos com os seus links de afiliado (Magalu, Amazon, Shopee, Mercado Livre).

Cada notícia mostra cidade, fonte, tempo, "Abrir na fonte ↗" e "Compartilhar no WhatsApp". No topo há a previsão do tempo de Leopoldina (Open-Meteo, sem chave). Se os dados passarem de 1 hora, aparece uma faixa vermelha de "Coleta parada".

## Como funciona

```
atualizar.py  ->  noticias.json  ->  index.html
 (coletor)         (dados)           (o site, relê o JSON a cada 2 min)
```

### O rodízio de cidades

O Google bloqueia quem faz muitos pedidos seguidos. Por isso, cada rodada atualiza só **5 das 25 cidades**, em sequência (sem sorteio):

```
bloco = (minuto_atual // 5) % 5
bloco 0 = cidades 0-4   (Juiz de Fora, Ubá, Muriaé, Cataguases, Leopoldina)
bloco 1 = cidades 5-9   (Viçosa, Barbacena, São João del Rei, Conselheiro Lafaiete, Santos Dumont)
bloco 2 = cidades 10-14 (Visconde do Rio Branco, Ponte Nova, Manhuaçu, Caratinga, Além Paraíba)
bloco 3 = cidades 15-19 (Astolfo Dutra, Recreio, Miraí, Laranjal, Guidoval)
bloco 4 = cidades 20-24 (Rodeiro, Argirita, Palma, Pirapetinga, Descoberto)
```

As outras 20 cidades continuam como estavam no `noticias.json`. A capa do Brasil atualiza em **toda** rodada. Cada rodada faz 6 pedidos nacionais + 5 de notícias + 5 de vagas + 1 do PCI Concursos = 17 pedidos.

**Na prática:** a capa do Brasil atualiza a cada 5 minutos, mas cada cidade é atualizada **a cada 25 minutos** (5 blocos x 5 min). O texto "Atualização a cada 5 min" do site vale para a capa nacional, não para cada cidade. O GitHub também pode atrasar execuções; se uma rodada atrasar para o minuto de outro bloco, o bloco anterior só volta na próxima volta do rodízio.

### Anti-bloqueio

User-Agent `Mozilla/5.0`, 3 segundos entre pedidos, tempo máximo de 15 segundos por pedido e a etapa para depois de 3 erros seguidos (os dados que já estavam salvos ficam). A capa nacional e as cidades contam erros separadamente, então um feed oficial fora do ar não impede a coleta das cidades.

### De onde vêm os dados

| O quê | Fonte |
|---|---|
| Brasil | RSS oficiais. Se um feed não responder, o coletor usa o Google News restrito ao site do órgão |
| Notícias da cidade | Google News RSS: `q="NOME_DA_CIDADE" MG` |
| Vagas | Google News RSS: `site:indeed.com.br OR site:gupy.io OR site:vagas.com.br ("NOME_DA_CIDADE" MG)` e o RSS do PCI Concursos Sudeste, filtrado pelo nome da cidade sem acento |
| Fallback de vagas | se a cidade não tiver nenhuma, copia as vagas de Juiz de Fora e Ubá com a tag "Vagas na região" |
| Clima | Open-Meteo, direto do navegador de quem abre o site |

Nas vagas, o `MG` fica **fora** das aspas de propósito: assim pega "Ubá - MG" e "Ubá, MG". Os endereços dos feeds do STF, TSE, Itamaraty e Agência Brasil ficam na lista `ORGAOS` no topo do `atualizar.py`; se algum mudar, é só corrigir lá.

O `noticias.json` é lido e regravado por inteiro: a chave **`"ofertas"`** (seus links de afiliado) nunca é apagada nem alterada. Todas as datas são salvas em ISO UTC (o site mostra no horário de Brasília).

## Arquivos no repositório

```
seu-repositorio/
├── index.html
├── atualizar.py
├── noticias.json
├── README.md
└── .github/
    └── workflows/
        └── atualizar.yml     <- o arquivo atualizar.yml vai dentro desta pasta
```

> O `noticias.json` que vem junto tem **exemplos** (marcados "[Exemplo]"). Cada cidade passa a ter dados reais quando o rodízio chega nela. Para encher tudo de uma vez, use a execução manual com "tudo" (passo 6 abaixo). As 12 ofertas de exemplo ficam até você trocá-las, e os preços delas são fictícios.

## Publicar no GitHub Pages

**O repositório precisa ser PÚBLICO.** O GitHub Pages gratuito exige repositório público, e em repositório público o GitHub Actions não cobra os minutos de execução. Em repositório privado a conta gratuita tem só **2.000 minutos por mês**, e uma execução a cada 5 minutos gasta isso em poucos dias.

1. Crie um repositório **público** no GitHub (por exemplo `jornal-helena`).
2. Envie `index.html`, `atualizar.py`, `noticias.json` e `README.md` para a raiz (**Add file → Upload files**).
3. **Add file → Create new file**, digite `.github/workflows/atualizar.yml` como nome (as barras criam as pastas) e cole o conteúdo do `atualizar.yml`.
4. **Settings → Actions → General → Workflow permissions**: marque **Read and write permissions** e salve.
5. **Settings → Pages**: *Deploy from a branch*, branch `main`, pasta `/ (root)`, e salve.
6. Aba **Actions → Atualizar Jornal Helena → Run workflow**, marque **tudo** e rode. Isso atualiza as 25 cidades de uma vez (leva uns 3 minutos).
7. O site fica em `https://SEU-USUARIO.github.io/jornal-helena/`.

Depois disso o GitHub roda sozinho a cada 5 minutos (`*/5 * * * *`), uma execução por vez, e só faz commit se o `noticias.json` mudou. Como o campo `atualizado_em` muda a cada rodada, haverá cerca de 288 commits por dia; é normal.

O agendamento do GitHub pode atrasar alguns minutos em horário de pico, e o Pages leva cerca de 1 minuto para publicar cada commit. Se aparecer a faixa vermelha "Coleta parada", olhe a aba **Actions** (agendamentos podem ser pausados em repositórios sem atividade).

## Seu WhatsApp e o preço do anúncio

No `index.html`, logo no começo do `<script>`, está o bloco `CONFIG`:

```js
var CONFIG = {
  whatsappAnuncio: '5532999999999',      // seu WhatsApp com 55 + DDD, só números
  precoAnuncio: 'R$ 150/mês por cidade',
  cidadesBanner: ['Leopoldina', 'Cataguases', 'Ubá', 'Juiz de Fora']
};
```

Troque o número (o de exemplo **não é um número real**). Os 4 banners de exemplo levam o anunciante direto para o seu WhatsApp, já com a cidade na mensagem.

## Como trocar os links de afiliado (Magalu, Amazon, Shopee, Mercado Livre)

As ofertas ficam na chave `"ofertas"`, no começo do `noticias.json`:

```json
{
 "loja": "Magalu",
 "titulo": "Smart TV 50 polegadas 4K",
 "preco_antigo": 3299.0,
 "preco_novo": 2399.0,
 "link_afiliado": "https://www.magazineluiza.com.br/",
 "exemplo": true
}
```

Para trocar:

1. No GitHub, abra `noticias.json` e clique no lápis (**Edit**).
2. Troque o valor de `"link_afiliado"` pelo **seu link de afiliado** daquele produto.
3. Ajuste `"titulo"`, `"preco_antigo"` e `"preco_novo"` (números com ponto, sem R$). O desconto em % e o formato em reais o site calcula sozinho.
4. **Apague a linha `"exemplo": true,`**: assim o cartão deixa de mostrar o selo "exemplo: preço fictício".
5. Em `"loja"` use `Magalu`, `Amazon`, `Shopee` ou `Mercado Livre`.
6. Clique em **Commit changes**. O site atualiza sozinho em poucos minutos.

Para **adicionar** uma oferta, copie um bloco inteiro (de `{` até `}`, com a vírgula depois) e cole junto às outras. Para **remover**, apague o bloco.

Cuidados ao editar o `noticias.json`:

- O JSON é rígido: uma vírgula sobrando ou faltando quebra o arquivo. Se isso acontecer, o **coletor recusa gravar** (para não perder suas ofertas) e o site mostra "Não foi possível carregar". Corrija a vírgula ou as aspas e a próxima execução volta ao normal. Dica: cole o conteúdo em um validador de JSON antes de salvar.
- Como o robô faz commit a cada 5 minutos, o GitHub pode avisar que o arquivo mudou enquanto você editava. Se isso acontecer, copie a sua alteração, recarregue a página e refaça a edição rapidamente.

## Como conseguir os links de afiliado

Cada loja tem um programa próprio e gratuito. Procure pelo nome do programa e **confira as regras e a aprovação no site oficial de cada um**, porque mudam com frequência:

| Loja | Programa |
|---|---|
| Magalu | Parceiro Magalu |
| Amazon | Amazon Associados |
| Shopee | Shopee Afiliados |
| Mercado Livre | Mercado Livre Afiliados |

Em geral: criar a conta no programa, informar o site (a URL do GitHub Pages) e esperar a aprovação. Depois, a plataforma do programa gera o link de afiliado de qualquer produto, e você cola esse link no campo `"link_afiliado"`.

Pontos de atenção:

- Alguns programas pedem que o site já tenha conteúdo e visitas antes de aprovar. A Amazon, segundo guias de terceiros, exige algumas vendas em até 180 dias para manter a conta ativa. Confirme no site deles.
- O site já avisa no rodapé e na aba OFERTAS que pode receber comissão. Mantenha o aviso: os programas costumam exigir transparência.
- Os preços da página são digitados por você e podem ficar desatualizados. Evite exibir preço que a loja já não pratica.

## Rodar no seu computador

Precisa só do Python 3.

```bash
python3 atualizar.py              # uma rodada (capa do Brasil + o bloco do minuto atual)
python3 atualizar.py --tudo       # atualiza as 25 cidades de uma vez
python3 atualizar.py --bloco 2    # força o bloco 2 (cidades 10-14)
python3 atualizar.py --loop       # roda sozinho, uma rodada a cada 5 minutos (Ctrl+C para parar)
```

Para ver o site, abra **outro terminal** na mesma pasta:

```bash
python3 -m http.server 8000
```

e acesse `http://localhost:8000` (abrir o `index.html` direto no navegador não funciona: ele bloqueia a leitura do `noticias.json`).

## Dicas de uso no site

- Digite a cidade sem acento: "uba" acha Ubá, "sao joao" acha São João del Rei. O site já muda para ZONA DA MATA.
- Digite "vagas muriae" para ir direto às vagas de Muriaé, ou "oferta geladeira" para a aba OFERTAS.
- Os endereços aceitam `#zona`, `#vagas`, `#brasil` e `#ofertas` para abrir direto numa aba.
