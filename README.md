# ISLP aplicado a WDO e WIN (B3)

Estudo do curso **Statistical Learning with Python** (Stanford Online / edX, Hastie & Tibshirani), aplicando cada capítulo a dados **negócio a negócio** dos minicontratos futuros da B3:

- **WDO**: mini dólar
- **WIN**: mini Ibovespa

A ideia não é só refazer os labs do livro. Em cada capítulo, levo o método para dados reais de mercado e procuro dinâmicas nesses dois ativos, que são muito líquidos.

- Livro: *An Introduction to Statistical Learning with Applications in Python* (James, Witten, Hastie, Tibshirani, Taylor, 2023). PDF gratuito em [statlearning.com](https://www.statlearning.com/).
- Curso: [edX — Statistical Learning with Python](https://learning.edx.org/course/course-v1:StanfordOnline+SOHS-YSTATSLEARNINGP+1T2024/home)

## Progresso

| Cap. | Tema | Aplicação em WDO/WIN | Status |
|---|---|---|---|
| 2 | Statistical Learning | Exploração dos dados: volume intradiário, caudas, autocorrelação, fluxo × retorno | 🟡 notebook 00 pronto, aguardando dados |
| 3 | Regressão linear | Retorno do próximo minuto ~ desequilíbrio de agressão + retornos defasados + volume; diagnósticos e erros robustos | ⬜ |
| 4 | Classificação | Direção do próximo movimento: logística, LDA/QDA, Naive Bayes, KNN contra um baseline ingênuo | ⬜ |
| 5 | Reamostragem | k-fold × *walk-forward*: medir o vazamento de informação do futuro; bootstrap de métricas | ⬜ |
| 6 | Regularização | Ridge/Lasso com dezenas de features (lags, fluxo, horário, WIN→WDO) | ⬜ |
| 7 | Não linearidade | Splines/GAM: efeito do horário do dia e efeito não linear do fluxo | ⬜ |
| 8 | Árvores | Random Forest e Boosting; importância de variáveis | ⬜ |
| 9 | SVM | Classificação de direção com kernels | ⬜ |
| 10 | Deep Learning | MLP/RNN em sequências de barras (PyTorch, CPU) | ⬜ |
| 11 | Sobrevivência | Tempo até o preço andar ±N ticks (*time-to-event*, com censura no fim do pregão) | ⬜ |
| 12 | Não supervisionado | PCA das features; clusters de "tipos de dia" | ⬜ |
| 13 | Testes múltiplos | Testar muitos sinais e ver quantos sobrevivem a FDR/Bonferroni | ⬜ |

## Dados

**Fonte:** B3, [Boletim Diário do Mercado](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/consultas/boletim-diario/boletim-diario-do-mercado/) → *Derivativos → Derivativos de bolsa → Negócio a negócio*.

**Como obter:** baixe manualmente o arquivo de cada pregão (`.zip`) e salve em `data/raw/`, sem descompactar. A página da B3 proíbe coleta automatizada, por isso o repositório **não tem scraper**. Pelo mesmo motivo, e também por tamanho, os dados **não são versionados** (`data/` está no `.gitignore`).

**Layout** (Glossário B3 *Negócios Listados*, separador `;`, decimal `,`):

| Coluna | Significado |
|---|---|
| `DataReferencia` / `DataNegocio` | data (AAAA-MM-DD) |
| `CodigoInstrumento` | ticker (ex.: `WDOZ26`, `WINZ26`) |
| `AcaoAtualizacao` | 0 = negócio, 2 = cancelado (removido no carregamento) |
| `PrecoNegocio`, `QuantidadeNegociada` | preço e quantidade |
| `HoraFechamento` | HHMMSSmmm, horário de Brasília |
| `CodigoIdentificadorNegocio` | id do negócio |
| `TipoSessaoPregao` | 1 = regular, 6 = after hours |
| `CodigoParticipanteComprador` / `Vendedor` | código da corretora de cada lado |
| `TipoDoCanal` | existe no arquivo real, mas não aparece no glossário |

**O que o arquivo real mostra** (pregão de 17/11/2026, `17-11-2026_NEGOCIOSAVISTA_DRV.txt`):
- Tamanho: 50 MB zipado, 520 MB de texto, 7,2 milhões de negócios. Só o WIN tem 5,9 milhões e o WDO 0,8 milhão. O loader lê em blocos e guarda apenas WDO/WIN, ocupando cerca de 300 MB por pregão em memória.
- **Cancelamento:** o negócio original (`AcaoAtualizacao = 0`) continua no arquivo, e o cancelamento entra como uma linha nova (`= 2`) com o mesmo instrumento e id. O loader remove as duas.
- **Ids:** `CodigoIdentificadorNegocio` só é único *dentro* de cada instrumento. WDO e WIN repetem ids.
- **Datas:** algumas centenas de linhas têm `DataNegocio` diferente do pregão (por exemplo, 01h do dia anterior) e são descartadas.
- **Mesmo milissegundo:** cerca de 2/3 dos negócios dividem o milissegundo com outro. A ordem do arquivo é preservada com uma ordenação estável.

> ⚠️ O arquivo **não informa o lado agressor**. O fluxo de compra e venda é *estimado* pela *tick rule* (Lee & Ready, 1991): se o preço sobe em relação ao negócio anterior, conta como compra agressora. Isso é uma aproximação e vale lembrar disso ao interpretar os resultados.

## Estrutura

```
src/
  b3_loader.py   # lê os .zip da B3, filtra WDO/WIN, remove cancelados, monta timestamps
  features.py    # vencimento principal, tick rule, barras de tempo, retornos futuros
notebooks/
  00_exploracao_wdo_win.ipynb
  chXX_*.ipynb   # um por capítulo do curso
data/            # (não versionado) raw/ = .zip da B3, processed/ = parquet
```

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu   # só para o cap. 10
```

Depois, abra `notebooks/00_exploracao_wdo_win.ipynb` e rode tudo. O notebook lê `data/raw/` e grava um `.parquet` em `data/processed/`.

## Cuidados metodológicos

- **Sem k-fold aleatório em série temporal.** A validação é sempre *walk-forward*: treino no passado, teste no futuro.
- **Retornos não atravessam a noite.** Alvos e defasagens são calculados dentro de cada pregão.
- **Viés de mineração de dados (cap. 13).** Testar muitos sinais e reportar só o melhor gera falsos positivos. Todos os testes ficam registrados.
- **Custos.** Um sinal estatisticamente significativo pode não sobreviver ao *spread* e aos emolumentos. Na hora de avaliar, a comparação é sempre contra 1 tick de custo.
