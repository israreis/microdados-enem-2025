# ENEM 2025 · Análise dos Microdados

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-2.x-150458?logo=pandas&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-relatório-F2C811?logo=powerbi&logoColor=black)
![Dados](https://img.shields.io/badge/dados-INEP%20·%20públicos-0B2545)

Análise de ponta a ponta dos **microdados oficiais do ENEM 2025** (INEP): 4,8 milhões de registros e 2,6 GB de CSVs processados em Python e transformados em um relatório analítico em Power BI.

O projeto cobre o ciclo completo de dados: **ingestão** de arquivos grandes em blocos, **validação** contra os números oficiais, **modelagem dimensional** (esquema em estrela) e **comunicação** dos resultados em um relatório pensado para quem decide.

---

## Principais resultados

| | Achado |
|---|---|
| **67,4%** | Dos 4.810.772 inscritos, só dois terços fizeram as quatro provas objetivas. A abstenção foi de 28,1% no 1º dia e de 32,2% no 2º. |
| **+75 pontos** | Em Ciências da Natureza, alunos de escolas privadas tiveram média 75 pontos acima dos de escolas públicas (552,0 × 477,0). No Piauí, a diferença chega a 99,6. |
| **Federais ≈ privadas** | Escolas federais (535,7) ficam próximas das privadas e mais de 60 pontos acima das estaduais (472,7): "escola pública" esconde realidades muito diferentes. |
| **10 notas 1000** | A redação teve a maior média do exame (580,8), mas apenas 10 notas máximas. A competência mais fraca é a 5 (proposta de intervenção). |
| **6,1% zeradas** | O segundo motivo mais comum de nota zero na redação é a cópia do texto motivador (~55 mil), três vezes mais que a fuga ao tema. |
| **6 em cada 10** | As mulheres são 60% dos inscritos; 21% são treineiros, que fazem a prova antes do último ano do ensino médio. |

> Resultados detalhados, metodologia e o passo a passo do relatório estão em [**projeto-1-analise-powerbi**](projeto-1-analise-powerbi/).

---

## Os dados

Microdados oficiais do INEP, divulgados em 22/06/2026: três CSVs (separador `;`, codificação latin-1).

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `RESULTADOS_2025.csv` | 4,8 mi | presença, notas, respostas questão a questão, redação por competência, UF e rede da escola |
| `PARTICIPANTES_2025.csv` | 4,8 mi | perfil e questionário socioeconômico |
| `ITENS_PROVA_2025.csv` | ~6 mil | parâmetros TRI, gabarito e habilidade de cada questão de cada caderno |

**Mudança em 2025:** por causa da LGPD, perfil e resultados não têm mais chave em comum. Não é possível cruzar nota com renda, sexo, cor/raça ou idade. Toda a análise foi desenhada respeitando essa limitação: os cruzamentos de nota usam UF, rede de ensino e localização da escola, que estão no próprio arquivo de resultados.

---

## Arquitetura

```
CSVs do INEP (2,6 GB)
      │   leitura em blocos de 400 mil linhas (pandas)
      ▼
scripts/02_tabelas_powerbi.py
      │   agrega somas e contagens · valida totais contra os números oficiais
      ▼
Tabelas fato e dimensão (poucos MB)
      │   Power Query · modelo em estrela · medidas DAX
      ▼
Relatório Power BI (5 páginas)
```

As tabelas guardam **somas e contagens**, e não médias prontas: assim, as médias continuam corretas em qualquer combinação de filtros.

**Validação:** o pipeline reproduz exatamente os números oficiais divulgados pelo INEP: 4.810.772 inscritos, 3.244.348 presentes nas quatro provas e 10 redações nota 1000.

---

## Estrutura do repositório

```
├── src/
│   └── enem.py                     leitura em blocos e mapeamento das questões
├── scripts/
│   ├── 00_baixar_dados.py          abre o download do INEP e extrai o zip em data/raw/
│   ├── 01_inspecionar.py           confere colunas e categorias antes da análise
│   ├── 02_tabelas_powerbi.py       agrega os 4,8 mi de registros em tabelas para o Power BI
│   └── 03_base_modelo.py           monta a matriz de acertos por questão (base para modelagem)
├── projeto-1-analise-powerbi/
│   ├── dimensoes/                  tabelas de rótulos (UF, rede, status da redação...)
│   ├── medidas.dax                 todas as medidas do relatório
│   └── tema_enem2025.json          tema visual do Power BI
├── tests/
│   └── gerar_dados_sinteticos.py   base falsa no mesmo formato, para testar sem baixar 3 GB
└── requirements.txt
```

---

## Como reproduzir

Requer Python 3.10+ e Power BI Desktop.

```bash
git clone https://github.com/israreis/microdados-enem-2025.git
cd microdados-enem-2025
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

python scripts/00_baixar_dados.py        # abre o download no navegador e extrai o zip
python scripts/01_inspecionar.py         # confere a estrutura dos arquivos
python scripts/02_tabelas_powerbi.py     # gera as tabelas do relatório (~1 min)
```

Depois, siga o [guia do relatório](projeto-1-analise-powerbi/README.md) para montar o modelo no Power BI.

### Testar sem baixar a base real

```bash
python tests/gerar_dados_sinteticos.py --saida data/raw_sintetico
set ENEM_DATA_RAW=data/raw_sintetico      # Linux/Mac: export ENEM_DATA_RAW=data/raw_sintetico
python scripts/02_tabelas_powerbi.py
```

---

## Limitações

- Perfil e notas não podem ser cruzados (separação feita pelo INEP em 2025, por causa da LGPD).
- A rede de ensino só é conhecida para quem estava no ensino médio; egressos aparecem como "sem escola informada".
- Diferenças entre redes misturam o efeito da escola com o perfil socioeconômico dos alunos, que os dados de 2025 não permitem separar.

---

## Fonte

INEP · [Microdados do ENEM](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem). Dados públicos e anonimizados.

## Autor

**Israel dos Reis Costa Junior** &nbsp; [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/israreis/)
