"""Funções compartilhadas para ler e processar os microdados do ENEM 2025.

Os microdados de 2025 vêm em três arquivos (pasta DADOS do zip do INEP):

- PARTICIPANTES_2025.csv  -> perfil dos inscritos (chave NU_INSCRICAO)
- RESULTADOS_2025.csv     -> presença, notas e respostas (chave NU_SEQUENCIAL)
- ITENS_PROVA_2025.csv    -> parâmetros TRI de cada questão de cada caderno

PARTICIPANTES e RESULTADOS NÃO têm chave em comum (LGPD): não cruze os dois.
Todos os arquivos usam separador ';' e encoding latin-1.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
# ENEM_DATA_RAW permite apontar para outra pasta (ex.: a base sintética de teste)
DATA_RAW = Path(os.environ.get("ENEM_DATA_RAW", RAIZ / "data" / "raw"))
DATA_PROCESSED = RAIZ / "data" / "processed"
SAIDA_POWERBI = RAIZ / "projeto-1-analise-powerbi" / "dados"

SEP = ";"
ENCODING = "latin-1"
CHUNK = 400_000

AREAS = ["CN", "CH", "LC", "MT"]
NOMES_AREAS = {
    "CN": "Ciências da Natureza",
    "CH": "Ciências Humanas",
    "LC": "Linguagens e Códigos",
    "MT": "Matemática",
}
# Áreas em que a string de respostas tem uma posição por questão, sem a
# complicação da língua estrangeira (LC mistura inglês e espanhol).
AREAS_ITENS = ["CN", "CH", "MT"]


def achar_arquivo(nome: str, pasta: Path = DATA_RAW) -> Path:
    """Procura um CSV pelo nome (sem diferenciar maiúsculas) dentro de data/raw."""
    candidatos = [p for p in pasta.rglob("*.csv") if p.name.upper() == nome.upper()]
    if not candidatos:
        raise FileNotFoundError(
            f"Não encontrei {nome} em {pasta}. Rode scripts/00_baixar_dados.py "
            "ou extraia o zip do INEP dentro de data/raw/."
        )
    return candidatos[0]


def colunas(caminho: Path) -> list[str]:
    """Lê só o cabeçalho de um CSV do INEP."""
    return list(pd.read_csv(caminho, sep=SEP, encoding=ENCODING, nrows=0).columns)


def ler_em_blocos(caminho: Path, usecols: list[str], chunksize: int = CHUNK, **kw):
    """Itera sobre o CSV em blocos, lendo apenas as colunas pedidas.

    Colunas de texto (TX_*, SG_*, NO_*, TP_SEXO) ficam como string; o resto
    é inferido pelo pandas.
    """
    disponiveis = set(colunas(caminho))
    faltando = [c for c in usecols if c not in disponiveis]
    if faltando:
        raise KeyError(
            f"Colunas ausentes em {caminho.name}: {faltando}. Rode "
            "scripts/01_inspecionar.py e ajuste os nomes em src/enem.py."
        )
    dtype = {c: "string" for c in usecols if c.startswith(("TX_", "SG_", "NO_")) or c == "TP_SEXO"}
    return pd.read_csv(
        caminho, sep=SEP, encoding=ENCODING, usecols=usecols, dtype=dtype,
        chunksize=chunksize, low_memory=False, **kw,
    )


def matriz_caracteres(textos: pd.Series, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Converte uma série de strings de tamanho n numa matriz (linhas x n) de bytes.

    Retorna (matriz, mascara_valida). Linhas nulas ou com tamanho diferente de n
    ficam fora da matriz (mascara False).
    """
    s = textos.astype("string")
    valida = (s.str.len() == n).fillna(False).to_numpy()
    validos = s[valida].tolist()
    if not validos:
        return np.empty((0, n), dtype=np.uint8), valida
    buf = "".join(validos).encode(ENCODING)
    return np.frombuffer(buf, dtype=np.uint8).reshape(len(validos), n), valida


def carregar_itens(caminho: Path | None = None) -> pd.DataFrame:
    """Lê ITENS_PROVA_2025.csv e padroniza os tipos."""
    caminho = caminho or achar_arquivo("ITENS_PROVA_2025.csv")
    itens = pd.read_csv(caminho, sep=SEP, encoding=ENCODING, low_memory=False)
    for c in ["NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C"]:
        if c in itens:
            itens[c] = pd.to_numeric(itens[c], errors="coerce")
    if "IN_ITEM_ABAN" not in itens:
        itens["IN_ITEM_ABAN"] = 0
    itens["IN_ITEM_ABAN"] = itens["IN_ITEM_ABAN"].fillna(0).astype(int)
    return itens


def mapa_posicoes(itens: pd.DataFrame, area: str) -> dict[int, pd.DataFrame]:
    """Para cada caderno (CO_PROVA) da área, devolve os itens ordenados por posição.

    A i-ésima letra de TX_RESPOSTAS_<area> corresponde ao i-ésimo item desta tabela.
    """
    sub = itens[itens["SG_AREA"] == area].sort_values(["CO_PROVA", "CO_POSICAO"])
    return {int(cp): g.reset_index(drop=True) for cp, g in sub.groupby("CO_PROVA")}
