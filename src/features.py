"""Transformações de negócio a negócio em séries para modelagem."""

from __future__ import annotations

import numpy as np
import pandas as pd


def front_month(trades: pd.DataFrame) -> pd.DataFrame:
    """Mantém, para cada dia e ativo-raiz (WDO/WIN), só o vencimento mais negociado."""
    day = trades["ts"].dt.normalize()
    vol = trades.groupby([day, "root", "ticker"], observed=True)["qty"].sum()
    top = vol.groupby(level=[0, 1], observed=True).idxmax().map(lambda key: key[2])
    keep = pd.Series(top.values, index=top.index.set_names(["day", "root"]))
    key = pd.MultiIndex.from_arrays([day, trades["root"].astype(str)], names=["day", "root"])
    return trades[trades["ticker"].astype(str).values == keep.reindex(key).values].reset_index(drop=True)


def tick_rule(price: pd.Series) -> pd.Series:
    """Estima o lado agressor: +1 se o preço subiu vs. o negócio anterior, -1 se caiu,
    e repete o último sinal quando não mudou. O arquivo público da B3 não traz o agressor,
    então esta é uma aproximação (Lee & Ready, 1991)."""
    sign = np.sign(price.diff()).replace(0, np.nan).ffill().fillna(0)
    return sign.astype(int)


def time_bars(trades: pd.DataFrame, freq: str = "1min") -> pd.DataFrame:
    """Agrega um único ticker em barras de tempo com OHLC, volume e fluxo estimado.

    Espera os negócios de um só contrato (use front_month e filtre por root antes).
    """
    t = trades.sort_values("ts", kind="stable").copy()
    t["day"] = t["ts"].dt.normalize()
    t["side"] = t.groupby("day", group_keys=False)["price"].apply(tick_rule)
    t["signed_qty"] = t["side"] * t["qty"]
    t["notional"] = t["price"] * t["qty"]

    g = t.set_index("ts").groupby([pd.Grouper(key="day"), pd.Grouper(freq=freq)])
    bars = g.agg(
        open=("price", "first"),
        high=("price", "max"),
        low=("price", "min"),
        close=("price", "last"),
        volume=("qty", "sum"),
        n_trades=("price", "size"),
        signed_volume=("signed_qty", "sum"),
        notional=("notional", "sum"),
    ).dropna(subset=["close"])
    bars.index = bars.index.droplevel(0)
    bars.index.name = "ts"

    bars["vwap"] = bars["notional"] / bars["volume"]
    bars["imbalance"] = bars["signed_volume"] / bars["volume"]  # entre -1 e +1
    day = bars.index.normalize()
    bars["ret"] = np.log(bars["close"]).groupby(day).diff()     # não atravessa a noite
    return bars.drop(columns="notional")


def add_forward_return(bars: pd.DataFrame, horizon: int = 1, col: str = "close") -> pd.DataFrame:
    """Alvo: log-retorno das próximas `horizon` barras, sem cruzar dias (evita gap noturno)."""
    day = bars.index.normalize()
    logp = np.log(bars[col])
    out = bars.copy()
    out[f"fwd_ret_{horizon}"] = logp.groupby(day).shift(-horizon) - logp
    return out
