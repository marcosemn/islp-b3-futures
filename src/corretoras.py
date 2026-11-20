"""Nomes curtos das corretoras (participantes de negociação) que aparecem nos negócios de WDO e WIN.

O arquivo negócio a negócio da B3 só traz o código numérico da corretora compradora e da vendedora
(colunas buyer e seller). Os nomes vêm da lista oficial de participantes da B3:

    https://www.b3.com.br/pt_br/produtos-e-servicos/participantes/busca-de-participantes/participantes/

(exportada em 20/11/2026; o código usado é o do perfil "Participante de Negociação Pleno").
Os nomes abaixo foram encurtados à mão para leitura. Se aparecer uma corretora nova nos dados,
nome_corretora() devolve "cód. N"; aí é só consultar a lista e acrescentar o código aqui.
"""

from __future__ import annotations

NOMES_CURTOS = {
    "3": "XP",
    "8": "UBS BB",
    "13": "MERRILL LYNCH",
    "16": "J.P. MORGAN",
    "23": "NECTON (BTG)",
    "27": "SANTANDER INST.",
    "39": "ÁGORA",
    "40": "MORGAN STANLEY",
    "59": "SAFRA",
    "77": "CITI",
    "85": "BTG",
    "88": "CM CAPITAL",
    "92": "WARREN",
    "93": "NOVA FUTURA",
    "107": "TERRA",
    "114": "ITAÚ",
    "120": "GENIAL",
    "122": "BGC LIQUIDEZ",
    "127": "TULLETT PREBON",
    "147": "ATIVA",
    "238": "GOLDMAN SACHS",
    "262": "MIRAE",
    "346": "DAYCOVAL",
    "688": "ABN AMRO",
    "746": "LEV",
    "1099": "INTER",
    "1130": "STONEX",
    "1618": "IDEAL",
    "4090": "SANTANDER",
    "6003": "C6",
    "7035": "PAGINVEST",
}


def nome_corretora(codigo) -> str:
    """Nome curto da corretora; se o código não estiver na tabela, devolve "cód. N"."""
    codigo = str(codigo).strip()
    return NOMES_CURTOS.get(codigo, f"cód. {codigo}")
