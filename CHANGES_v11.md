# CHANGES v11 — QLIK_PPT_SalesCredit_DailyExport_v11.qvs

A v11 é o **QVS da analista** (`QLIK_PPT_SalesCredit_DailyExport 2026Jan.qvs`, transcrito das 16 fotos) **corrigido** para chegar no mesmo número do `Castine.py`.
Ela mantém do script original o que é ambiente e método. As regras de negócio que divergiam do Python foram trocadas pela lógica do v10, que já tinha passado pelo teste diferencial.
O v10 recebeu a rev 2 no mesmo dia (ver `CHANGES_v10.md`); as abas 04–12 da v11 são as dele.

Status: **nunca recarregado em engine Qlik**. A validação é o próprio reload, seguido da aba 13 (comparação).

## O que ficou da analista

| Item | Linhas originais | Na v11 |
|---|---|---|
| SETs de locale + `Must_Include` do `Config_QS.txt` | L1–24 | 00_Main |
| Conexões e pastas reais (`lib://Fldr_SDrive/...`, `SDrive`, `SDrive_SalesControlData`) | várias | 00b_Parameters, num único bloco |
| Leitura do XML com **XmlSimple** (`BatchFeed/TradeFeed`, `TransactionCosts/TransactionCost`) | L367–449 | 03_Load_BBGXML_TradeData |
| Pasta de saída UAT/castine | L638 | aba 11 (STORE), com prefixo `QLIK_V11_` até validar |
| Comparação Qlik × Python por `CompNum` | L28–151 | 13_Python_Comparison |
| Split matrix `RR Teams Split Matrix.xlsx`, aba `Split_Matrix` | L310 | o negócio confirmou que é o mesmo arquivo do Python |

## O que foi corrigido

| # | QVS da analista | v11 (= Castine.py) |
|---|---|---|
| 1 | `EXIT SCRIPT` na L151 parava o reload depois da comparação | A comparação vai para o fim (aba 13), com o liga/desliga `vRunCompare` |
| 2 | Só lia `f392fd1.ext.YY01*.4` com dia ≤ 30 | `*.ext.26*`, a maior versão de cada arquivo, limite opcional `vDateLimitToken` (o teste de janeiro equivale a `260130`) |
| 3 | Filtros na leitura do XML (TEST, X, Salesperson, Exists do split, ano) | Nenhum filtro na leitura. As regras rodam depois, na ordem do Python |
| 4 | Versão por OriginalTktId + MAX(TradeDate) | Por TransactionNumber → OriginalTktId → Sec+Data+Valor, ordenado por data do arquivo + AsOf, fica a última (aba 04) |
| 5 | Cancel removido antes do versionamento | Cancel removido **depois** (aba 04) |
| 6 | Gross = soma de todos os TransactionCost em USD por `Type` | 1º Cost fora de TransactionCosts (senão o 1º TC não-AddOn) + AddOn (`Code` R **antes** do Cost). A ordem Code/Cost vem do texto do arquivo, porque o XmlSimple não a preserva |
| 7 | Split sem janela de datas, sem validação, Split cru | Janela AsOf → Trade → data do payout; validação de soma 1 e de sobreposição; parse 25 / 25% / 0,25 (abas 05–06) |
| 8 | Join do split por RR Team cru | `normalize_team_key` nos dois lados |
| 9 | Moeda: filtrava linhas de custo | Exclui o trade com `SecurityCurrencyISOCode` ≠ USD (aba 07) |
| 10 | Sem as regras finais | GNCL/MULT/GNPL de 2026, Trade Date da versão original / dos modificados, RR Team 235, Client TEST (aba 10) |
| 11 | Repo sem RR Team, logo sem split; caminho fixo | Repo com split e a busca de arquivo do Python (aba 08) |
| 12 | Sem ajustes manuais | Aba 09 |
| 13 | GLCS: mappings montados e nunca aplicados | Tiara + GLCS do Python (aba 10b) |
| 14 | Sem arredondamento | round10 / round2 half-to-even; export com `%.2f` |
| 15 | `FROM $(var)` sem colchetes em caminho com espaço | Todos os FROM com colchetes |
| 16 | CSV do Python lido como Latin-1 (28591) | `utf8` |
| 17 | Datas ISO com `T` dependiam da interpretação automática | `fPdDate` e `ParseDateColumn` reconhecem `YYYY-MM-DDThh:mm:ss` (o v10 também recebeu) |

