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

Demais correções e pontos a provar: `CHANGES_v3.md`.
