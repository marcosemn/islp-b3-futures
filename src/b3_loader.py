"""Leitura dos arquivos "negócio a negócio" da B3 (TradeIntradayFile).

Layout oficial: Glossário Dados Públicos - Negócios Listados (B3, v3, mai/2023),
conferido contra o arquivo real de derivativos de 17/11/2026
(17-11-2026_NEGOCIOSAVISTA_DRV.txt: ~520 MB, 7,2 milhões de negócios, 50 MB zipado).

Origem: Boletim Diário do Mercado > Derivativos > Derivativos de bolsa > Negócio a negócio.
Salve os .zip em data/raw/ ou passe os bytes do .zip direto para read_trades().
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
from pandas.api.types import union_categoricals

COLUMNS = [
    "DataReferencia",
    "CodigoInstrumento",
    "AcaoAtualizacao",             # 0 = novo, 2 = cancelamento de um negócio anterior
    "PrecoNegocio",
    "QuantidadeNegociada",
    "HoraFechamento",              # HHMMSSNNN, horário de Brasília (UTC-3)
    "CodigoIdentificadorNegocio",  # único só dentro do instrumento (WDO e WIN repetem ids)
    "TipoSessaoPregao",            # 1 = regular, 6 = after hours
    "DataNegocio",
    "CodigoParticipanteComprador",
    "CodigoParticipanteVendedor",
    "TipoDoCanal",                 # presente no arquivo real, ausente do glossário
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


def _open_text(source: Path | bytes) -> io.TextIOBase:
    """Abre o .txt/.csv, o primeiro arquivo de um .zip em disco ou um .zip em memória."""
    if isinstance(source, (bytes, bytearray)):
        zf = zipfile.ZipFile(io.BytesIO(source))
    elif source.suffix.lower() == ".zip":
        zf = zipfile.ZipFile(source)
    else:
        return open(source, encoding="latin-1")
    inner = next(n for n in zf.namelist() if not n.endswith("/"))
    return io.TextIOWrapper(zf.open(inner), encoding="latin-1")


def read_trades(source: str | Path | bytes, roots: tuple[str, ...] | None = DEFAULT_ROOTS) -> pd.DataFrame:
    """Lê um arquivo diário e devolve os negócios válidos, um por linha.

    source: caminho do .zip/.txt ou os bytes do .zip baixado.
    roots: prefixos de ticker a manter (ex.: ("WDO", "WIN")); None mantém tudo.
    """
    if not isinstance(source, (bytes, bytearray)):
        source = Path(source)
    with _open_text(source) as fh:
        has_header = fh.readline().startswith("DataReferencia")
    # Um pregão tem milhões de negócios (só o WIN passa de 5 milhões), então lê em
    # blocos e filtra cada um, para não carregar o arquivo inteiro na memória.
    with _open_text(source) as fh:
        chunks = pd.read_csv(
            fh,
            sep=";",
            decimal=",",
            header=0 if has_header else None,
            names=None if has_header else COLUMNS,
            dtype={"HoraFechamento": str, "CodigoInstrumento": str, "AcaoAtualizacao": int,
                   "CodigoParticipanteComprador": str, "CodigoParticipanteVendedor": str},
            chunksize=500_000,
        )
        parts = []
        for chunk in chunks:
            chunk["CodigoInstrumento"] = chunk["CodigoInstrumento"].str.strip()
            if roots is not None:
                chunk = chunk[chunk["CodigoInstrumento"].str.startswith(tuple(roots))]
            parts.append(chunk)
    df = pd.concat(parts, ignore_index=True)

    # Um cancelamento é uma linha nova (AcaoAtualizacao = 2) com o mesmo instrumento e id
    # do negócio original, que continua no arquivo: remove as duas.
    key = ["CodigoInstrumento", "CodigoIdentificadorNegocio"]
    cancelled = df.loc[df["AcaoAtualizacao"] == 2, key].drop_duplicates()
    if len(cancelled):
        hit = df[key].merge(cancelled, how="left", indicator=True)["_merge"].eq("both").values
        df = df[~hit]

    # O arquivo de um pregão traz algumas linhas com DataNegocio de outro dia
    # (ex.: 01h do dia anterior); elas criariam um "pregão" falso nas barras.
    df = df[df["DataNegocio"] == df["DataReferencia"]]

    hora = df["HoraFechamento"].str.strip().str.zfill(9)
    df = df.assign(
        ts=pd.to_datetime(df["DataNegocio"] + " " + hora, format="%Y-%m-%d %H%M%S%f"),
        root=df["CodigoInstrumento"].str[:3],
    )
    df = df.rename(columns=RENAME)
    cols = ["ts", "root", "ticker", "price", "qty", "trade_id", "session", "buyer", "seller"]
    # Ordenação estável: negócios no mesmo milissegundo mantêm a ordem do arquivo.
    df = df[cols].sort_values(["ticker", "ts"], kind="stable").reset_index(drop=True)
    # Texto repetido milhões de vezes vira category (~1,7 GB -> poucas centenas de MB por pregão).
    return df.astype({c: "category" for c in ["root", "ticker", "buyer", "seller"]})


def load_raw_dir(raw_dir: str | Path = "data/raw", roots: tuple[str, ...] | None = DEFAULT_ROOTS) -> pd.DataFrame:
    """Lê todos os arquivos .zip/.txt/.csv de raw_dir e concatena."""
    raw_dir = Path(raw_dir)
    files = sorted(p for p in raw_dir.iterdir() if p.suffix.lower() in {".zip", ".txt", ".csv"})
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo em {raw_dir.resolve()} - veja o README (seção Dados).")
    # union_categoricals evita que o concat transforme as categorias de volta em texto
    frames = [read_trades(p, roots) for p in files]
    out = pd.concat(frames, ignore_index=True)
    for c in ["root", "ticker", "buyer", "seller"]:
        out[c] = union_categoricals([f[c] for f in frames])
    return out
