# Glossário

Conceitos de mercado, microestrutura e estatística que aparecem neste estudo. Cada um tem o que é, por que importa aqui e onde aparece no repositório. A lista cresce conforme novos conceitos entram no código.

**Sumário:** [Mercado e contratos](#mercado-e-contratos) · [Microestrutura](#microestrutura) · [Retornos e estatística descritiva](#retornos-e-estatística-descritiva) · [Regressão e inferência](#regressão-e-inferência) · [Aprendizado estatístico (ISLP cap. 2)](#aprendizado-estatístico-islp-cap-2) · [Validação de modelos](#validação-de-modelos)

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
- **Aqui:** explica a pausa na abertura de 26/10 e a barra do WIN às 18:31. A negociação contínua do WIN termina às 18:24:59. Às 18:31, o leilão de fechamento executa de uma vez, num preço único e em ~5 ms, de 800 a 3.100 negócios (8 a 31 mil contratos). `trading_segments()` em [src/features.py](src/features.py) evita que esses saltos virem "retornos de 1 minuto".
- **Limitação para a tick rule:** num leilão não há agressor. Todos os negócios saem no mesmo preço e herdam o sinal do último negócio antes do leilão.

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

### Tamanho do negócio: contagem × volume
Uma estatística sobre negócios pode ser feita **por contagem** (cada negócio vale 1) ou **ponderada pelo volume** (cada negócio vale o número de contratos). Quando a distribuição do tamanho é muito assimétrica, as duas contam histórias diferentes.
- **Aqui:** 67% dos negócios do WDO são de 1 contrato, mas eles movimentam só 16% do volume. Já os negócios de 11 contratos ou mais são menos de 8% e carregam ~60% dos contratos ([notebook 00](notebooks/00_exploracao_wdo_win.ipynb)).
- **Limitação:** o tamanho do *negócio* não é o tamanho da *ordem*. Uma ordem grande que encontra várias ordens pequenas no livro vira vários negócios pequenos.

### Negócio direto (oferta direta)
Pela regra da B3 (Manual de Procedimentos Operacionais de Negociação), a oferta direta é "composta por uma oferta de compra e uma oferta de venda [...] registradas simultaneamente por um mesmo preço e pelo mesmo participante, representando o cliente comprador e o cliente vendedor". A B3 só aceita a oferta direta entre a melhor oferta de compra e a de venda (ou nelas, para ordens grandes), rejeita durante leilão e exige um lote mínimo (500 contratos no WDO e no WIN, pelo Ofício Circular 176/2022-PRE; o valor é revisado). Não há agressor.
- **Fonte:** [parecer da CVM sobre ofertas diretas (2021)](https://conteudo.cvm.gov.br/export/sites/cvm/decisoes/anexos/2021/20211123/2389_21.pdf), que reproduz a regra do MPO, e [OC 176/2022-PRE](https://www.b3.com.br/data/files/51/B1/C5/83/E6D05810F534EB48AC094EA8/OC%20176-2022%20PRE%20Regras%20para%20Registro%20de%20Ofertas%20Diretas%20%E2%80%93%20Tamanho%20M%C3%ADnimo%20e%20Thresholds%20de%20Ofertas%20Diretas...%20(PT).pdf).
- **Proxy usada aqui:** o arquivo público não marca os diretos. `direct_trade_proxy()` em [src/features.py](src/features.py) marca os negócios com a mesma corretora dos dois lados, pelo menos 500 contratos e fora dos leilões. A regra diz como um direto tem de ser, mas não garante que todo negócio assim seja direto. Uma corretora que agrediu uma oferta de outro cliente dela também passa no filtro.
- **Aqui:** acima de 5.000 contratos, 97–100% dos negócios têm a mesma corretora dos dois lados, contra 16–40% nos negócios comuns ([notebook 00](notebooks/00_exploracao_wdo_win.ipynb)). Para a tick rule eles são ruído, porque um negócio direto de 30 mil contratos vira uma "agressão" falsa. Por isso as barras têm `imbalance` (todos os negócios) e `imbalance_sem_diretos` (sem a proxy).

### Cauda longa e função de sobrevivência (CCDF)
A **função de sobrevivência** P(X ≥ x) dá, para cada valor x, a fração das observações que são pelo menos x. Em escala log-log, uma distribuição de **cauda curta** (como a exponencial) despenca, enquanto uma de **cauda longa** desce quase em linha reta e chega a valores enormes. Uma reta em log-log é a marca de uma *cauda de potência*.
- **Por que importa:** com cauda longa, a média é puxada por poucos valores extremos e descreve mal o caso típico.
- **Aqui:** o tamanho dos negócios. Com a mesma média, uma distribuição de cauda curta tornaria um negócio de 100 contratos praticamente impossível (5 em 1 trilhão no WDO). Nos dados, é 1 em cada 369, e 1 em cada ~40 mil negócios do WDO passa de 1.000 contratos.
- **Como ler o gráfico:** os dois eixos estão em **escala logarítmica** (cada marca vale 10 vezes a anterior), para caberem frações de 1 até 0,00000001. Uma curva quase reta quer dizer que, cada vez que o tamanho é multiplicado por 10, a chance cai por um fator parecido.

### Distribuição geométrica
A "exponencial" dos números inteiros: cada passo (aqui, cada contrato a mais) multiplica a probabilidade por um fator fixo. É o exemplo clássico de **cauda curta**, porque a probabilidade cai rápido demais para produzir valores enormes.
- **Aqui:** é a linha tracejada de referência no gráfico de P(tamanho ≥ x) do [notebook 00](notebooks/00_exploracao_wdo_win.ipynb), com a mesma média dos dados (fator 0,77 por contrato no WDO).

### Curva de concentração
Ordena os itens do maior para o menor e mostra que fração do total os x% maiores carregam. Se todos fossem iguais, a curva seria a diagonal. Quanto mais longe dela, mais concentrado.
- **Aqui:** os 1% maiores negócios carregam 24% do volume do WDO e 14% do WIN.

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
- **Aqui:** os retornos de 1 minuto têm curtose 15 (WDO) e 21 (WIN). Movimentos extremos são muito mais comuns do que a normal prevê. A curtose depende de poucos minutos: no WDO, uma única queda de 47 bps em 1 minuto (19/11, 12:03) faz boa parte dela.

### Assimetria (*skewness*)
Mede se a distribuição pende para um lado. Negativa: quedas fortes são mais comuns que altas fortes. Positiva: o contrário.
- **Limitação:** é muito sensível a poucos pontos. Aqui, a assimetria do WIN muda de −0,05 para −0,66 só de tirar 26/10.

### Autocorrelação (ACF)
A correlação de uma série com ela mesma defasada em k períodos ("lag k"): o minuto anterior ajuda a prever o próximo? A banda ±1,96/√n indica até onde o valor ainda é indistinguível de zero.
- **Limitação:** a banda supõe variância constante. Com aglomeração de volatilidade, ela fica estreita demais e exagera a significância.
- **Aqui:** no [notebook 00](notebooks/00_exploracao_wdo_win.ipynb), sem 26/10, o lag 1 do WDO (−0,031) fica fora da banda, mas com erros HAC o t cai de −3,4 para −1,9 e deixa de ser significativo.

### Aglomeração de volatilidade (*volatility clustering*)
Períodos agitados tendem a vir seguidos de períodos agitados, e calmos de calmos. Aparece como autocorrelação positiva de |retorno|, mesmo quando o retorno em si não tem autocorrelação.
- **Aqui:** a autocorrelação de |ret| fica entre 0,29 e 0,33 com todos os pregões e em ~0,22 sem 26/10. A *intensidade* do movimento é previsível, mas a *direção* não.

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
- **Aqui:** as regressões do [notebook 00](notebooks/00_exploracao_wdo_win.ipynb) usam `cov_type="HAC"`. No teste de reversão de 1 minuto, o HAC reduz o |t| quase pela metade em relação ao erro-padrão comum.

### Retornos sobrepostos
Retornos de horizonte maior que o intervalo das observações compartilham minutos: o retorno de 9h00–9h05 e o de 9h01–9h06 têm 4 minutos em comum. Isso cria autocorrelação nos erros da regressão por construção, mesmo sem nenhum sinal.
- **Por que importa:** sem correção, os t ficam inflados. O HAC precisa de `maxlags` pelo menos igual ao horizonte.
- **Aqui:** os testes de 5 e 15 minutos do [notebook 00](notebooks/00_exploracao_wdo_win.ipynb) usam `maxlags` = horizonte + 5.

### Testes múltiplos e correção de Bonferroni
Com um limite de 5%, 1 em cada 20 testes dá "significativo" por puro acaso. Ao testar muitas hipóteses, algum falso positivo é quase certo. Bonferroni divide o nível de significância pelo número de testes: com 18 testes, o |t| exigido sobe de ~2 para ~3. É o tema do cap. 13 do ISLP.
- **Aqui:** no [notebook 00](notebooks/00_exploracao_wdo_win.ipynb), dos 18 testes registrados (2 ativos × 3 horizontes × 3 preditores), só 1 passa de |t| > 1,96 (o fluxo do WIN "prevendo" os 5 minutos seguintes, t = −2,0), e ele não sobrevive à correção (|t| > 2,99). Com 18 testes, o acaso sozinho já daria em média 0,9 "significativo". Com 20 pregões, o teste que passava era outro ("WDO antecipa o WIN em 1 minuto", t = −2,7), que caiu para −1,7 com 2 pregões a mais: falsos positivos mudam de lugar quando a amostra cresce.

### Antecipação (*lead-lag*)
Quando o movimento de um ativo hoje ajuda a prever o movimento de outro **depois**. É diferente de correlação no mesmo instante, que não serve para prever nada.
- **Aqui:** WDO e WIN têm correlação de −0,46 no mesmo minuto, mas nenhum antecipa o outro em 1 a 15 minutos.

### Correlação × causalidade
Duas variáveis andarem juntas não quer dizer que uma cause a outra. As duas podem estar reagindo a uma terceira coisa, como uma notícia.
- **Aqui:** volume e volatilidade sobem juntos, mas isso não prova que o volume causa a volatilidade.

---

## Aprendizado estatístico (ISLP cap. 2)

### f(X), erro redutível e erro irredutível
O ponto de partida do curso é **Y = f(X) + ε**. O melhor palpite para Y quando se conhece X é f(x) = E[Y | X = x], a média de Y entre os casos com aquele x. Essa f ideal se chama **função de regressão**, e é ela que minimiza o erro quadrático médio. O erro de um modelo tem duas partes: a **redutível**, que vem de estimar f mal e diminui com um modelo melhor, e a **irredutível**, que é a variância de ε. Essa segunda nenhum modelo elimina, porque ε depende de coisas que não estão em X.
- **Por que importa:** em retornos de curto prazo, quase todo o erro é irredutível.
- **Limitação:** o erro só é "irredutível" em relação às features escolhidas. Com outra informação, parte dele poderia ser explicada.
- **Aqui:** seção 1 do [notebook do cap. 2](notebooks/ch02_statistical_learning.ipynb). A direção do próximo minuto é quase toda irredutível, e a intensidade não.

### Flexibilidade de um modelo
O quanto um modelo consegue se dobrar para seguir os dados. Uma reta é pouco flexível, porque só tem inclinação e intercepto. Um KNN com K=1 é flexível ao extremo, porque cada previsão copia o ponto mais próximo. Mais flexibilidade significa menos viés e mais variância.
- **Aqui:** no KNN, a flexibilidade é 1/K. Os gráficos do [notebook do cap. 2](notebooks/ch02_statistical_learning.ipynb) usam 1/K no eixo horizontal.

### Modelo paramétrico (estruturado) × não paramétrico
Um modelo **paramétrico** supõe uma forma para f (por exemplo, uma reta) e estima poucos números. É estável, mas erra se a forma estiver errada. Um modelo **não paramétrico**, como o KNN, não supõe forma nenhuma. Ele se adapta melhor, mas precisa de muito mais dados e sofre com muitas features.
- **Exemplo intermediário:** o modelo **quadrático** (y = b0 + b1·x + b2·x²) continua paramétrico e é estimado como uma regressão linear, mas consegue fazer curva.
- **Aqui:** na seção 1 do [notebook do cap. 2](notebooks/ch02_statistical_learning.ipynb), reta, parábola e KNN aparecem lado a lado.

### Interpretabilidade, parcimônia e caixa-preta
Quanto mais flexível o modelo, mais difícil entender *por que* ele prevê o que prevê. Uma regressão linear mostra o efeito de cada feature num coeficiente. Um KNN ou um boosting (cap. 8) são **caixas-pretas**. **Parcimônia** é preferir o modelo mais simples, com menos features, quando ele prevê quase tão bem quanto o complexo.
- **Aqui:** na seção 5, uma linear com só 3 features (as defasagens de |ret|) chega a 18,9% de R² no WIN, contra 24,2% do melhor KNN (escolhido olhando o teste).

### KNN (K vizinhos mais próximos)
Para prever num ponto x, o KNN pega os K exemplos do treino mais próximos de x. Na **regressão**, tira a média do Y deles. Na **classificação**, escolhe a classe mais frequente entre eles. É a forma mais direta de estimar E[Y | X = x].
- **Limitação:** usa distância, então as features precisam estar na mesma escala (ver padronização). Também sofre com a maldição da dimensionalidade.
- **Aqui:** `KNeighborsRegressor` e `KNeighborsClassifier` (scikit-learn) no [notebook do cap. 2](notebooks/ch02_statistical_learning.ipynb).

### Padronização
Subtrair a média e dividir pelo desvio-padrão de cada feature, para que todas fiquem na mesma escala. Sem isso, no KNN, uma feature medida em minutos (0 a 560) dominaria outra medida em bps (0 a 10) só por causa da unidade. A média e o desvio-padrão vêm **só do treino**, para não vazar informação do teste.
- **Aqui:** `StandardScaler` antes de cada KNN.

### Treino × teste e MSE
O modelo é ajustado no **treino** e avaliado no **teste**, que são dados que ele não viu. O **MSE** (*mean squared error*) é a média dos erros ao quadrado. O MSE de treino sempre cai quando o modelo fica mais flexível. O que interessa é o de teste.

### Overfitting (sobreajuste)
Quando o modelo decora o ruído do treino: erro de treino baixo e erro de teste alto.
- **Aqui:** o KNN com K=1 tem erro de treino zero e é o pior modelo no teste, com R² fora da amostra de −89% a −145% na direção.

### Trade-off viés-variância
O erro de teste esperado é a soma de três partes: **viés²**, o erro por o modelo ser simples demais para a forma verdadeira de f; **variância**, o quanto a previsão muda se o modelo for treinado em outra amostra; e o **erro irredutível**. Aumentar a flexibilidade troca viés por variância. O ótimo fica no meio, e por isso a curva de erro de teste tem forma de "U".
- **Aqui:** na seção 3.1 do [notebook do cap. 2](notebooks/ch02_statistical_learning.ipynb), uma simulação com f conhecido mede as três partes separadamente.

### Maldição da dimensionalidade
Com muitas features, os pontos ficam espalhados e até os "vizinhos mais próximos" estão longe. Métodos locais, como o KNN, pioram rápido.
- **Aqui:** com 9 features, o raio da vizinhança que contém 10% dos minutos já cobre ~60% da distância típica entre dois minutos quaisquer. Com 50 features de ruído, o KNN perde ~40% do R² e a regressão linear quase nada.

### R² fora da amostra (MSE relativo)
MSE relativo = MSE do modelo no teste / MSE do chute ingênuo (prever sempre a média do treino). R² fora da amostra = 1 − MSE relativo. Se for positivo, o modelo acrescenta informação. Se for negativo, ele é **pior** do que não saber nada, algo que o R² dentro da amostra nunca mostra.

### Taxa de erro e chute ingênuo (*baseline*)
Na classificação, a **taxa de erro** é a fração de previsões erradas. O **chute ingênuo** é prever sempre a classe mais comum no treino. Um classificador só tem valor se errar menos que isso.

### Classificador de Bayes e erro de Bayes
O classificador de Bayes escolhe, para cada x, a classe mais provável, P(Y | X = x). Ele tem o menor erro possível, o **erro de Bayes**, que é o erro irredutível da classificação. Na prática, P(Y | X) é desconhecida, então ele serve de referência teórica. O KNN tenta aproximá-lo.
- **Fronteira de decisão de Bayes:** o conjunto de pontos x em que duas classes empatam em probabilidade (com duas classes, onde P = 0,5). De um lado da fronteira o classificador escolhe uma classe; do outro, a outra.
- **Aqui:** na seção 4.2, uma simulação em que P(Y | X) é conhecida. A fronteira é `abs_ret` ≈ 3,45 bps, o erro de Bayes é 42,0%, e o melhor KNN chega a 42,3%.

### Probabilidade estimada e calibração
Além da classe, um classificador pode dar a probabilidade de cada classe (no KNN, a fração de vizinhos de cada classe). Uma probabilidade é **calibrada** quando, entre os casos com p̂ ≈ 0,7, cerca de 70% são de fato daquela classe. Um modelo pode **ordenar** bem os casos (os de p̂ alto são mais arriscados que os de p̂ baixo) e mesmo assim errar o **nível** das probabilidades.
- **Por que importa:** decisões de risco e de tamanho de posição usam a probabilidade, não só a classe.
- **Aqui:** na seção 4.1, o KNN ordena bem os minutos por chance de agitação, mas superestima essa chance, porque aprendeu num período mais agitado que o teste.

---

## Validação de modelos

### Retorno futuro (alvo) e viés de *look-ahead*
O alvo de um modelo de previsão é o que acontece **depois** (ex.: `fwd_ret_1`, o retorno do próximo minuto). *Look-ahead* é usar, sem querer, informação que ainda não estaria disponível no momento da decisão. Isso produz resultados ótimos e falsos.
- **Aqui:** `front_month()` escolhe o vencimento pelo volume do dia inteiro, o que às 9h não seria conhecido. É aceitável para estudar barras, porque a troca é nítida, mas não para simular uma estratégia. O mesmo cuidado vale para a padronização e para o limiar "agitado" do cap. 2, que são calculados só com o treino.

### Mudança de regime (não estacionariedade)
O comportamento do mercado muda ao longo do tempo (volatilidade, volume, correlações). Um modelo treinado num período pode encontrar outro "mundo" no teste.
- **Aqui:** o treino do cap. 2 inclui 26/10, e o teste (11/11 a 19/11) foi mais calmo. Só 39–41% dos minutos do teste ficaram acima da mediana de |retorno| do treino.

### Validação *walk-forward*
Treinar com o passado e testar no período seguinte, avançando a janela no tempo. É a forma correta de validar em séries temporais. O k-fold aleatório mistura passado e futuro e vaza informação (cap. 5 do ISLP).
