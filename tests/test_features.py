"""Transformações de negócios em barras: tick rule, trechos, leilões, proxy de diretos e barras."""

import numpy as np
import pandas as pd
import pytest

from src.features import (add_forward_return, add_lags, auction_mask, direct_trade_proxy, front_month,
                          tick_rule, time_bars, trading_segments)

ts = pd.Timestamp


def test_tick_rule():
    precos = pd.Series([10.0, 11.0, 11.0, 10.0, 10.0, 12.0])
    # primeiro negócio sem referência = 0; preço igual repete o sinal anterior
    assert list(tick_rule(precos)) == [0, 1, 1, -1, -1, 1]


def test_trading_segments_quebra_no_dia_e_na_pausa():
    idx = pd.DatetimeIndex([ts("2026-11-17 09:00"), ts("2026-11-17 09:01"), ts("2026-11-17 09:10"),
                            ts("2026-11-17 09:11"), ts("2026-11-18 09:00")])
    seg = trading_segments(idx)
    assert list(seg) == [1, 1, 2, 2, 3]                      # pausa de 9 min e novo pregão abrem trechos


def test_auction_mask_primeiros_50ms_de_cada_trecho():
    t = pd.Series([ts("2026-11-17 09:00:00.000"), ts("2026-11-17 09:00:00.010"), ts("2026-11-17 09:00:00.060"),
                   ts("2026-11-17 09:05:00"), ts("2026-11-17 09:20:00.000")])
    # o último abre um trecho novo (pausa de 15 min), como um leilão de fechamento
    assert list(auction_mask(t)) == [True, True, False, False, True]


def test_direct_trade_proxy():
    t = pd.DataFrame({
        "ts": [ts("2026-11-17 09:00:00.000"), ts("2026-11-17 09:03"), ts("2026-11-17 09:04"),
               ts("2026-11-17 09:05"), ts("2026-11-17 09:06")],
        "buyer": ["3", "3", "3", "3", "8"],
        "seller": ["3", "3", "3", "3", "16"],
        "qty": [600, 600, 400, 500, 600],
    })
    # leilão / direto / abaixo do lote / exatamente o lote mínimo / corretoras diferentes
    assert list(direct_trade_proxy(t)) == [False, True, False, True, False]


def test_front_month_fica_com_o_mais_negociado_de_cada_dia():
    t = pd.DataFrame({
        "ts": [ts("2026-10-29 10:00")] * 2 + [ts("2026-10-30 10:00")] * 2,
        "root": ["WDO"] * 4,
        "ticker": ["WDOX26", "WDOZ26", "WDOX26", "WDOZ26"],
        "qty": [20, 10, 5, 30],
    })
    fm = front_month(t)
    assert list(fm["ticker"]) == ["WDOX26", "WDOZ26"]


@pytest.fixture
def negocios():
    """Dois pregões de um contrato, com um negócio direto no segundo minuto do primeiro dia."""
    linhas = [
        # dia 1, 09:00: 100 -> 101 (lados 0 e +1)
        ("2026-11-17 09:00:00.000", 100.0, 1, "1", "2"),
        ("2026-11-17 09:00:30.000", 101.0, 2, "1", "2"),
        # dia 1, 09:01: direto de 600 no mesmo preço (+1 repetido) e uma venda (-1)
        ("2026-11-17 09:01:10.000", 101.0, 600, "5", "5"),
        ("2026-11-17 09:01:20.000", 100.0, 1, "1", "2"),
        # dia 2: a tick rule recomeça (primeiro negócio = 0)
        ("2026-11-18 09:00:00.000", 105.0, 1, "1", "2"),
        ("2026-11-18 09:00:30.000", 104.0, 1, "1", "2"),
        ("2026-11-18 09:01:00.000", 106.0, 1, "1", "2"),
    ]
    return pd.DataFrame(linhas, columns=["ts", "price", "qty", "buyer", "seller"]).assign(ts=lambda d: pd.to_datetime(d["ts"]))


def test_time_bars_fluxo_e_diretos(negocios):
    b = time_bars(negocios)
    m0, m1 = b.loc[ts("2026-11-17 09:00")], b.loc[ts("2026-11-17 09:01")]
    assert (m0["volume"], m0["signed_volume"]) == (3, 2)
    assert m0["imbalance"] == pytest.approx(2 / 3)
    assert (m1["n_diretos"], m1["volume_direto"]) == (1, 600)
    assert m1["imbalance"] == pytest.approx(599 / 601)       # com o direto
    assert m1["imbalance_sem_diretos"] == pytest.approx(-1.0)  # sem ele, sobra a venda
    assert b["imbalance"].between(-1, 1).all()


def test_retornos_nao_atravessam_o_pregao(negocios):
    b = time_bars(negocios)
    assert np.isnan(b.loc[ts("2026-11-17 09:00"), "ret"])
    assert b.loc[ts("2026-11-17 09:01"), "ret"] == pytest.approx(np.log(100 / 101))
    assert np.isnan(b.loc[ts("2026-11-18 09:00"), "ret"])   # o 1º minuto do dia 2 não usa o fechamento do dia 1
    f = add_forward_return(b, 1)
    assert np.isnan(f.loc[ts("2026-11-17 09:01"), "fwd_ret_1"])  # o último minuto do dia 1 não vê o dia 2
    assert f.loc[ts("2026-11-18 09:00"), "fwd_ret_1"] == pytest.approx(np.log(106 / 104))


def test_add_lags_nao_atravessa_trechos():
    idx = pd.DatetimeIndex([ts("2026-11-17 09:00"), ts("2026-11-17 09:01"), ts("2026-11-17 09:02"),
                            ts("2026-11-18 09:00"), ts("2026-11-18 09:01")])
    b = add_lags(pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]}, index=idx), "x", 2)
    assert b["x_l1"].tolist()[:3] == [pytest.approx(v, nan_ok=True) for v in [np.nan, 1.0, 2.0]]
    assert np.isnan(b.loc[ts("2026-11-18 09:00"), "x_l1"])   # não usa o dia anterior
    assert b.loc[ts("2026-11-18 09:01"), "x_l1"] == 4.0
    assert np.isnan(b.loc[ts("2026-11-18 09:01"), "x_l2"])
