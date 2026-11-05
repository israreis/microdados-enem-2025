# ENEM 2025 · Análise dos MicroDados

Projeto construído com a base pública — os **microdados do ENEM 2025** (INEP, 4,8 milhões de inscritos) — mostrando o ciclo completo: engenharia dos dados brutos, análise para tomada de decisão e modelagem.

| | Projeto | Pergunta | Ferramentas |
|---|---|---|---|
| 📊 | [**ENEM 2025 em números**](projeto-1-analise-powerbi/) | Onde e para quem o ENEM 2025 foi mais difícil? | Python, Power BI, DAX |


## Os dados

Microdados oficiais do INEP, divulgados em 22/06/2026: três CSVs (`;`, latin-1) que somam ~2,6 GB.

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `RESULTADOS_2025.csv` | 4,8 mi | presença, notas, respostas questão a questão, redação por competência, UF e rede da escola |
| `PARTICIPANTES_2025.csv` | 4,8 mi | perfil e questionário socioeconômico |
| `ITENS_PROVA_2025.csv` | ~6 mil | parâmetros TRI, gabarito e habilidade de cada questão de cada caderno |

**Mudança de 2025:** por causa da LGPD, perfil e resultados não têm mais chave em comum. Não é possível cruzar nota com renda, sexo, cor/raça ou idade; os dois projetos foram desenhados respeitando essa limitação.

## Estrutura

```
├── src/enem.py                      funções de leitura em blocos e mapeamento das questões
├── scripts/
│   ├── 00_baixar_dados.py           baixa e extrai o zip do INEP para data/raw/
│   ├── 01_inspecionar.py            confere colunas e categorias (data/processed/schema_2025.md)
│   ├── 02_tabelas_powerbi.py        agrega os 4,8 mi de linhas em tabelas para o Power BI
│   └── 03_base_modelo.py            monta a matriz de acertos para o modelo
├── projeto-1-analise-powerbi/       relatório, medidas DAX, tabelas de rótulos
├── projeto-2-ciencia-de-dados/      notebook (.py com células), figuras, resultados
└── tests/gerar_dados_sinteticos.py  base falsa no mesmo formato, para testar sem baixar 3 GB
```

## Como rodar

Requer Python 3.10+.

```bash
git clone https://github.com/israreis/dados.git
cd dados
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

python scripts/00_baixar_dados.py
python scripts/01_inspecionar.py
python scripts/02_tabelas_powerbi.py     # Projeto 1
python scripts/03_base_modelo.py         # Projeto 2
```

Os scripts leem os CSVs em blocos, então rodam num notebook comum com 8 GB de RAM.

### Testar sem a base real

```bash
python tests/gerar_dados_sinteticos.py --saida data/raw_sintetico
set ENEM_DATA_RAW=data/raw_sintetico      # Linux/Mac: export ENEM_DATA_RAW=data/raw_sintetico
python scripts/02_tabelas_powerbi.py
```

## Fonte

INEP — [Microdados do ENEM](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem). Dados públicos e anonimizados.
