"""Leitura do arquivo negócio a negócio da B3 com um arquivo sintético no mesmo layout."""

import io
import zipfile

import pandas as pd
import pytest

from src.b3_loader import COLUMNS, read_trades

# Cada linha testa uma regra do loader (ver comentários).
LINHAS = [
    # dois negócios do WDO no mesmo milissegundo: a ordem do arquivo deve ser preservada
    "2026-11-17;WDOZ26;0;5800,500;2;090000100;10;1;2026-11-17;3;85;1",
    "2026-11-17;WDOZ26;0;5801,000;1;090000100;11;1;2026-11-17;85;3;1",
    # negócio 12 do WDO e o seu cancelamento: os dois devem sair
    "2026-11-17;WDOZ26;0;5802,000;5;090001000;12;1;2026-11-17;3;3;1",
    "2026-11-17;WDOZ26;2;5802,000;5;090001000;12;1;2026-11-17;3;3;1",
    # o mesmo id 12 no WIN é outro negócio e deve ficar; a hora com 8 dígitos ganha o zero à esquerda
    "2026-11-17;WINZ26;0;170000,000;3;90000200;12;1;2026-11-17;8;16;1",
    # negócio do WIN anterior ao de cima no tempo: deve vir primeiro depois de ordenar
    "2026-11-17;WINZ26;0;170005,000;1;090000050;13;1;2026-11-17;8;8;1",
    # outro ativo: fora do filtro de WDO/WIN
    "2026-11-17;DOLZ26;0;5800,000;1;090000100;14;1;2026-11-17;3;3;1",
    # data do negócio diferente da data do pregão: deve ser descartado
    "2026-11-17;WDOZ26;0;5799,000;1;010000000;15;1;2026-11-16;3;3;1",
]
TEXTO = ";".join(COLUMNS) + "\n" + "\n".join(LINHAS) + "\n"


@pytest.fixture
def arquivo_txt(tmp_path):
    p = tmp_path / "17-11-2026_NEGOCIOSAVISTA_DRV.txt"
    p.write_text(TEXTO, encoding="latin-1")
    return p


def _zip_em_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("17-11-2026_NEGOCIOSAVISTA_DRV.txt", TEXTO.encode("latin-1"))
    return buf.getvalue()


def test_regras_de_limpeza(arquivo_txt):
    t = read_trades(arquivo_txt)
    assert list(t["trade_id"]) == [10, 11, 13, 12]          # cancelados, outra data e outro ativo fora
    assert set(t["root"].astype(str)) == {"WDO", "WIN"}
    assert 15 not in set(t["trade_id"])                       # data diferente do pregão


def test_ordem_estavel_e_timestamps(arquivo_txt):
    t = read_trades(arquivo_txt)
    wdo = t[t["root"] == "WDO"]
    assert list(wdo["trade_id"]) == [10, 11]                 # mesmo milissegundo: ordem do arquivo
    assert wdo["ts"].iloc[0] == pd.Timestamp("2026-11-17 09:00:00.100")
    win = t[t["root"] == "WIN"]
    assert list(win["ts"]) == [pd.Timestamp("2026-11-17 09:00:00.050"), pd.Timestamp("2026-11-17 09:00:00.200")]


def test_tipos(arquivo_txt):
    t = read_trades(arquivo_txt)
    assert t["price"].iloc[0] == 5800.5                      # decimal com vírgula
    assert t["qty"].iloc[0] == 2
    assert t["buyer"].astype(str).iloc[0] == "3"
    for c in ["root", "ticker", "buyer", "seller"]:
        assert isinstance(t[c].dtype, pd.CategoricalDtype)


def test_zip_em_disco_e_em_memoria(tmp_path, arquivo_txt):
    dados = _zip_em_bytes()
    caminho = tmp_path / "17-11-2026_NEGOCIOSAVISTA_DRV.zip"
    caminho.write_bytes(dados)
    esperado = read_trades(arquivo_txt)
    for fonte in [caminho, dados]:
        pd.testing.assert_frame_equal(read_trades(fonte), esperado)
