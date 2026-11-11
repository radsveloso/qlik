# Bloomberg_Python_Parity_v10.qvs

Feita a partir do `Bloomberg_Python_Parity_v3.qvs`. O número v10 identifica a linha desta sessão e não indica dez versões anteriores. Os arquivos da outra sessão (`_v2`, `_v2_EN`, `CHANGES_v2.md`) não foram alterados.

**Status: nunca executada em um Qlik.**

## Mudanças sobre o v3

| Problema | Correção |
|---|---|
| Coluna ausente no repo ou nos ajustes colocava `''` dentro do acumulador do `LOAD`, e a expansão seguinte podia quebrar o script | Expressão sem apóstrofo: `Repeat(Chr(32),0)` |
| Não havia como saber a versão pelo log | `TRACE [CASTINE] Script Bloomberg_Python_Parity v10` no início |
| Leitura dos XML presa em `f392fd1.ext.26*.4`: só o prefixo `f392fd1` e só a versão `.4` (correção do Rafael, 2026-11-10) | `vXmlPattern = '*.ext.26*'`. O último segmento é a versão; para cada arquivo (mesmo caminho sem a versão) fica só a maior, comparada como número (`.10` vence `.9`). Nome sem versão numérica (`.tmp`, `.bak`, sem versão) é ignorado com `TRACE [WARN]`. `ExtractFileToken` aceita qualquer versão. Mesma mudança no `Castine.py` (`split_xml_version`, `select_latest_xml_versions`) |
| Comentários e mensagens de log em pt-BR | Todos os comentários (incluindo nomes das abas `///$tab`) e as 18 mensagens de `TRACE` em pt-BR passaram para inglês. Código sem alteração, conferido por comparação sem os comentários. O valor `(VAZIO)` continua igual, porque é dado do script |
| Datas no formato ISO com `T` (`2026-01-15T10:22:00`), que é o formato do feed real visto no QVS da analista, não eram reconhecidas por `ParseDateColumn` nem por `fPdDate`. As datas de saída ficavam em branco e a ordem das versões perdia o AsOf. As fixtures (`YYYYMMDD`) não pegavam o caso. | `fPdDate` e o fallback de `ParseDateColumn` passaram a ler `YYYY-MM-DDThh:mm:ss`, ignorando fração e fuso (`Left(...,19)`), como faz o `dateutil` do Python. Ficou igual à v11 |

## rev 2 (2026-11-10) — ambiente real

O QVS da analista (`QLIK_PPT_SalesCredit_DailyExport 2026Jan.qvs`) mostrou como é o ambiente do Santander. O v10 só tinha rodado em testes com dados sintéticos e falharia nos pontos abaixo. Nenhuma regra de negócio mudou.

| Problema | Correção |
|---|---|
| Conexões fictícias (`lib://Bloomberg_XML/`, `lib://Split_Matrix/` …) | Conexões reais: `lib://Fldr_SDrive/...` para XML, Repo, Tiara e ajustes; `$(SDrive_SalesControlData)/` para o split; `$(SDrive)/UAT/Qlikview/Sales/Data/castine/` para a saída. Entrou o `Must_Include` do `Config_QS.txt`, com TRACE de erro se as variáveis não vierem |
| A aba real do split (`Split_Matrix`) não estava em `vSplitSheetCandidates`: o split não seria achado e o payout sairia vazio | `Split_Matrix` é a primeira candidata; `vSplitMatrixFile = 'RR Teams Split Matrix.xlsx'` (mesmo conteúdo do arquivo do Python, confirmado pelo Rafael) |
| Repo, Tiara, ajustes e XML lidos sempre como UTF-8. O Python tenta UTF-8 e cai para cp1252; a analista lê Repo e Tiara como Latin-1 | `SUB DetectCodepage`: lê como 65001 e, se aparecer `U+FFFD`, relê como 1252. No XML a releitura é por arquivo |
| Tag `<TradeFeed ...>` com atributo não casava com `vXmlFeedOpen` | A tag é reescrita como `<TradeFeed><!-- ...` antes da extração, com TRACE da quantidade |
| O export saía como `PPT_DailyExportOfPayout_<data>.csv`, mesmo nome do Python | Todos os `STORE` usam o prefixo `vOutTag = 'QLIK_V10_'`, sempre na pasta UAT |
| Não havia comparação com o Python dentro do script | Aba `13_Python_Comparison`: Novo × Python × Atual (export de hoje da analista), com `COMPARE_BY_KEY` e `COMPARE_SUMMARY` |
| O teste diferencial não cobria data ISO com `T` | `scripts/differential_test.py` ganhou o ramo ISO e 9 casos; resultado: 1067 comparações, 0 divergências |

Para rodar com as fixtures sintéticas do kit, aponte as seis variáveis `vLib*` do bloco de conexões para as pastas do kit.

Demais correções e pontos a provar: `CHANGES_v3.md`.
