"""Gera uma base FALSA, pequena, no mesmo formato dos microdados ENEM 2025.

Serve só para testar os scripts sem baixar os 3 GB do INEP. As respostas são
simuladas com o modelo TRI de 3 parâmetros, então os padrões (acerto x nota,
dificuldade x % de acerto) se parecem com os reais, mas os números não são reais.

Uso:
    python tests/gerar_dados_sinteticos.py --saida data/raw_sintetico --n 60000
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
UFS = ["SP", "MG", "BA", "RJ", "PE", "CE", "PA", "RS", "PR", "GO", "AM", "DF"]
INICIO = {"LC": 1, "CH": 46, "CN": 91, "MT": 136}
CORES = ["AZUL", "AMARELA", "BRANCA", "ROSA"]


def gerar_itens() -> pd.DataFrame:
    linhas = []
    co_prova, co_item = 1500, 100000
    for area, ini in INICIO.items():
        for aplicacao in ("regular", "reaplicacao"):
            # 45 itens por aplicação, com parâmetros TRI plausíveis
            a = rng.lognormal(0.7, 0.3, 45)
            b = rng.normal(1.0, 1.0, 45)
            c = rng.uniform(0.1, 0.25, 45)
            gab = rng.choice(list("ABCDE"), 45)
            hab = rng.integers(1, 31, 45)
            ids = np.arange(co_item, co_item + 45)
            co_item += 45
            aban = np.zeros(45, int)
            if aplicacao == "regular" and area == "MT":
                aban[7] = 1  # um item anulado, como acontece às vezes
            for cor in (CORES if aplicacao == "regular" else CORES[:1]):
                ordem = rng.permutation(45)
                for pos, k in enumerate(ordem):
                    linhas.append(dict(CO_POSICAO=ini + pos, SG_AREA=area, CO_ITEM=ids[k],
                                       TX_GABARITO=gab[k], CO_HABILIDADE=hab[k], IN_ITEM_ABAN=aban[k],
                                       TX_MOTIVO_ABAN=None, NU_PARAM_A=round(a[k], 5),
                                       NU_PARAM_B=round(b[k], 5), NU_PARAM_C=round(c[k], 5),
                                       TX_COR=cor, CO_PROVA=co_prova, TP_LINGUA=None,
                                       IN_ITEM_ADAPTADO=0))
                co_prova += 1
    return pd.DataFrame(linhas)


def gerar_resultados(n: int, itens: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame({"NU_SEQUENCIAL": np.arange(1, n + 1), "NU_ANO": 2025})
    df["SG_UF_PROVA"] = rng.choice(UFS, n)
    tem_escola = rng.random(n) < 0.4
    rede = rng.choice([1, 2, 3, 4], n, p=[0.03, 0.72, 0.02, 0.23]).astype(float)
    df["TP_DEPENDENCIA_ADM_ESC"] = np.where(tem_escola, rede, np.nan)
    df["TP_LOCALIZACAO_ESC"] = np.where(tem_escola, rng.choice([1.0, 2.0], n, p=[0.93, 0.07]), np.nan)
    efeito_rede = np.select([rede == 4, rede == 1], [0.9, 0.8], 0.0) * tem_escola
    theta_geral = rng.normal(0, 1, n) + efeito_rede

    dia1 = np.where(rng.random(n) < 0.72, 1, 0)
    dia1 = np.where((dia1 == 1) & (rng.random(n) < 0.002), 2, dia1)
    dia2 = np.where(dia1 == 1, np.where(rng.random(n) < 0.93, 1, 0), 0)
    pres = {"LC": dia1, "CH": dia1, "CN": dia2, "MT": dia2}

    for area in ["CN", "CH", "LC", "MT"]:
        df[f"TP_PRESENCA_{area}"] = pres[area]
        reg = itens[(itens.SG_AREA == area)]
        cadernos = sorted(reg.CO_PROVA.unique())
        pesos = np.array([0.24] * 4 + [0.04])
        caderno = rng.choice(cadernos, n, p=pesos / pesos.sum())
        theta = 0.75 * theta_geral + rng.normal(0, 0.65, n)
        resp = np.full((n, 45), ".", dtype="<U1")
        gab = np.full((n, 45), "", dtype="<U1")
        acertou_ponderado = np.zeros(n)
        for cp in cadernos:
            idx = np.where(caderno == cp)[0]
            it = reg[reg.CO_PROVA == cp].sort_values("CO_POSICAO")
            a, b, c = (it[x].to_numpy() for x in ["NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C"])
            p = c + (1 - c) / (1 + np.exp(-1.7 * a * (theta[idx, None] - b)))
            acerto = rng.random(p.shape) < p
            g = it.TX_GABARITO.to_numpy()
            erradas = np.array([[x for x in "ABCDE" if x != gg] for gg in g])
            escolha_errada = erradas[np.arange(45), rng.integers(0, 4, (len(idx), 45))]
            r = np.where(acerto, g, escolha_errada)
            r[rng.random(r.shape) < 0.01] = "."
            resp[idx] = r
            gab[idx] = g
            acertou_ponderado[idx] = (acerto * a).sum(1)
        presente = pres[area] == 1
        df[f"CO_PROVA_{area}"] = np.where(presente, caderno, np.nan)
        # nota simulada: depende do theta e um pouco do padrão de acertos
        nota = 500 + 100 * theta + 4 * (acertou_ponderado - acertou_ponderado.mean()) + rng.normal(0, 15, n)
        df[f"NU_NOTA_{area}"] = np.where(presente, np.clip(nota, 300, 950).round(1), np.nan)
        df[f"TX_RESPOSTAS_{area}"] = np.where(presente, ["".join(x) for x in resp], None)
        df[f"TX_GABARITO_{area}"] = np.where(presente, ["".join(x) for x in gab], None)

    df["TP_LINGUA"] = np.where(dia1 == 1, rng.choice([0, 1], n), np.nan)
    status = rng.choice([1, 2, 3, 4, 6, 7, 8, 9], n, p=[0.93, 0.005, 0.005, 0.02, 0.02, 0.005, 0.01, 0.005])
    df["TP_STATUS_REDACAO"] = np.where(dia1 == 1, status, np.nan)
    comp_base = np.clip(np.round((5 + 1.2 * theta_geral[:, None] + rng.normal(0, 0.8, (n, 5))) / 1) * 20, 0, 200)
    comp_base = np.clip(np.round(comp_base / 40) * 40, 0, 200)
    comp_base[status != 1] = 0
    for i in range(5):
        df[f"NU_NOTA_COMP{i + 1}"] = np.where(dia1 == 1, comp_base[:, i], np.nan)
    df["NU_NOTA_REDACAO"] = np.where(dia1 == 1, comp_base.sum(1), np.nan)
    return df


def gerar_participantes(n: int) -> pd.DataFrame:
    return pd.DataFrame({
        "NU_INSCRICAO": np.arange(250000000000, 250000000000 + n),
        "NU_ANO": 2025,
        "TP_FAIXA_ETARIA": rng.choice(range(1, 21), n, p=np.r_[[0.05, 0.25, 0.2, 0.1], [0.4 / 16] * 16]),
        "TP_SEXO": rng.choice(["F", "M"], n, p=[0.6, 0.4]),
        "TP_COR_RACA": rng.choice(range(7), n, p=[0.02, 0.38, 0.13, 0.43, 0.02, 0.01, 0.01]),
        "TP_ST_CONCLUSAO": rng.choice([1, 2, 3, 4], n, p=[0.45, 0.35, 0.15, 0.05]),
        "IN_TREINEIRO": rng.choice([0, 1], n, p=[0.9, 0.1]),
        "SG_UF_PROVA": rng.choice(UFS, n),
        "Q006": rng.choice(list("ABCDEFGHIJKLMNOPQ"), n),
    })


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default="data/raw_sintetico")
    ap.add_argument("--n", type=int, default=60_000)
    args = ap.parse_args()
    pasta = Path(args.saida) / "DADOS"
    pasta.mkdir(parents=True, exist_ok=True)
    itens = gerar_itens()
    kw = dict(sep=";", encoding="latin-1", index=False)
    itens.to_csv(pasta / "ITENS_PROVA_2025.csv", **kw)
    gerar_resultados(args.n, itens).to_csv(pasta / "RESULTADOS_2025.csv", **kw)
    gerar_participantes(args.n).to_csv(pasta / "PARTICIPANTES_2025.csv", **kw)
    print(f"Base sintética gravada em {pasta}")


if __name__ == "__main__":
    main()
