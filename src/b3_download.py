"""Baixa os arquivos "negócio a negócio" de derivativos da B3 e guarda em data/raw/.

Origem: Boletim Diário do Mercado > Derivativos > Derivativos de bolsa > Negócio a negócio.
Cada pregão é um .zip de ~50 MB com um .txt de ~500 MB dentro (layout em b3_loader.py).
Baixa uma vez e guarda: arquivos já presentes não são baixados de novo.

Uso:
    python -m src.b3_download            # últimos 30 dias corridos
    python -m src.b3_download --dias 60
"""

from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from pathlib import Path

import requests

URL = "https://drp.b3.com.br/rapinegocios/tickercsv/{d:%Y-%m-%d}?type={tipo}"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIPO_DERIVATIVOS = 1
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
PAUSA_S = 2.0  # entre downloads, para não sobrecarregar o servidor da B3


def nome_arquivo(dia: date) -> str:
    return f"{dia:%d-%m-%Y}_NEGOCIOSAVISTA_DRV.zip"


def baixar_zip(dia: date, tipo: int = TIPO_DERIVATIVOS, tentativas: int = 3) -> bytes | None:
    """Retorna o .zip do pregão (em memória) ou None se não existir (feriado, fim de semana,
    ainda não publicado ou fora do período que a B3 mantém)."""
    for n in range(1, tentativas + 1):
        try:
            resp = requests.get(URL.format(d=dia, tipo=tipo), headers=HEADERS, timeout=300)
            break
        except requests.RequestException as erro:  # ex.: conexão cortada no meio do download
            if n == tentativas:
                raise
            print(f"{dia:%d/%m/%Y}: falha ({type(erro).__name__}), tentando de novo...", flush=True)
            time.sleep(10 * n)
    if resp.status_code == 200 and resp.content[:2] == b"PK":  # assinatura de zip
        return resp.content
    return None


def ultimo_pregao(referencia: date | None = None, max_dias: int = 10,
                  tipo: int = TIPO_DERIVATIVOS) -> tuple[date, bytes]:
    """Procura o arquivo mais recente a partir do dia anterior à referência."""
    dia = (referencia or date.today()) - timedelta(days=1)
    for _ in range(max_dias):
        if dia.weekday() < 5:  # pula fim de semana sem fazer requisição
            conteudo = baixar_zip(dia, tipo)
            if conteudo:
                return dia, conteudo
        dia -= timedelta(days=1)
    raise RuntimeError(f"Nenhum arquivo encontrado nos últimos {max_dias} dias.")


def baixar_periodo(inicio: date, fim: date, raw_dir: Path = RAW_DIR) -> list[Path]:
    """Salva em raw_dir os pregões entre inicio e fim (inclusive) que ainda não estão lá."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    salvos = []
    dia = inicio
    while dia <= fim:
        destino = raw_dir / nome_arquivo(dia)
        if dia.weekday() < 5 and not destino.exists():
            conteudo = baixar_zip(dia)
            if conteudo:
                # grava num arquivo temporário e só depois renomeia: se o processo cair no meio,
                # não fica um .zip truncado que seria pulado ("já existe") nas próximas execuções
                parcial = destino.with_suffix(".part")
                parcial.write_bytes(conteudo)
                parcial.replace(destino)
                salvos.append(destino)
                print(f"{dia:%d/%m/%Y}: {len(conteudo) / 1_048_576:.0f} MB", flush=True)
            else:
                print(f"{dia:%d/%m/%Y}: sem arquivo (feriado ou indisponível)", flush=True)
            time.sleep(PAUSA_S)
        dia += timedelta(days=1)
    return salvos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dias", type=int, default=30, help="quantos dias corridos para trás (padrão: 30)")
    args = parser.parse_args()
    hoje = date.today()
    novos = baixar_periodo(hoje - timedelta(days=args.dias), hoje - timedelta(days=1))
    print(f"{len(novos)} pregões novos em {RAW_DIR}")
