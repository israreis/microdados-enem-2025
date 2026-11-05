"""Confere a estrutura real dos arquivos antes de qualquer análise.

Gera data/processed/schema_2025.md com: colunas de cada arquivo, exemplo de
valores e as categorias encontradas nas colunas TP_* / Q0xx. Também avisa se
alguma coluna que os outros scripts usam não existir com o nome esperado.

Uso:
    python scripts/01_inspecionar.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from enem import DATA_PROCESSED, ENCODING, SEP, achar_arquivo  # noqa: E402

ESPERADAS = {
    "RESULTADOS_2025.csv": [
        "NU_SEQUENCIAL", "SG_UF_PROVA", "TP_DEPENDENCIA_ADM_ESC", "TP_LOCALIZACAO_ESC",
        "TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT",
        "CO_PROVA_CN", "CO_PROVA_CH", "CO_PROVA_MT",
        "NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO",
        "NU_NOTA_COMP1", "NU_NOTA_COMP2", "NU_NOTA_COMP3", "NU_NOTA_COMP4", "NU_NOTA_COMP5",
        "TP_STATUS_REDACAO",
        "TX_RESPOSTAS_CN", "TX_RESPOSTAS_CH", "TX_RESPOSTAS_MT",
        "TX_GABARITO_CN", "TX_GABARITO_CH", "TX_GABARITO_MT",
    ],
    "ITENS_PROVA_2025.csv": [
        "CO_POSICAO", "SG_AREA", "CO_ITEM", "TX_GABARITO", "CO_HABILIDADE",
        "IN_ITEM_ABAN", "NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C", "CO_PROVA",
    ],
    "PARTICIPANTES_2025.csv": [
        "NU_INSCRICAO", "TP_FAIXA_ETARIA", "TP_SEXO", "TP_COR_RACA", "SG_UF_PROVA",
    ],
}
AMOSTRA = 200_000


def main() -> None:
    faltam = []
    for nome in ESPERADAS:
        try:
            achar_arquivo(nome)
        except FileNotFoundError:
            faltam.append(nome)
    if faltam:
        sys.exit(f"Arquivos não encontrados em data/raw/: {', '.join(faltam)}\n"
                 "Rode antes: python scripts/00_baixar_dados.py")

    linhas = ["# Estrutura dos microdados ENEM 2025\n",
              f"Categorias calculadas sobre as primeiras {AMOSTRA:,} linhas de cada arquivo.\n"]
    problemas = []

    for nome, esperadas in ESPERADAS.items():
        try:
            caminho = achar_arquivo(nome)
        except FileNotFoundError as e:
            problemas.append(str(e))
            continue
        df = pd.read_csv(caminho, sep=SEP, encoding=ENCODING, nrows=AMOSTRA, low_memory=False)
        print(f"\n== {nome}: {df.shape[1]} colunas")
        linhas.append(f"\n## {nome}\n\n{df.shape[1]} colunas.\n\n| coluna | tipo | exemplo | nulos (amostra) |\n|---|---|---|---|")
        for c in df.columns:
            ex = df[c].dropna()
            exemplo = str(ex.iloc[0])[:40] if len(ex) else ""
            linhas.append(f"| {c} | {df[c].dtype} | {exemplo} | {df[c].isna().mean():.1%} |")

        cats = [c for c in df.columns if (c.startswith("TP_") or c.startswith("Q0") or c.startswith("IN_")) and df[c].nunique() <= 30]
        if cats:
            linhas.append("\n### Categorias\n")
            for c in cats:
                vc = df[c].value_counts(dropna=False).sort_index()
                linhas.append(f"- **{c}**: " + ", ".join(f"`{k}` ({v:,})" for k, v in vc.items()))

        faltando = [c for c in esperadas if c not in df.columns]
        if faltando:
            problemas.append(f"{nome}: colunas esperadas não encontradas -> {faltando}")
        for c in df.columns:
            if c.startswith("NU_NOTA") and df[c].dtype == object:
                problemas.append(f"{nome}: {c} veio como texto (decimal com vírgula?). Use decimal=',' na leitura.")

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    saida = DATA_PROCESSED / "schema_2025.md"
    saida.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nRelatório salvo em {saida}")

    if problemas:
        print("\nATENÇÃO:")
        for p in problemas:
            print(" -", p)
        print("Ajuste os nomes nos scripts antes de seguir.")
    else:
        print("\nTudo certo: todas as colunas esperadas existem.")


if __name__ == "__main__":
    main()
