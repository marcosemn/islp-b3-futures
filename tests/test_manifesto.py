import pandas as pd

from src.manifesto import comparar


def _m(linhas):
    return pd.DataFrame(linhas, columns=["pregao", "sha256"])


def test_comparar_detecta_novos_ausentes_e_alterados():
    referencia = _m([("2026-11-17", "aaa"), ("2026-11-18", "bbb"), ("2026-11-19", "ccc")])
    atual = _m([("2026-11-18", "bbb"), ("2026-11-19", "xxx"), ("2026-11-20", "ddd")])
    assert comparar(atual, referencia) == {"novos": ["2026-11-20"], "ausentes": ["2026-11-17"], "alterados": ["2026-11-19"]}


def test_comparar_amostra_igual():
    m = _m([("2026-11-17", "aaa")])
    assert comparar(m, m) == {"novos": [], "ausentes": [], "alterados": []}
