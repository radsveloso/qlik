# QVS da analista × Castine.py — análise refeita (2ª edição, 2026-11-10)

**Objetivo:** o export do Qlik tem que ser idêntico ao do `Castine.py`.
**Situação:** o QVS da analista (`QLIK_PPT_SalesCredit_DailyExport 2026Jan.qvs`, 674 linhas, transcrito das fotos) gera a saída atual do Qlik, e essa saída não bate com o Python.

## 1. Como a análise foi refeita

- Reli o `Castine.py` do início ao fim: a configuração (L74–185) e o `main` (L3436–3830), função por função.
- Para cada regra, procurei a linha correspondente no QVS da analista.
- Cada diferença abaixo tem a linha do QVS e a função do Python. A coluna **Certeza** separa o que está escrito nos dois códigos do que depende dos dados reais.
- Nenhum script foi recarregado no Qlik. O que é medido nos dados reais fica para o reload: a v11 grava esses números no log (`[FIX-nn]`) e na tabela `FIX_LOG`.

## 2. A ordem das regras é diferente

| Passo | Castine.py (`main`) | QVS da analista |
|---|---|---|
| 1 | Lê **todos** os TradeFeeds de `*.ext.26*` (maior versão de cada arquivo) | Lê só `f392fd1.ext.YY01*.4`, dia ≤ 30, e **já filtra** TEST, X, Salesperson, split e ano (L415–422) |
| 2 | Versiona por TransactionNumber (`keep_last_version`) | Junta custos; versiona por OriginalTktId (L455–460) |
| 3 | Remove cancelamentos (`remove_cancels`) | (cancelamento já saiu no passo 1) |
| 4 | Valida o split e aplica por janela de data (`merge_split_and_compute`) | LEFT JOIN do split por RR Team, sem data (L578–585) |
| 5 | Monta as 23 colunas; exclui o que não é USD | — |
| 6 | Repo com split; ajustes manuais | Repo sem RR Team (L557); sem ajustes |
| 7 | Regra GNCL/MULT/GNPL → Trade Date dos modificados → exclui 235/TEST → GLCS | — |
| 8 | Grava com 2 casas | `STORE` da tabela de trabalho (L638) |

## 3. Onde estava o problema

Cada item tem a mesma etiqueta `[FIX-nn]` dentro da v11, na aba em que a correção acontece.

| FIX | QVS da analista | Castine.py | Efeito | Certeza |
|---|---|---|---|---|
| 01 | `EXIT SCRIPT` na L151, depois da aba de comparação | — | O reload para ali; as abas de carga não rodam | Certo |
| 02 | L320, L339: prefixo `f392fd1`, versão `.4`, janeiro, dia ≤ 30 | `discover_files` L1957, `select_latest_xml_versions` L1934 | Arquivo reenviado com versão maior não é lido | Certo na regra; o efeito depende de existir versão ≠ 4 |
| 03 | L415–422: filtros na leitura. O filtro de ano + `Sales_Mapping.xlsx` (L420–422) **não existe no Python** | `parse_tradefeed_to_row` L1087 lê tudo | Linhas a mais ou a menos | Certo |
| 04 | L455–460: versão por **OriginalTktId** + MAX(TradeDate) | `keep_last_version` L1199: por **TransactionNumber**, ordem arquivo + AsOf | Ticket repetido em dois arquivos fica duplicado; ticket e correção viram um só; tickets sem OriginalTktId caem num grupo único | Certo na regra; o tamanho depende dos dados |
| 05 | L416: tira o `X` **antes** de versionar | `remove_cancels` L1274, chamado **depois** (L3517) | Trade cancelado continua pago pela versão anterior | Certo |
| 06 | L470–515: Gross = soma de **todos** os TransactionCost em USD, por `Type` | `find_primary_cost_tradefeed` L1010 + `find_add_on_tradefeed` L1037: **um** custo primário + AddOn (`Code` R antes do Cost) | Valor de Gross Comms e de Production | Certo na regra; o efeito depende de haver mais de um custo por trade |
| 07 | L298–311: split carregado sem validação | `load_split_matrix_castine` L1290 | Versão com soma ≠ 100% ou janela sobreposta é paga | Certo |
| 08 | L578–585: join por RR Team cru, **sem janela de datas** | `merge_split_and_compute` L1599 | Time com 2 janelas duplica todos os trades | Certo na regra; o efeito depende de haver time com 2 janelas |
| 09 | L603–604: `Gross * Split` sem arredondar | L1679–1690: round 10 e round 2, half-to-even | Centavos | Certo |
| 10 | L485, L502: filtra a moeda da **linha de custo** | `exclude_xml_nonusd_from_output` L1781: exclui o **trade** pela moeda do papel | Trades não-USD a mais | Certo |
| 11 | L384: Trade Date da versão que sobrou | L1716 (versão original) e `force_modified…` L1878 (modificado = As of) | Muda a chave do comparativo | Certo |
| 12 | sem as regras finais | `exclude_legacy_roll_shortdesc_records` L1813, `exclude_rrteam_235_and_client_test` L2646 | Linhas a mais | Certo |
| 13 | L557: RR Team do Repo comentado | `build_repo_official_output` L2178 | Repo sem Salesperson e sem Production | Certo |
| 14 | não carrega ajustes | `prepare_adjustments_output` L2601 | Linhas a menos | Certo |
| 15 | L237–281: mappings do Tiara montados e **nunca aplicados** (aba 09 vazia) | `populate_glcs_code` L3098 | GLCS CODE vazio | Certo |
| 16 | L597–628: sem Sec Type, com colunas técnicas | `OFFICIAL_OUTPUT_COLUMNS` L190, `%.2f` | Layout do arquivo | Certo |
| 17 | L387, L420: `NUM()`/`YEAR()` sobre texto ISO com `T` | `pd.to_datetime` / `dateutil` | Funciona hoje por interpretação automática; na v11 ficou explícito | Baixo risco |
| 18 | L148: CSV do Python lido como Latin-1 | `to_csv(encoding="utf-8")` L3826 | Nome com acento nunca casa no comparativo | Certo |

