"""Conjunto de modelagem dos capítulos 2 e 3: sem look-ahead e com divisão por data."""

import numpy as np
import pandas as pd
import pytest

from src.dataset import FEATURES, dividir, montar
from src.features import time_bars


@pytest.fixture
def barras():
    """Barras de 1 minuto de dois pregões, com uma pausa de 10 minutos no primeiro."""
    rng = np.random.default_rng(0)
    minutos = (list(pd.date_range("2026-11-17 09:00", periods=8, freq="1min"))
               + list(pd.date_range("2026-11-17 09:18", periods=8, freq="1min"))
               + list(pd.date_range("2026-11-18 09:00", periods=8, freq="1min")))
    precos = 100 + np.cumsum(rng.choice([-0.5, 0.5], len(minutos)))
    negocios = pd.DataFrame({"ts": minutos, "price": precos, "qty": rng.integers(1, 5, len(minutos)),
                             "buyer": "1", "seller": "2"})
    return time_bars(negocios)


def test_alvo_e_o_retorno_do_minuto_seguinte(barras):
    d = montar(barras)
    for t, linha in d.iterrows():
        seguinte = barras.index[barras.index.get_loc(t) + 1]
        assert linha["fwd"] == pytest.approx(barras.loc[seguinte, "ret"] * 1e4)


def test_features_so_usam_o_passado_do_mesmo_trecho(barras):
    # Como o retorno é vazio no 1º minuto de cada trecho, uma defasagem que atravessasse trechos
    # ainda seria descartada aqui. O vazamento de defasagens é testado direto na função
    # (test_features.py::test_add_lags_nao_atravessa_trechos).
    d = montar(barras)
    for t, linha in d.iterrows():
        i = barras.index.get_loc(t)
        assert linha["ret"] == pytest.approx(barras["ret"].iloc[i] * 1e4)
        assert linha["ret_l1"] == pytest.approx(barras["ret"].iloc[i - 1] * 1e4)
        assert linha["abs_ret_l2"] == pytest.approx(abs(barras["ret"].iloc[i - 2]) * 1e4)
        # o minuto e as duas defasagens estão no mesmo trecho (nada de antes da pausa ou da noite)
        assert (t - barras.index[i - 2]) == pd.Timedelta("2min")
    assert not d[FEATURES + ["fwd", "abs_fwd"]].isna().any().any()


def test_minutos_sem_historico_ou_sem_futuro_ficam_de_fora(barras):
    d = montar(barras)
    inicios = [pd.Timestamp("2026-11-17 09:00"), pd.Timestamp("2026-11-17 09:18"), pd.Timestamp("2026-11-18 09:00")]
    fins = [pd.Timestamp("2026-11-17 09:07"), pd.Timestamp("2026-11-17 09:25"), pd.Timestamp("2026-11-18 09:07")]
    for inicio in inicios:                                   # sem retorno e sem duas defasagens
        assert not any(inicio <= t < inicio + pd.Timedelta("3min") for t in d.index)
    for fim in fins:                                         # sem minuto seguinte no mesmo trecho
        assert fim not in d.index


def test_dividir_por_data():
    idx = pd.date_range("2026-11-02 10:00", periods=10, freq="1D")
    dados = {"WDO": pd.DataFrame({"x": range(10)}, index=idx)}
    treino, teste = dividir(dados, frac_treino=0.7)
    assert len(treino["WDO"]) == 7 and len(teste["WDO"]) == 3
    assert treino["WDO"].index.max() < teste["WDO"].index.min()
