"""Refaz o estudo inteiro a partir dos arquivos de data/raw/.

Etapas: testes -> pipeline (só pregões novos) -> comparação com o manifesto -> notebooks em ordem.

Uso:
    python -m src.executar                        # tudo
    python -m src.executar --sem-notebooks        # só testes, pipeline e comparação
    python -m src.executar --atualizar-manifesto  # grava o manifesto com os dados atuais

Os textos dos notebooks e dos relatórios citam números de uma amostra específica (a do manifesto).
Se a amostra mudar, os notebooks são refeitos com os dados novos, mas os textos não; por isso o
manifesto só é atualizado com --atualizar-manifesto, depois de os textos serem revisados.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

import nbformat
from nbclient import NotebookClient

from src import manifesto
from src.pipeline import ROOT_DIR, build

NOTEBOOKS = ["00_exploracao_wdo_win.ipynb", "ch02_statistical_learning.ipynb", "ch03_linear_regression.ipynb"]


def rodar_testes() -> None:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT_DIR)
    if r.returncode != 0:
        sys.exit("Testes falharam; nada foi executado.")


def comparar_amostra() -> bool:
    """Compara os arquivos de data/raw/ com o manifesto. Devolve True se a amostra for a mesma."""
    atual = manifesto.gerar()
    if not manifesto.MANIFESTO.exists():
        print("Sem manifesto de referência (relatorios/dados_usados.csv).")
        return False
    dif = manifesto.comparar(atual, manifesto.ler())
    if not any(dif.values()):
        print(f"Amostra igual à do manifesto: {len(atual)} pregões, de {atual['pregao'].iloc[0]} a {atual['pregao'].iloc[-1]}.")
        return True
    for nome, dias in dif.items():
        if dias:
            print(f"Pregões {nome} em relação ao manifesto: {', '.join(dias)}")
    print("A amostra mudou: os textos dos notebooks e dos relatórios citam os números da amostra anterior.")
    return False


def executar_notebooks() -> None:
    for nome in NOTEBOOKS:
        caminho = ROOT_DIR / "notebooks" / nome
        inicio = time.time()
        nb = nbformat.read(caminho, as_version=4)
        NotebookClient(nb, timeout=3600, kernel_name="python3",
                       resources={"metadata": {"path": str(caminho.parent)}}).execute()
        nbformat.write(nb, caminho)
        print(f"{nome}: {time.time() - inicio:.0f} s", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sem-notebooks", action="store_true", help="não executa os notebooks")
    parser.add_argument("--atualizar-manifesto", action="store_true", help="grava relatorios/dados_usados.csv com os dados atuais")
    args = parser.parse_args()

    rodar_testes()
    novos = build()
    print(f"Pipeline: {len(novos)} pregões novos processados.")
    comparar_amostra()
    if not args.sem_notebooks:
        executar_notebooks()
    if args.atualizar_manifesto:
        manifesto.gravar(manifesto.gerar())
        print(f"Manifesto gravado em {manifesto.MANIFESTO.relative_to(ROOT_DIR)}.")
