"""Leitura dos arquivos "negócio a negócio" da B3 (TradeIntradayFile).

Layout oficial: Glossário Dados Públicos - Negócios Listados (B3, v3, mai/2023).
Os arquivos devem ser baixados manualmente do Boletim Diário do Mercado
(Derivativos > Derivativos de bolsa > Negócio a negócio) e salvos em data/raw/.
A B3 proíbe coleta automatizada na página, por isso não há scraper aqui.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

COLUMNS = [
    "DataReferencia",
    "CodigoInstrumento",
    "AcaoAtualizacao",             # 0 = novo, 2 = cancelado
    "PrecoNegocio",
    "QuantidadeNegociada",
    "HoraFechamento",              # HHMMSSNNN, horário de Brasília (UTC-3)
    "CodigoIdentificadorNegocio",
    "TipoSessaoPregao",            # 1 = regular, 6 = after hours
    "DataNegocio",
    "CodigoParticipanteComprador",
    "CodigoParticipanteVendedor",
]

RENAME = {
    "CodigoInstrumento": "ticker",
    "PrecoNegocio": "price",
    "QuantidadeNegociada": "qty",
    "CodigoIdentificadorNegocio": "trade_id",
    "TipoSessaoPregao": "session",
    "CodigoParticipanteComprador": "buyer",
    "CodigoParticipanteVendedor": "seller",
}

DEFAULT_ROOTS = ("WDO", "WIN")


def _open_text(path: Path) -> io.TextIOBase:
    """Abre o .txt/.csv diretamente ou o primeiro arquivo de dentro do .zip."""
    if path.suffix.lower() == ".zip":
        zf = zipfile.ZipFile(path)
        inner = next(n for n in zf.namelist() if not n.endswith("/"))
        return io.TextIOWrapper(zf.open(inner), encoding="latin-1")
    return open(path, encoding="latin-1")


def read_trades(path: str | Path, roots: tuple[str, ...] | None = DEFAULT_ROOTS) -> pd.DataFrame:
    """Lê um arquivo diário e devolve os negócios válidos, um por linha.

    roots: prefixos de ticker a manter (ex.: ("WDO", "WIN")); None mantém tudo.
    """
    path = Path(path)
    with _open_text(path) as fh:
        has_header = fh.readline().startswith("DataReferencia")
    with _open_text(path) as fh:
        df = pd.read_csv(
            fh,
            sep=";",
            decimal=",",
            header=0 if has_header else None,
            names=None if has_header else COLUMNS,
            dtype={"HoraFechamento": str, "CodigoInstrumento": str,
                   "CodigoParticipanteComprador": str, "CodigoParticipanteVendedor": str},
        )

    df["CodigoInstrumento"] = df["CodigoInstrumento"].str.strip()
    if roots is not None:
        df = df[df["CodigoInstrumento"].str.startswith(tuple(roots))]
    df = df[df["AcaoAtualizacao"] != 2]  # remove negócios cancelados

    hora = df["HoraFechamento"].str.strip().str.zfill(9)
    df = df.assign(
        ts=pd.to_datetime(df["DataNegocio"] + " " + hora, format="%Y-%m-%d %H%M%S%f"),
        root=df["CodigoInstrumento"].str[:3],
    )
    df = df.rename(columns=RENAME)
    cols = ["ts", "root", "ticker", "price", "qty", "trade_id", "session", "buyer", "seller"]
    return df[cols].sort_values(["ticker", "ts", "trade_id"]).reset_index(drop=True)


def load_raw_dir(raw_dir: str | Path = "data/raw", roots: tuple[str, ...] | None = DEFAULT_ROOTS) -> pd.DataFrame:
    """Lê todos os arquivos .zip/.txt/.csv de raw_dir e concatena."""
    raw_dir = Path(raw_dir)
    files = sorted(p for p in raw_dir.iterdir() if p.suffix.lower() in {".zip", ".txt", ".csv"})
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo em {raw_dir.resolve()} - veja o README (seção Dados).")
    return pd.concat([read_trades(p, roots) for p in files], ignore_index=True)
