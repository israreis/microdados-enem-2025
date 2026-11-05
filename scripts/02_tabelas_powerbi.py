"""Projeto 1: gera as tabelas agregadas que alimentam o relatório no Power BI.

Lê RESULTADOS_2025.csv (2,1 GB) em blocos, sem carregar tudo na memória, e
grava CSVs pequenos em projeto-1-analise-powerbi/dados/:

- fato_resultados.csv      presença e somas de notas por UF x rede x localização
- fato_distribuicao.csv    histograma das notas (faixas de 20 pontos) por área e rede
- fato_redacao_status.csv  situação da redação por UF e rede
- fato_itens.csv           % de acerto de cada questão (CN, CH, MT) por rede, com parâmetros TRI
- fato_perfil.csv          perfil dos inscritos (vem de PARTICIPANTES, NÃO cruza com notas)
- dim_*.csv                tabelas de rótulos

Uso:
    python scripts/02_tabelas_powerbi.py            # base completa (~10-20 min)
    python scripts/02_tabelas_powerbi.py --linhas 300000   # teste rápido
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from enem import (  # noqa: E402
    AREAS, AREAS_ITENS, CHUNK, NOMES_AREAS, RAIZ, SAIDA_POWERBI,
    achar_arquivo, carregar_itens, colunas, ler_em_blocos, matriz_caracteres,
)

CHAVES = ["SG_UF_PROVA", "TP_DEPENDENCIA_ADM_ESC", "TP_LOCALIZACAO_ESC"]
COMPS = [f"NU_NOTA_COMP{i}" for i in range(1, 6)]
FAIXA = 20  # largura das faixas do histograma


def preparar_bloco(df: pd.DataFrame) -> pd.DataFrame:
    for c in ["TP_DEPENDENCIA_ADM_ESC", "TP_LOCALIZACAO_ESC"]:
        if c in df:
            df[c] = df[c].fillna(0).astype(int)  # 0 = sem escola informada
        else:
            df[c] = 0
    df["SG_UF_PROVA"] = df["SG_UF_PROVA"].fillna("NI")
    return df


def agregar_resultados(df: pd.DataFrame) -> pd.DataFrame:
    m = pd.DataFrame(index=df.index)
    m["inscritos"] = 1
    for a in AREAS:
        pres = df[f"TP_PRESENCA_{a}"]
        m[f"presentes_{a}"] = (pres == 1).astype(int)
        m[f"eliminados_{a}"] = (pres == 2).astype(int)
        nota = df[f"NU_NOTA_{a}"].where(pres == 1)
        valida = nota.notna() & (nota > 0)
        m[f"n_nota_{a}"] = valida.astype(int)
        m[f"soma_nota_{a}"] = nota.where(valida, 0)
        m[f"soma_quad_nota_{a}"] = (nota ** 2).where(valida, 0)
    m["presentes_dia1"] = ((df["TP_PRESENCA_LC"] == 1) & (df["TP_PRESENCA_CH"] == 1)).astype(int)
    m["presentes_dia2"] = ((df["TP_PRESENCA_CN"] == 1) & (df["TP_PRESENCA_MT"] == 1)).astype(int)
    m["presentes_todas"] = (m["presentes_dia1"] & m["presentes_dia2"]).astype(int)

    red = df["NU_NOTA_REDACAO"]
    tem_red = red.notna() & (df["TP_PRESENCA_LC"] == 1)
    m["n_redacao"] = tem_red.astype(int)
    m["soma_redacao"] = red.where(tem_red, 0)
    m["redacao_mil"] = (tem_red & (red == 1000)).astype(int)
    m["redacao_zero"] = (tem_red & (red == 0)).astype(int)
    m["redacao_900_mais"] = (tem_red & (red >= 900)).astype(int)
    for i, c in enumerate(COMPS, 1):
        m[f"soma_comp{i}"] = df[c].where(tem_red, 0).fillna(0)

    m[CHAVES] = df[CHAVES]
    return m.groupby(CHAVES, as_index=False).sum()


def agregar_distribuicao(df: pd.DataFrame) -> pd.DataFrame:
    partes = []
    for a in AREAS + ["REDACAO"]:
        col = f"NU_NOTA_{a}"
        pres = df["TP_PRESENCA_LC"] if a == "REDACAO" else df[f"TP_PRESENCA_{a}"]
        nota = df[col].where(pres == 1).dropna()
        if a != "REDACAO":
            nota = nota[nota > 0]
        faixa = (np.floor(nota / FAIXA) * FAIXA).clip(upper=1000 - FAIXA).astype(int)
        t = pd.DataFrame({"area": a, "faixa_inicio": faixa,
                          "TP_DEPENDENCIA_ADM_ESC": df.loc[faixa.index, "TP_DEPENDENCIA_ADM_ESC"]})
        partes.append(t.value_counts().rename("participantes").reset_index())
    return pd.concat(partes)


def agregar_status_redacao(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["TP_PRESENCA_LC"] == 1]
    return (sub.groupby(["SG_UF_PROVA", "TP_DEPENDENCIA_ADM_ESC", "TP_STATUS_REDACAO"], dropna=False)
               .size().rename("participantes").reset_index())


def agregar_itens(df: pd.DataFrame, n_itens: dict[str, int]) -> pd.DataFrame:
    """Conta respostas, acertos e brancos por caderno x posição x rede."""
    partes = []
    for a in AREAS_ITENS:
        n = n_itens[a]
        sub = df[df[f"TP_PRESENCA_{a}"] == 1]
        if sub.empty:
            continue
        ok = ((sub[f"TX_RESPOSTAS_{a}"].str.len() == n) & (sub[f"TX_GABARITO_{a}"].str.len() == n)
              & sub[f"CO_PROVA_{a}"].notna()).fillna(False).to_numpy()
        resp, _ = matriz_caracteres(sub.loc[ok, f"TX_RESPOSTAS_{a}"], n)
        gab, _ = matriz_caracteres(sub.loc[ok, f"TX_GABARITO_{a}"], n)
        acerto = resp == gab
        branco = (resp == ord(".")) | (resp == ord(" "))
        chave = sub.loc[ok, [f"CO_PROVA_{a}", "TP_DEPENDENCIA_ADM_ESC"]].astype(int).to_numpy()
        grupos = pd.DataFrame(chave, columns=["CO_PROVA", "rede"]).groupby(["CO_PROVA", "rede"]).indices
        for (cp, rede), idx in grupos.items():
            partes.append(pd.DataFrame({
                "SG_AREA": a, "CO_PROVA": cp, "TP_DEPENDENCIA_ADM_ESC": rede,
                "ordem": np.arange(1, n + 1),
                "respostas": len(idx),
                "acertos": acerto[idx].sum(axis=0),
                "brancos": branco[idx].sum(axis=0),
            }))
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes)


def finalizar_itens(brutos: pd.DataFrame, itens: pd.DataFrame) -> pd.DataFrame:
    """Liga cada (caderno, ordem) ao item real e soma o mesmo item entre cadernos."""
    it = itens[itens["SG_AREA"].isin(AREAS_ITENS)].sort_values(["CO_PROVA", "CO_POSICAO"]).copy()
    it["ordem"] = it.groupby("CO_PROVA").cumcount() + 1
    base = brutos.groupby(["SG_AREA", "CO_PROVA", "ordem", "TP_DEPENDENCIA_ADM_ESC"], as_index=False).sum()
    base = base.merge(it, on=["SG_AREA", "CO_PROVA", "ordem"], how="inner")
    cols_item = ["CO_ITEM", "SG_AREA", "CO_HABILIDADE", "NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C", "IN_ITEM_ABAN"]
    cols_item = [c for c in cols_item if c in base]
    out = base.groupby(cols_item + ["TP_DEPENDENCIA_ADM_ESC"], as_index=False, dropna=False)[
        ["respostas", "acertos", "brancos"]].sum()
    # posição do item no caderno mais respondido, para facilitar a consulta à prova
    pos = (base.groupby(["CO_ITEM", "CO_POSICAO"])["respostas"].sum().reset_index()
               .sort_values("respostas").drop_duplicates("CO_ITEM", keep="last")[["CO_ITEM", "CO_POSICAO"]])
    return out.merge(pos, on="CO_ITEM", how="left")


def gerar_perfil(limite: int | None) -> pd.DataFrame | None:
    try:
        caminho = achar_arquivo("PARTICIPANTES_2025.csv")
    except FileNotFoundError as e:
        print("  (pulando perfil)", e)
        return None
    disp = colunas(caminho)
    desejadas = ["SG_UF_PROVA", "TP_FAIXA_ETARIA", "TP_SEXO", "TP_COR_RACA",
                 "TP_ST_CONCLUSAO", "TP_ESCOLA", "IN_TREINEIRO", "Q006", "Q005"]
    usar = [c for c in desejadas if c in disp]
    print(f"  colunas de perfil usadas: {usar}")
    partes = []
    for i, bloco in enumerate(ler_em_blocos(caminho, usar, nrows=limite)):
        partes.append(bloco.fillna(-1).value_counts().rename("inscritos").reset_index())
    perfil = pd.concat(partes)
    return perfil.groupby(usar, as_index=False)["inscritos"].sum()


def escrever_dimensoes() -> None:
    origem = RAIZ / "projeto-1-analise-powerbi" / "dimensoes"
    for f in origem.glob("dim_*.csv"):
        shutil.copy(f, SAIDA_POWERBI / f.name)
    pd.DataFrame({"SG_AREA": list(NOMES_AREAS) + ["REDACAO"],
                  "area": list(NOMES_AREAS.values()) + ["Redação"]}).to_csv(
        SAIDA_POWERBI / "dim_area.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--linhas", type=int, default=None, help="limita as linhas lidas (teste)")
    args = ap.parse_args()
    SAIDA_POWERBI.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    caminho = achar_arquivo("RESULTADOS_2025.csv")
    disp = set(colunas(caminho))
    usar = (["SG_UF_PROVA", "TP_STATUS_REDACAO", "NU_NOTA_REDACAO"] + COMPS
            + [c for c in ["TP_DEPENDENCIA_ADM_ESC", "TP_LOCALIZACAO_ESC"] if c in disp]
            + [f"TP_PRESENCA_{a}" for a in AREAS] + [f"NU_NOTA_{a}" for a in AREAS]
            + [f"{p}_{a}" for a in AREAS_ITENS for p in ("CO_PROVA", "TX_RESPOSTAS", "TX_GABARITO")])

    itens = carregar_itens()
    n_itens = {a: int(itens[itens["SG_AREA"] == a].groupby("CO_PROVA").size().mode().iloc[0])
               for a in AREAS_ITENS}
    print(f"Questões por caderno: {n_itens}")

    res, dist, red, its = [], [], [], []
    lidas = 0
    for bloco in ler_em_blocos(caminho, usar, chunksize=CHUNK, nrows=args.linhas):
        bloco = preparar_bloco(bloco)
        res.append(agregar_resultados(bloco))
        dist.append(agregar_distribuicao(bloco))
        red.append(agregar_status_redacao(bloco))
        its.append(agregar_itens(bloco, n_itens))
        lidas += len(bloco)
        print(f"  {lidas:,} linhas processadas ({time.time() - t0:,.0f}s)")

    def soma(partes, chaves):
        return pd.concat(partes).groupby(chaves, as_index=False, dropna=False).sum()

    fato = soma(res, CHAVES)
    fato.to_csv(SAIDA_POWERBI / "fato_resultados.csv", index=False, encoding="utf-8-sig")
    soma(dist, ["area", "faixa_inicio", "TP_DEPENDENCIA_ADM_ESC"]).to_csv(
        SAIDA_POWERBI / "fato_distribuicao.csv", index=False, encoding="utf-8-sig")
    soma(red, ["SG_UF_PROVA", "TP_DEPENDENCIA_ADM_ESC", "TP_STATUS_REDACAO"]).to_csv(
        SAIDA_POWERBI / "fato_redacao_status.csv", index=False, encoding="utf-8-sig")
    fato_itens = finalizar_itens(pd.concat(its), itens)
    fato_itens.to_csv(SAIDA_POWERBI / "fato_itens.csv", index=False, encoding="utf-8-sig")

    print("Gerando perfil dos inscritos (PARTICIPANTES)...")
    perfil = gerar_perfil(args.linhas)
    if perfil is not None:
        perfil.to_csv(SAIDA_POWERBI / "fato_perfil.csv", index=False, encoding="utf-8-sig")

    escrever_dimensoes()

    print(f"\nPronto em {time.time() - t0:,.0f}s. Conferência rápida:")
    print(f"  inscritos: {fato['inscritos'].sum():,}")
    print(f"  presentes nas 4 provas: {fato['presentes_todas'].sum():,} "
          f"({fato['presentes_todas'].sum() / fato['inscritos'].sum():.1%})")
    for a in AREAS:
        print(f"  média {a}: {fato[f'soma_nota_{a}'].sum() / fato[f'n_nota_{a}'].sum():.1f}")
    print(f"  redações nota mil: {fato['redacao_mil'].sum():,}")
    print(f"  itens com estatística: {fato_itens['CO_ITEM'].nunique()}")
    print(f"Arquivos em {SAIDA_POWERBI}")


if __name__ == "__main__":
    main()
