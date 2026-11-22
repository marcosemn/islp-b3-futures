"""Conjunto de modelagem dos capítulos 2 e 3: features conhecidas no fechamento do minuto t
e alvos do minuto t+1, com a mesma divisão treino/teste nos dois capítulos."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.features import add_forward_return, add_lags
from src.pipeline import PROCESSED_DIR, load

# Tudo conhecido no fechamento do minuto t (retornos em bps)
FEATURES = ["ret", "ret_l1", "ret_l2", "abs_ret", "abs_ret_l1", "abs_ret_l2", "imbalance", "log_vol", "minuto"]
# Alvos do minuto t+1: direção (fwd) e intensidade (abs_fwd), em bps
ALVOS = ["fwd", "abs_fwd"]


def montar(barras: pd.DataFrame) -> pd.DataFrame:
    """Features e alvos para as barras de 1 minuto de um ativo (sem a coluna root).
    Defasagens e alvos não atravessam a noite nem os leilões (trading_segments)."""
    b = add_forward_return(barras, 1)
    b["ret"] = b["ret"] * 1e4
    b["fwd"] = b["fwd_ret_1"] * 1e4
    b["abs_ret"], b["abs_fwd"] = b["ret"].abs(), b["fwd"].abs()
    b = add_lags(add_lags(b, "ret", 2), "abs_ret", 2)
    b["log_vol"] = np.log(b["volume"])
    b["minuto"] = (b.index.hour - 9) * 60 + b.index.minute
    return b.dropna(subset=FEATURES + ["fwd"])


def carregar(processed_dir: Path = PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    """Conjunto de modelagem de cada ativo, a partir das barras de 1 minuto do pipeline."""
    return {r: montar(g.drop(columns="root")) for r, g in load("bars_1min", processed_dir).groupby("root")}


def dividir(dados: dict[str, pd.DataFrame], frac_treino: float = 0.7):
    """Divide por data, nunca por sorteio: os primeiros `frac_treino` dos pregões vão para o treino
    e o restante para o teste. Devolve (treino, teste), dicionários por ativo."""
    dias = sorted(set().union(*(d.index.normalize().unique() for d in dados.values())))
    corte = dias[round(frac_treino * len(dias))]
    treino = {r: d[d.index < corte] for r, d in dados.items()}
    teste = {r: d[d.index >= corte] for r, d in dados.items()}
    return treino, teste