## rev 2 (2026-11-10) — onde estava o problema

| Mudança | Detalhe |
|---|---|
| Etiquetas `[FIX-01]` a `[FIX-18]` | Índice no cabeçalho do script. Em cada aba, um bloco com `WAS` (linha do QVS da analista), `PROBLEM` e `NOW` (função e linha do `Castine.py`). Tudo em inglês |
| Aba `11b_Fix_Log` | `TRACE [FIX-nn] métrica = valor` e tabela `FIX_LOG`, gravada em `QLIK_V11_fix_log_<data>.csv`. Mede nos dados do reload o que a regra antiga fazia: linhas que a versão por OriginalTktId deixaria, cancelados com versão anterior, trades com Gross diferente da regra antiga, times com mais de uma janela no split, entre outros |
| Comparação em 3 lados (aba 13) | Novo × Python × Atual (`QLIK_PPT_DailyExportOfPayout_<data>.csv`). Colunas `Status New vs Python` (tem que dar `MATCH`) e `Status Current vs Python` (onde a saída atual erra). Compara todas as Sources e o GLCS CODE |
| Saída sem sobrescrever a atual | Prefixo `vOutTag = 'QLIK_V11_'` em todos os arquivos. Depois de validar, trocar para `'QLIK_'` para substituir o export atual |
| Export do Python | Procura em `daily files/` e depois em `Sales/Data/castine/` (`vPythonExportLibs`) |
| Encoding de Repo, Tiara e ajustes | Mesma `DetectCodepage` do v10 rev 2 |
| Comentário corrigido | Saiu a afirmação de que `NULL <> 'TEST'` descartaria a linha (no Qlik, `A <> NULL` é verdadeiro) |

A tabela "O que foi corrigido" acima continua valendo; os números das linhas correspondem aos `[FIX-nn]` descritos em `Analise_QVS_Analista_vs_Python.md`.

## Regra da analista que não existe no Python

O filtro "AsOf no ano atual, ou no ano anterior só para traders do `Sales_Mapping.xlsx`" (L420–422) ficou **desligado**: `vApplySalesMappingYearFilter = 0`.
Se for regra nova do negócio, primeiro ela entra no Python de produção; depois é só ligar o switch.

## Premissas do XmlSimple (aparecem no TRACE do reload)

- `vXmlTradeFeedPath = 'BatchFeed/TradeFeed'`, como no script da analista.
- Arquivo em que nenhum trade tem mais de 1 TransactionCost: o XmlSimple achata o custo na tabela TradeFeed, e a v11 trata esse caso.
- ExtendedFields (Sec Type): espera a tabela `.../ExtendedFields/Field` com o atributo `name` e o texto em `Field`. Se o layout for outro, gera WARN e o Sec Type fica em branco.
- Se a contagem de `<TransactionCost>` no texto diferir da do XmlSimple, gera WARN e o AddOn passa a usar só `Code = R`.

## Teste feito

- Simulação da aba 03 sobre as 34 trades das fixtures do kit, comparada com `Castine.parse_tradefeed_to_row`: **0 diferenças** em campos, custo, AddOn, Salesperson, MasterAccountName e ExtendedFields.
  - Script: `scratchpad/v11/sim_tab03.py`.
  - Ele modela o XmlSimple; não executa Qlik.
- Lint estrutural: só os 3 CALLs de abort intencionais, os mesmos do v10.
- As abas 04–12 são as do v10, sem mudança de regra. A validação delas é o teste diferencial que já existia.
