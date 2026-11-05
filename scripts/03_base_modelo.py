"""Projeto 2: monta a base de modelagem a partir das respostas de uma área.

Para cada participante presente, transforma TX_RESPOSTAS_<area> numa linha com
uma coluna 0/1 por questão (identificada pelo CO_ITEM, que é o mesmo em todas
as cores de caderno), mais a nota TRI oficial, a UF e a rede de ensino.

Só entram cadernos da aplicação principal: os que têm exatamente o mesmo
conjunto de questões do caderno mais respondido. Itens anulados são removidos.

Uso:
    python scripts/03_base_modelo.py                    # MT, amostra de 500 mil
    python scripts/03_base_modelo.py --area CN --amostra 300000
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from enem import (  # noqa: E402
    DATA_PROCESSED, achar_arquivo, carregar_itens, ler_em_blocos, mapa_posicoes, matriz_caracteres,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="MT", choices=["CN", "CH", "MT"])
    ap.add_argument("--amostra", type=int, default=500_000, help="nº máximo de participantes")
    ap.add_argument("--linhas", type=int, default=None, help="limita linhas lidas (teste)")
    args = ap.parse_args()
    a = args.area
    t0 = time.time()

    itens = carregar_itens()
    mapa = mapa_posicoes(itens, a)
    resultados = achar_arquivo("RESULTADOS_2025.csv")

    # 1ª passada (leve): qual caderno foi o mais respondido?
    contagem = pd.Series(dtype=float)
    for b in ler_em_blocos(resultados, [f"CO_PROVA_{a}"], nrows=args.linhas):
        contagem = contagem.add(b[f"CO_PROVA_{a}"].value_counts(), fill_value=0)
    principal = int(contagem.idxmax())
    conjunto = set(mapa[principal]["CO_ITEM"])
    cadernos = [cp for cp, t in mapa.items() if set(t["CO_ITEM"]) == conjunto]
    print(f"Caderno mais respondido: {principal}. Cadernos com as mesmas questões: {cadernos}")

    ref = mapa[principal]
    validos = ref.loc[ref["IN_ITEM_ABAN"] == 0, "CO_ITEM"].tolist()
    print(f"{len(ref)} questões, {len(ref) - len(validos)} anulada(s) removida(s)")
    n = len(ref)
    total = contagem[contagem.index.isin(cadernos)].sum()
    frac = min(1.0, 1.1 * args.amostra / total)  # amostra já na leitura, poupa memória

    # 2ª passada: monta a matriz de acertos
    usar = [f"CO_PROVA_{a}", f"TP_PRESENCA_{a}", f"NU_NOTA_{a}", f"TX_RESPOSTAS_{a}",
            f"TX_GABARITO_{a}", "SG_UF_PROVA", "TP_DEPENDENCIA_ADM_ESC"]
    partes = []
    for b in ler_em_blocos(resultados, usar, nrows=args.linhas):
        mask = ((b[f"TP_PRESENCA_{a}"] == 1) & b[f"CO_PROVA_{a}"].isin(cadernos)
                & (b[f"NU_NOTA_{a}"] > 0)
                & (b[f"TX_RESPOSTAS_{a}"].str.len() == n) & (b[f"TX_GABARITO_{a}"].str.len() == n))
        b = b[mask.fillna(False).astype(bool)]
        if frac < 1:
            b = b.sample(frac=frac, random_state=42)
        for cp, g in b.groupby(f"CO_PROVA_{a}"):
            resp, _ = matriz_caracteres(g[f"TX_RESPOSTAS_{a}"], n)
            gab, _ = matriz_caracteres(g[f"TX_GABARITO_{a}"], n)
            acerto = pd.DataFrame((resp == gab).astype(np.int8),
                                  columns=[f"item_{i}" for i in mapa[int(cp)]["CO_ITEM"]], index=g.index)
            acerto["brancos"] = ((resp == ord(".")) | (resp == ord(" "))).sum(axis=1)
            acerto["nota"] = g[f"NU_NOTA_{a}"]
            acerto["caderno"] = int(cp)
            acerto["uf"] = g["SG_UF_PROVA"]
            acerto["rede"] = g["TP_DEPENDENCIA_ADM_ESC"].fillna(0).astype(int)
            partes.append(acerto)
        print(f"  {sum(len(p) for p in partes):,} participantes ({time.time() - t0:,.0f}s)")

    base = pd.concat(partes, ignore_index=True)
    base = base.drop(columns=[f"item_{i}" for i in conjunto if i not in validos])
    if len(base) > args.amostra:
        base = base.sample(args.amostra, random_state=42).reset_index(drop=True)

    params = (itens[itens["CO_ITEM"].isin(validos)]
              .drop_duplicates("CO_ITEM")[["CO_ITEM", "CO_HABILIDADE", "NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C"]])

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    base.to_pickle(DATA_PROCESSED / f"modelo_{a}.pkl")
    params.to_csv(DATA_PROCESSED / f"itens_{a}.csv", index=False)
    print(f"Base salva: {len(base):,} linhas x {base.shape[1]} colunas "
          f"-> {DATA_PROCESSED / f'modelo_{a}.pkl'} ({time.time() - t0:,.0f}s)")


if __name__ == "__main__":
    main()