**Observação sobre o FIX-03.** A regra de ano da analista e a regra GNCL/MULT/GNPL do Python parecem tratar o mesmo assunto (trades de ano anterior), mas são diferentes:
- A da analista usa o `TraderAccountNumber` e uma lista no Excel.
- A do Python usa o `ShortDesc` e três códigos fixos.

Na v11 vale a do Python. A da analista ficou atrás de um switch desligado.

## 4. O que eu corrigi da minha análise anterior

| O que eu tinha dito | O que é |
|---|---|
| Os dois splits eram arquivos diferentes | São o mesmo arquivo com nomes diferentes (confirmado por você). Não é causa de diferença |
| `MasterAccountName` nulo faria `NULL <> 'TEST'` descartar a linha | No Qlik, `A <> NULL` é verdadeiro, então a linha fica. Retirado |
| `NOCONCATENATE` antes do rótulo (L336, L470, L597) seria erro | É uma forma aceita, e o script dela roda hoje. Retirado |
| `FROM $(var)` sem colchetes (L231, L271) travaria o script | O script roda hoje, então o Qlik aceita. Fica só como recomendação |
| O v10 estava pronto para rodar | Não estava. Ver a seção 5 |

## 5. v10 rev 2 — o que precisava mudar para a saída correta

O QVS da analista mostrou como é o ambiente real. O v10 tinha sido testado só com dados sintéticos e falharia nestes pontos:

| # | Problema no v10 | Correção |
|---|---|---|
| 1 | Conexões fictícias (`lib://Bloomberg_XML/` …) | Conexões reais (`lib://Fldr_SDrive/...`) e `Must_Include` do `Config_QS.txt` |
| 2 | Aba do split: a lista de candidatas não tinha `Split_Matrix`. O split não seria encontrado e o **payout sairia vazio** | `Split_Matrix` em primeiro; arquivo `RR Teams Split Matrix.xlsx` |
| 3 | Datas `2026-01-15T10:22:00` não eram lidas: **datas em branco** no export | Feito na rodada anterior; agora coberto por 9 casos novos no teste |
| 4 | Repo, Tiara e ajustes lidos sempre como UTF-8. A analista lê como Latin-1; o Python tenta UTF-8 e cai para cp1252 | `DetectCodepage`: lê como UTF-8 e, se aparecer caractere inválido, relê como cp1252 |
| 5 | `<TradeFeed id="...">` (tag com atributo) não seria reconhecida | A tag é normalizada antes da leitura, com TRACE da quantidade |
| 6 | Gravava `PPT_DailyExportOfPayout_…` com o mesmo nome do Python | Todos os arquivos saem com prefixo `QLIK_V10_`, só na pasta UAT |
| 7 | Não tinha comparação com o Python | Aba 13, igual à da v11 |

