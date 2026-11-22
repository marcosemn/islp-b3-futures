"""Registro dos dados que geraram os números dos relatórios.

relatorios/dados_usados.csv lista cada pregão com o hash SHA-256 do arquivo da B3. Quem tiver
os mesmos arquivos em data/raw/ obtém os mesmos hashes, e portanto os mesmos resultados.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.pipeline import RAW_DIR, ROOT_DIR

MANIFESTO = ROOT_DIR / "relatorios" / "dados_usados.csv"


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def gerar(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Um registro por arquivo de data/raw/: data do pregão, nome, tamanho e SHA-256."""
    linhas = []
    for p in raw_dir.glob("*.zip"):
        dia = datetime.strptime(p.name[:10], "%d-%m-%Y").date()
        linhas.append({"pregao": dia.isoformat(), "arquivo": p.name, "bytes": p.stat().st_size, "sha256": _sha256(p)})
    return pd.DataFrame(linhas, columns=["pregao", "arquivo", "bytes", "sha256"]).sort_values("pregao").reset_index(drop=True)


def ler(caminho: Path = MANIFESTO) -> pd.DataFrame:
    return pd.read_csv(caminho, dtype=str)


def comparar(atual: pd.DataFrame, referencia: pd.DataFrame) -> dict[str, list[str]]:
    """Pregões novos, ausentes e com arquivo diferente em relação ao manifesto de referência."""
    a = atual.set_index("pregao")["sha256"]
    r = referencia.set_index("pregao")["sha256"]
    comuns = a.index.intersection(r.index)
    return {"novos": sorted(a.index.difference(r.index)),
            "ausentes": sorted(r.index.difference(a.index)),
            "alterados": sorted(comuns[a[comuns] != r[comuns]])}


def gravar(manifesto: pd.DataFrame, caminho: Path = MANIFESTO) -> None:
    caminho.parent.mkdir(exist_ok=True)
    manifesto.to_csv(caminho, index=False)
