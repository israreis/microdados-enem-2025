# Projeto 1 · ENEM 2025 em números (Power BI)

> **Pergunta central:** onde e para quem o ENEM 2025 foi mais difícil — e o que isso diz sobre a desigualdade no ensino médio brasileiro?

Relatório em Power BI construído sobre os microdados oficiais do INEP (4,8 milhões de inscritos). Os dados brutos (2,6 GB) são processados em Python e agregados em tabelas pequenas, que o Power BI carrega em segundos.

## Perguntas que o relatório responde

1. **Participação:** quantos inscritos realmente fizeram as provas? Quanto se perde do 1º para o 2º dia, e em quais estados?
2. **Desigualdade:** qual a diferença de nota entre escolas privadas e públicas em cada UF e área? Onde o gap é maior?
3. **Redação:** em qual das 5 competências os participantes mais perdem pontos? Por que tantas redações são zeradas?
4. **Questões:** quais foram as questões mais difíceis e mais fáceis? A dificuldade oficial (parâmetro *b* da TRI) bate com o % de acerto real?
5. **Perfil:** quem são os inscritos (idade, sexo, cor/raça, renda)?

> ⚠️ **Limitação importante dos dados de 2025:** o INEP separou o perfil dos participantes (`PARTICIPANTES_2025.csv`) dos resultados (`RESULTADOS_2025.csv`) sem chave em comum, por causa da LGPD. Por isso **o perfil não pode ser cruzado com as notas** — a página 5 é descritiva e independente. Os cruzamentos de nota são feitos por UF, rede de ensino (federal, estadual, municipal, privada) e localização da escola, que estão no arquivo de resultados.

## Como reproduzir

```bash
# na raiz do repositório
python scripts/00_baixar_dados.py        # baixa e extrai (~1 GB)
python scripts/01_inspecionar.py         # confere colunas e categorias
python scripts/02_tabelas_powerbi.py     # gera os CSVs em projeto-1-analise-powerbi/dados/
```

## Tabelas geradas (`dados/`)

| Tabela | Grão (uma linha por...) | Uso |
|---|---|---|
| `fato_resultados` | UF × rede × localização | presença, somas de notas e redação |
| `fato_distribuicao` | área × faixa de 20 pontos × rede | histogramas |
| `fato_redacao_status` | UF × rede × situação da redação | motivos de nota zero |
| `fato_itens` | questão × rede | % de acerto, parâmetros TRI, habilidade |
| `fato_perfil` | combinação de características | perfil dos inscritos |
| `dim_*` | rótulo | UF/região, rede, localização, área, status, sexo, cor/raça, faixa etária |

As tabelas guardam **somas e contagens**, não médias prontas. Assim a média continua correta em qualquer filtro (média de médias daria resultado errado).

## Montando o relatório

### 1. Importar
*Obter dados > Texto/CSV* para cada arquivo de `dados/` (ou *Pasta* e combinar). Confira que `TP_DEPENDENCIA_ADM_ESC` veio como número inteiro em todas as tabelas.

### 2. Relacionamentos (Exibição de modelo)

```
dim_uf[SG_UF_PROVA]                   1 ── * fato_resultados, fato_redacao_status, fato_perfil
dim_rede[TP_DEPENDENCIA_ADM_ESC]      1 ── * fato_resultados, fato_distribuicao, fato_redacao_status, fato_itens
dim_localizacao[TP_LOCALIZACAO_ESC]   1 ── * fato_resultados
dim_status_redacao[TP_STATUS_REDACAO] 1 ── * fato_redacao_status
dim_area[SG_AREA]                     1 ── * fato_itens[SG_AREA], fato_distribuicao[area]
dim_faixa_etaria / dim_sexo / dim_cor_raca  1 ── * fato_perfil
```

`dim_area` fica **sem** relação com `fato_resultados`: ela funciona como segmentador da medida *Média da área selecionada*.

### 3. Medidas
Todas estão em [`medidas.dax`](medidas.dax), prontas para colar.

### 4. Páginas sugeridas

| Página | Visuais |
|---|---|
| **1. Visão geral** | Cartões: Inscritos, Taxa de presença, Abstenção dia 1 e dia 2, Média geral. Barras com a média das 5 provas. Mapa coroplético (ou barras) por UF com *Média da área selecionada*. |
| **2. Desigualdade** | Barras agrupadas por rede. Barras horizontais do *Gap privada - pública* por UF, ordenadas. Matriz UF × rede. Histograma (`fato_distribuicao`) com rede na legenda e *% na faixa* no eixo Y — mostra as curvas deslocadas. |
| **3. Redação** | Barras com as 5 competências (máx. 200 cada). Rosca ou barras de *% do status* (tirando "Sem problemas"). Cartões: Redações nota 1000, % 900+, % zerada. |
| **4. Questões** | Dispersão: eixo X = `NU_PARAM_B` (dificuldade TRI), eixo Y = *% Acerto*, detalhes = `CO_ITEM`, legenda = área. Tabela top 10 mais difíceis/fáceis. Barras de *% Acerto* por `CO_HABILIDADE`. Destaque para itens com `IN_ITEM_ABAN = 1` (anulados). |
| **5. Quem fez o ENEM** | Pirâmide/barras por faixa etária e sexo, cor/raça, renda familiar (`Q006`, conferir rótulos no dicionário). Nota explicando por que não há cruzamento com notas. |
| **6. Conclusões** | 3 a 5 achados em texto curto, cada um com o número que o sustenta. É a página que recrutadores mais leem. |

Segmentadores comuns: Região/UF, Rede, Localização.

### 5. Publicar no portfólio
- Salve o `.pbix` nesta pasta (`enem2025.pbix`).
- Exporte cada página como imagem para `imagens/` e use no README.
- Se tiver conta do Power BI Service, use *Publicar na Web* e coloque o link aqui.

## Checagem de sanidade

Ao rodar com a base completa, o script imprime os totais. Valores divulgados publicamente para comparar: **4.810.772 inscritos**, **3.244.348 presentes em todas as provas objetivas** (≈ 67,4%) e **10 redações nota 1000**. Se os seus números baterem, o pipeline está correto.

## Rótulos

Os códigos em `dimensoes/` seguem o dicionário de dados do INEP das edições anteriores. Abra o dicionário que vem no zip de 2025 (`DICIONÁRIO/`) e confirme as categorias — o `01_inspecionar.py` lista todos os códigos encontrados em `data/processed/schema_2025.md`.