Nenhuma regra de negócio do v10 mudou.

## 6. v11 rev 2 — o QVS da analista atualizado

- **Base:** o script dela (SETs, `Config_QS.txt`, conexões, XmlSimple, comparação).
- **Regras:** as do Python (abas 04–12, as mesmas do v10).
- **Onde estava o problema:** bloco `[FIX-nn]` no início de cada aba, com `WAS` (linha dela), `PROBLEM` e `NOW` (função do Python). O índice dos 18 fica no cabeçalho.
- **Efeito de cada correção nos dados:** a aba `11b_Fix_Log` escreve `TRACE [FIX-nn] métrica = valor` e grava a tabela `FIX_LOG`. Exemplos:
  - quantos trades cancelados a regra antiga manteria;
  - quantas linhas a regra antiga de versão deixaria;
  - quantos trades têm Gross diferente da regra antiga;
  - quantos times têm duas janelas no split.
- **Comparação em 3 lados (aba 13):** Novo × Python × Atual (o export de hoje, `QLIK_PPT_DailyExportOfPayout_<data>.csv`).
  - A coluna `Status New vs Python` tem que dar `MATCH` em todas as chaves.
  - A coluna `Status Current vs Python` mostra onde a saída atual erra.
- **Saída:** prefixo `QLIK_V11_`, para não apagar o export atual antes de validar.

## 7. O que foi verificado e o que falta

| Verificação | Resultado |
|---|---|
| Teste diferencial das fórmulas (Qlik transcrito × funções reais do Python), com 9 casos novos de data ISO | 1067 comparações, 0 divergências |
| Simulação da leitura XmlSimple da v11 nas 34 trades das fixtures × `parse_tradefeed_to_row` | 0 diferenças |
| Checagem de estrutura do v10 e da v11 | Só os 3 abortos propositais |
| **Reload no Qlik** | **Não feito.** Nenhum dos dois scripts rodou em engine |

Pontos que só o reload com dado real confirma:
1. O layout que o XmlSimple devolve para `ExtendedFields/Field` e para arquivo em que nenhum trade tem mais de um TransactionCost. Se o layout for outro, a v11 avisa no log.
2. Se o Qlik marca UTF-8 inválido com `U+FFFD`. A detecção de encoding depende disso.
3. Os números do `FIX_LOG`.

**Roteiro:** rodar a v11 para a data que já tem export do Python → abrir `COMPARE_SUMMARY` → para cada chave que não der `MATCH`, o `FIX_LOG` e os arquivos de alerta mostram em qual regra olhar.

## 8. Dependências

| Item | Onde |
|---|---|
| `Config_QS.txt` (`SDrive`, `SDrive_SalesControlData`, `vLastWorkDate_Year`, `vLastWorkDate_PriorYear`) | `lib://Fldr_QlikShare/SCRIPT/` |
| Conexões | `Fldr_SDrive`, `Fldr_QlikShare`; `QlikView SDrive` só se o filtro da analista for ligado |
| XML Bloomberg | `Fldr_SDrive/Trading/bloomberg/ftp/*.ext.26*` |
| Split | `$(SDrive_SalesControlData)/RR Teams Split Matrix.xlsx`, aba `Split_Matrix` |
| Repo | `Fldr_SDrive/Operations/BroadridgeData/Reports/<data>/` |
| Tiara | `Fldr_SDrive/Qlikview/Sales/Data/Tiara Accounts/` |
| Ajustes | `Fldr_SDrive/Qlikview/Sales/Data/adjustments DailyExportOfPayout_<data>.*` |
| Export do Python (para comparar) | `…/sales/data/daily files/` ou `…/Sales/Data/castine/` |
| Saída (só UAT) | `$(SDrive)/UAT/Qlikview/Sales/Data/castine/QLIK_V11_*` e `QLIK_V10_*` |
