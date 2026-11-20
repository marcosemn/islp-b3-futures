"""Processa data/raw/*.zip um pregão por vez e grava em data/processed/.

Saídas (um arquivo por pregão, então reprocessar só faz os dias novos):
    processed/summary/AAAA-MM-DD.parquet   negócios e contratos por ticker (todos os vencimentos)
    processed/trades/AAAA-MM-DD.parquet    negócios do vencimento principal de WDO e WIN
    processed/bars_1min/AAAA-MM-DD.parquet barras de 1 min (coluna root = WDO/WIN)

Uso:
    python -m src.pipeline
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.b3_loader import read_trades
from src.features import front_month, time_bars

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"


def process_day(path: Path, processed_dir: Path = PROCESSED_DIR, freq: str = "1min") -> str:
    """Processa um arquivo diário e retorna a data do pregão."""
    bars_dir = processed_dir / f"bars_{freq}"
    trades = read_trades(path)
    day = f"{trades['ts'].iloc[0]:%Y-%m-%d}"
    for sub in ["summary", "trades", bars_dir.name]:
        (processed_dir / sub).mkdir(parents=True, exist_ok=True)

    summary = trades.groupby("ticker", observed=True).agg(negocios=("price", "size"), contratos=("qty", "sum"))
    summary.assign(day=day).to_parquet(processed_dir / "summary" / f"{day}.parquet")

    fm = front_month(trades)
    fm.to_parquet(processed_dir / "trades" / f"{day}.parquet")

    bars = pd.concat(
        {r: time_bars(fm[fm["root"] == r], freq) for r in sorted(fm["root"].astype(str).unique())},
        names=["root"],
    ).reset_index("root")
    bars.to_parquet(bars_dir / f"{day}.parquet")
    return day


def build(raw_dir: Path = RAW_DIR, processed_dir: Path = PROCESSED_DIR, freq: str = "1min",
          refazer: bool = False) -> list[str]:
    """Processa os arquivos de raw_dir que ainda não foram processados.
    refazer=True reprocessa todos (use quando o cálculo das barras mudar)."""
    done_file = processed_dir / f"done_{freq}.txt"
    done = set(done_file.read_text().split()) if done_file.exists() and not refazer else set()
    new = []
    for path in sorted(raw_dir.glob("*.zip")):
        if path.name in done:
            continue
        day = process_day(path, processed_dir, freq)
        new.append(day)
        print(f"{day}: ok", flush=True)
        done.add(path.name)
        done_file.write_text("\n".join(sorted(done)))
    return new


def load(kind: str = "bars_1min", processed_dir: Path = PROCESSED_DIR) -> pd.DataFrame:
    """Concatena os parquets diários de uma saída (bars_1min, trades ou summary)."""
    files = sorted((processed_dir / kind).glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"Nada em {processed_dir / kind} - rode `python -m src.pipeline` antes.")
    # Em "trades" o índice é só a posição da linha no dia; renumera para não repetir entre dias.
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=(kind == "trades"))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refazer", action="store_true", help="reprocessa todos os pregões (após mudar o cálculo)")
    novos = build(refazer=parser.parse_args().refazer)
    print(f"{len(novos)} pregões processados")
