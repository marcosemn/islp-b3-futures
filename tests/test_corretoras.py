from src.corretoras import nome_corretora


def test_nomes_curtos():
    assert nome_corretora(3) == "XP"
    assert nome_corretora("85") == "BTG"
    assert nome_corretora(" 1618 ") == "IDEAL"


def test_codigo_desconhecido():
    assert nome_corretora(9999) == "cód. 9999"
