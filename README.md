# ISLP aplicado a WDO e WIN (B3)

Estudo do curso **Statistical Learning with Python** (Stanford Online / edX, Hastie & Tibshirani), aplicando cada capítulo a dados **negócio a negócio** dos minicontratos futuros da B3:

- **WDO**: mini dólar
- **WIN**: mini Ibovespa

A ideia não é só refazer os labs do livro. Em cada capítulo, levo o método para dados reais de mercado e procuro dinâmicas nesses dois ativos, que são muito líquidos.

- Livro: *An Introduction to Statistical Learning with Applications in Python* (James, Witten, Hastie, Tibshirani, Taylor, 2023). PDF gratuito em [statlearning.com](https://www.statlearning.com/).
- Curso: [edX — Statistical Learning with Python](https://learning.edx.org/course/course-v1:StanfordOnline+SOHS-YSTATSLEARNINGP+1T2024/home)
- Glossário: [GLOSSARIO.md](GLOSSARIO.md), com os conceitos de mercado, microestrutura e estatística usados no estudo.

## Progresso

| Cap. | Tema | Aplicação em WDO/WIN | Status |
|---|---|---|---|
| 2 | Statistical Learning | Exploração dos dados: volume intradiário, caudas, autocorrelação, fluxo × retorno | ✅ aulas (19/11/2026); exploração no [notebook 00](notebooks/00_exploracao_wdo_win.ipynb); f(X), viés-variância, dimensionalidade e Bayes no [notebook do cap. 2](notebooks/ch02_statistical_learning.ipynb) |
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

## Amostra atual

22 pregões, de 20/10/2026 a 19/11/2026, com o vencimento principal de WDO e WIN em barras de 1 minuto. Detalhes no [notebook 00](notebooks/00_exploracao_wdo_win.ipynb).

![Preços de WDO e WIN, 20/10 a 19/11/2026](figures/precos_wdo_win.png)

O salto em 26/10 é real: de sexta para segunda, o WDO abriu **+9,2%** e o WIN **−14,9%**. É um dia atípico, que altera vários resultados, e por isso as análises são feitas com e sem ele.

## Dados

**Fonte:** B3, [Boletim Diário do Mercado](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/consultas/boletim-diario/boletim-diario-do-mercado/) → *Derivativos → Derivativos de bolsa → Negócio a negócio*.

**Endereço de download:** a página do Boletim é só uma moldura. O conteúdo vem do aplicativo `arquivos.b3.com.br/bdi`, e o botão "Negócio a negócio → Derivativos" desse aplicativo baixa de `https://drp.b3.com.br/rapinegocios/tickercsv/AAAA-MM-DD?type=1` (`type=1` = derivativos, `type=2` = renda variável). Isso está no código público do aplicativo: `config.js` define `tickerApi` e a função `GetStorageUrl2` monta a URL, conferido em 20/11/2026. O script usa a mesma URL, então os arquivos são os mesmos do download manual.

**Como obter:** `python -m src.b3_download --dias 30` baixa os pregões que ainda não estão em `data/raw/`. Ele faz uma requisição por pregão, com pausa entre elas, e grava os `.zip` sem descompactar. Também dá para baixar manualmente pelo site e salvar na mesma pasta. A B3 só mantém os pregões mais recentes: em 18/11/2026, o dia 19/10 já não estava disponível. Por isso vale rodar o download com frequência para acumular histórico. Os dados **não são versionados** (`data/` está no `.gitignore`), por tamanho e pelos termos de uso da B3.

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
- **Mesmo milissegundo:** cerca de 3/4 dos negócios dividem o milissegundo com outro (75% no WIN e 78% no WDO). A ordem do arquivo é preservada com uma ordenação estável.

- **Negócios diretos:** o arquivo também não marca os negócios diretos (a corretora casa dois clientes dela, sem agressor). As barras trazem duas versões do fluxo: `imbalance`, com todos os negócios, e `imbalance_sem_diretos`, sem os prováveis diretos (proxy baseada nas regras da B3; ver `direct_trade_proxy` em `src/features.py` e o [glossário](GLOSSARIO.md#negócio-direto-oferta-direta)).

> ⚠️ O arquivo **não informa o lado agressor**. O fluxo de compra e venda é *estimado* pela *tick rule* (Lee & Ready, 1991): se o preço sobe em relação ao negócio anterior, conta como compra agressora. Isso é uma aproximação e vale lembrar disso ao interpretar os resultados.

## Estrutura

```
src/
  b3_download.py # baixa os .zip de negócio a negócio para data/raw/
  b3_loader.py   # lê um .zip, filtra WDO/WIN, remove cancelados, monta timestamps
  features.py    # vencimento principal, tick rule, leilões, proxy de negócios diretos, barras, defasagens, retornos futuros
  pipeline.py    # processa um pregão por vez: data/raw/*.zip -> data/processed/*.parquet
notebooks/
  00_exploracao_wdo_win.ipynb
  ch02_statistical_learning.ipynb
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

Depois:

```bash
python -m src.b3_download --dias 30   # ~55 MB por pregão
python -m src.pipeline                # ~1 min por pregão; só processa os dias novos
python -m src.pipeline --refazer      # reprocessa tudo (quando o cálculo das barras mudar)
```

e abra `notebooks/00_exploracao_wdo_win.ipynb`. Os notebooks leem os Parquet de `data/processed/`. Um pregão de WDO+WIN tem cerca de 6,7 milhões de negócios, e processar um dia por vez mantém a memória sob controle.

## Cuidados metodológicos

- **Sem k-fold aleatório em série temporal.** A validação é sempre *walk-forward*: treino no passado, teste no futuro.
- **Retornos não atravessam a noite.** Alvos e defasagens são calculados dentro de cada pregão.
- **Viés de mineração de dados (cap. 13).** Testar muitos sinais e reportar só o melhor gera falsos positivos. Todos os testes ficam registrados.
- **Custos.** Um sinal estatisticamente significativo pode não sobreviver ao *spread* e aos emolumentos. Na hora de avaliar, a comparação é sempre contra 1 tick de custo.
