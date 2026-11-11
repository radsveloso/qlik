# Validação estática do v10 rev 2 e da v11 rev 2 (2026-11-10)

Projeto **Qlik Sense do Santander**. A validação foi feita só localmente, sem engine, sem Qlik Cloud e sem ambiente de outro cliente.
Ela não substitui o reload: quem dá a palavra final é o Qlik Sense do Santander.

## Resultado

| Verificação | v10 rev 2 | v11 rev 2 |
|---|---|---|
| Validador estático (`scripts/qvs_validate.py`) | 0 erros, 0 avisos (1.298 instruções) | 0 erros, 0 avisos (1.546 instruções) |
| Checagem de campos | 98 de 170 níveis de LOAD conferidos | 107 de 187 conferidos |
| Fórmulas transcritas × funções reais do `Castine.py` (`differential_test.py`) | 1067 comparações, 0 divergências | mesmas fórmulas |
| Leitura XmlSimple simulada × `parse_tradefeed_to_row` | não se aplica (leitura textual) | 67 trades, 0 diferenças |

## O que o validador confere

| Código | Erro que ele acha |
|---|---|
| E-CTRL | IF/FOR/DO/SUB sem fechamento; IF sem THEN na mesma linha |
| E-PAREN, E-QUOTE | parêntese, aspas ou colchete sem fechar |
| E-SEMI, E-TERM | `;` faltando entre instruções ou no fim |
| E-COMMA | vírgula sobrando antes de FROM/RESIDENT, ou faltando entre campos |
| E-KEYWORD | instrução que não começa com palavra conhecida; palavra errada na especificação do arquivo |
| E-FUNC, E-ARITY | função inexistente ou com número errado de argumentos (catálogo de 326 funções + as de script) |
| E-PARAM | `$(fVar(a, b))` com vírgula a mais (o Qlik separa os parâmetros em toda vírgula) |
| E-VAR | `$(variável)` que nunca recebe valor |
| E-CALL | CALL de SUB inexistente ou com número errado de argumentos |
| E-TABLE | RESIDENT / JOIN / DROP / STORE / Peek de tabela que nunca é criada |
| E-FIELD | campo usado num LOAD que a tabela de origem não tem |
| W-LEAK | tabela temporária criada e nunca apagada |
| W-STRPAR | parênteses desbalanceados em expressão montada como texto |

## Quanto vale o "0 erros"

O próprio validador foi testado de dois jeitos:

- **25 erros plantados, um de cada tipo** (`qvs_validate_selftest.py`): 25 detectados.
- **500 erros de digitação aleatórios** em identificadores (`qvs_validate_fuzz.py`): 72% detectados na v11 e 71% no v10.

Os erros aleatórios que ele não vê caem em três grupos:

1. **Nome novo de campo (alias) digitado diferente.** Para o Qlik isso também não é erro de sintaxe: cria um campo com outro nome. É erro de lógica, que só a comparação com o Python pega.
2. **Campo lido de tabela montada com texto dinâmico.** São os 72 (v10) e 80 (v11) níveis de LOAD que a checagem de campos não consegue conferir: split com colunas detectadas, Repo, Tiara e a saída das SUBs.
3. **Nome dentro de `[colchetes]`** nessas mesmas tabelas.

## O que só o reload no Qlik Sense confirma

1. O layout que o XmlSimple devolve para `ExtendedFields/Field` e para arquivo com um único TransactionCost por trade (v11). O script avisa no log quando o layout é outro.
2. Se o Qlik marca UTF-8 inválido com `U+FFFD` (detecção de encoding de Repo, Tiara e ajustes).
3. Os campos das tabelas dinâmicas do grupo 2 acima.
4. O `Config_QS.txt` (variáveis `SDrive` e `SDrive_SalesControlData`) e as conexões `lib://Fldr_SDrive`.
5. O resultado final: a aba 13 tem que terminar com `[COMPARE] RESULT: this reload is IDENTICAL to the Python export on every key`.

## Como repetir

```
python scripts/qvs_validate.py qvs/QLIK_PPT_SalesCredit_DailyExport_v11.qvs --catalog scripts/FUNCTION_CATALOG.md
```
```
python scripts/qvs_validate_selftest.py qvs/QLIK_PPT_SalesCredit_DailyExport_v11.qvs --catalog scripts/FUNCTION_CATALOG.md
```
```
python scripts/qvs_validate_fuzz.py qvs/QLIK_PPT_SalesCredit_DailyExport_v11.qvs --catalog scripts/FUNCTION_CATALOG.md n=500
```

## Mudanças nos scripts durante a validação

- A SUB `LoadCompareSide` (aba 13) saiu de dentro do `IF` e foi para o nível principal da aba, nos dois scripts.
- A v11 ganhou o comentário `// @fields _PARSED: ...`, que declara o contrato fixo dessa tabela e permite conferir os campos do LOAD seguinte.
- O validador não apontou nenhum erro de sintaxe nem de referência a corrigir.
