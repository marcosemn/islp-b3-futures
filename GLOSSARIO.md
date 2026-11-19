# Glossário

Conceitos de mercado, microestrutura e estatística que aparecem neste estudo. Cada um tem o que é, por que importa aqui e onde aparece no repositório. A lista cresce conforme novos conceitos entram no código.

**Sumário:** [Mercado e contratos](#mercado-e-contratos) · [Microestrutura](#microestrutura) · [Retornos e estatística descritiva](#retornos-e-estatística-descritiva) · [Regressão e inferência](#regressão-e-inferência) · [Validação de modelos](#validação-de-modelos)

---

## Mercado e contratos

### WDO e WIN (minicontratos futuros)
Contratos futuros negociados na B3. **WDO** (mini dólar) vale US$ 10 mil. **WIN** (mini Ibovespa) vale R$ 0,20 por ponto do índice. Os dois são os ativos mais negociados da bolsa, com milhões de negócios por dia.
- **Aqui:** são os dois ativos estudados.

### Tick (variação mínima de preço)
O menor passo em que o preço pode mudar: **0,5 ponto no WDO** (R$ 5 por contrato) e **5 pontos no WIN** (R$ 1 por contrato).
- **Por que importa:** um movimento previsto menor que 1 tick dificilmente paga os custos de operar.
- **Aqui:** [README](README.md#cuidados-metodológicos), na parte de custos.

### Vencimento principal (*front month*)
Em cada momento existem vários contratos de WDO e WIN, um para cada mês de vencimento (ex.: `WINZ26` vence em dezembro de 2026). O vencimento principal é o mais negociado do dia, e é ele que representa o "preço do mercado".
- **Aqui:** `front_month()` em [src/features.py](src/features.py) fica só com ele.

### Rolagem
Quando um contrato se aproxima do vencimento, o mercado migra para o seguinte. Os preços dos dois são um pouco diferentes, então a troca cria um pequeno salto artificial na série.
- **Aqui:** o WDO rolou de `WDOX26` para `WDOZ26` em 30/10/2026.

### Leilão de abertura e de fechamento
Períodos em que as ordens se acumulam sem negociar e depois são executadas todas a um único preço. A abertura pode ser estendida quando o preço se move demais.
- **Aqui:** explica a pausa na abertura de 26/10 e o negócio isolado do WIN às 18h31 todos os dias. `trading_segments()` em [src/features.py](src/features.py) evita que esses saltos virem "retornos de 1 minuto".

### Gap
Diferença entre o fechamento de um pregão e a abertura do seguinte, causada por notícias que saem com o mercado fechado.
- **Aqui:** em 26/10/2026, o WDO abriu +9,2% e o WIN −14,9% depois do 2º turno da eleição. Os retornos são calculados dentro de cada pregão, para que os gaps não contaminem as estatísticas de 1 minuto.

---

## Microestrutura

### Livro de ofertas, bid e ask
O livro reúne as ordens limitadas que esperam execução. O **bid** é a melhor oferta de compra (o maior preço que alguém aceita pagar) e o **ask** é a melhor oferta de venda (o menor preço que alguém aceita receber). O *spread* é a diferença entre os dois.

### Negócio × ordem
Um **negócio** é uma execução entre uma corretora compradora e uma vendedora. Uma **ordem** grande a mercado consome várias ordens do livro e gera vários negócios no mesmo milissegundo.
- **Aqui:** cerca de 80% dos negócios dividem o milissegundo com outro, e a maior rajada foi de 4.379 negócios do WIN em 1 ms ([notebook 00](notebooks/00_exploracao_wdo_win.ipynb)).

### Agressor
Quem toma a iniciativa do negócio, enviando uma ordem a mercado contra uma ordem que já estava no livro. Comprar "agredindo" o ask indica pressão compradora; vender no bid indica pressão vendedora.

### Tick rule (regra do tick)
Um jeito de **estimar** o agressor quando os dados não o informam (Lee & Ready, 1991). Se o preço subiu em relação ao negócio anterior, conta como compra agressora; se caiu, como venda; se ficou igual, repete o lado anterior.
- **Por que importa:** o arquivo público da B3 não traz o agressor.
- **Limitação:** é uma aproximação e erra com frequência. Como usa o próprio preço, qualquer relação entre o fluxo estimado e o retorno *do mesmo minuto* é quase automática.
- **Aqui:** `tick_rule()` em [src/features.py](src/features.py).

### Desequilíbrio de fluxo (*imbalance*)
(volume de compra agressora − volume de venda agressora) / volume total, num período. Vai de −1 (só vendas) a +1 (só compras).
- **Aqui:** coluna `imbalance` das barras de 1 minuto.

### Bid-ask bounce
Mesmo com o "preço justo" parado, os negócios alternam entre o bid e o ask, e o preço observado oscila. Isso cria uma **autocorrelação negativa artificial** nos retornos de prazo muito curto.

### Barras de tempo e OHLC
Agrupar os negócios em intervalos fixos (aqui, 1 minuto) e resumir cada um em **O**pen, **H**igh, **L**ow e **C**lose (abertura, máxima, mínima e fechamento), mais volume e número de negócios.
- **Aqui:** `time_bars()` em [src/features.py](src/features.py).

### VWAP
*Volume-Weighted Average Price*: o preço médio do período ponderado pelo volume de cada negócio.

---

## Retornos e estatística descritiva

### Log-retorno
log(preço atual / preço anterior). Para movimentos pequenos fica quase igual ao retorno percentual. A vantagem é que log-retornos de períodos seguidos podem ser somados.
- **Aqui:** coluna `ret` das barras.

### bps (*basis points*, pontos-base)
1 bp = 0,01%. Unidade prática para retornos pequenos, como os de 1 minuto.

### Curtose e caudas gordas
A curtose mede o peso das caudas da distribuição, ou seja, a frequência de eventos extremos. A distribuição normal tem curtose 3; acima disso, a distribuição é **leptocúrtica** (caudas gordas).
- **Aqui:** os retornos de 1 minuto têm curtose 12 (WDO) e 21 (WIN). Movimentos extremos são muito mais comuns do que a normal prevê.

### Assimetria (*skewness*)
Mede se a distribuição pende para um lado. Negativa: quedas fortes são mais comuns que altas fortes. Positiva: o contrário.
- **Limitação:** é muito sensível a poucos pontos. Aqui, a assimetria do WIN muda de −0,05 para −0,66 só de tirar 26/10.

### Autocorrelação (ACF)
A correlação de uma série com ela mesma defasada em k períodos ("lag k"): o minuto anterior ajuda a prever o próximo? A banda ±1,96/√n indica até onde o valor ainda é indistinguível de zero.

### Aglomeração de volatilidade (*volatility clustering*)
Períodos agitados tendem a vir seguidos de períodos agitados, e calmos de calmos. Aparece como autocorrelação positiva de |retorno|, mesmo quando o retorno em si não tem autocorrelação.
- **Aqui:** a autocorrelação de |ret| fica entre 0,2 e 0,3. A *intensidade* do movimento é previsível, mas a *direção* não.

### Volatilidade realizada
Raiz da soma dos retornos ao quadrado num período (aqui, os retornos de 1 minuto de um pregão). Mede quanto o preço oscilou de fato.

---

## Regressão e inferência

### OLS (mínimos quadrados ordinários)
A regressão linear comum (cap. 3 do ISLP): encontra a reta que minimiza a soma dos erros ao quadrado. O **beta** diz quanto Y muda, em média, quando X aumenta em 1 unidade.

### Erro-padrão e estatística t
O erro-padrão mede a incerteza da estimativa do beta. A estatística t = beta / erro-padrão diz quantos erros-padrão o beta está longe de zero. Como regra prática, |t| > 2 costuma ser considerado significativo a 5%.

### R²
A fração da variação de Y explicada pelo modelo, de 0 a 1. Em retornos de curto prazo, valores muito pequenos (como 0,1%) já são comuns, e mesmo assim podem ter valor econômico se forem estáveis.

### Erros-padrão HAC (Newey-West)
*Heteroskedasticity and Autocorrelation Consistent.* A fórmula padrão do erro-padrão supõe erros independentes e com variância constante. Em finanças isso falha: a volatilidade muda ao longo do tempo e observações vizinhas se influenciam. O resultado é um erro-padrão pequeno demais, e coisas parecem significativas sem ser. O HAC corrige o erro-padrão para esses dois problemas. O beta não muda, só a incerteza em volta dele.
- **Aqui:** as regressões do [notebook 00](notebooks/00_exploracao_wdo_win.ipynb) usam `cov_type="HAC"`.

### Testes múltiplos e correção de Bonferroni
Com um limite de 5%, 1 em cada 20 testes dá "significativo" por puro acaso. Ao testar muitas hipóteses, algum falso positivo é quase certo. Bonferroni divide o nível de significância pelo número de testes: com 18 testes, o |t| exigido sobe de ~2 para ~3. É o tema do cap. 13 do ISLP.
- **Aqui:** o "WDO antecipa o WIN em 1 minuto" (t = −2,7) não sobrevive à correção.

### Correlação × causalidade
Duas variáveis andarem juntas não quer dizer que uma cause a outra. As duas podem estar reagindo a uma terceira coisa, como uma notícia.
- **Aqui:** volume e volatilidade sobem juntos, mas isso não prova que o volume causa a volatilidade.

---

## Validação de modelos

### Retorno futuro (alvo) e viés de *look-ahead*
O alvo de um modelo de previsão é o que acontece **depois** (ex.: `fwd_ret_1`, o retorno do próximo minuto). *Look-ahead* é usar, sem querer, informação que ainda não estaria disponível no momento da decisão. Isso produz resultados ótimos e falsos.

### Validação *walk-forward*
Treinar com o passado e testar no período seguinte, avançando a janela no tempo. É a forma correta de validar em séries temporais. O k-fold aleatório mistura passado e futuro e vaza informação (cap. 5 do ISLP).
