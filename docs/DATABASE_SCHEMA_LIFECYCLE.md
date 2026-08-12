# LabCim Manager — ciclo de vida versionado do schema

Status: implementado em M1B para execução local/efêmera; nenhuma base UFRN ou de produção foi acessada.

## Modelo adotado

O repositório usa um migrador pequeno e explícito, sem ORM, em `labcim_manager/schema.py` e `labcim_manager/migrations/`. Alembic foi avaliado e não foi adotado: o acesso a dados já é SQL direto, o schema está centralizado, há somente dois dialetos e a introdução de metadata/engine/ambiente Alembic aumentaria a superfície operacional sem substituir o adaptador existente.

Cada migration tem número, nome e checksum determinísticos. `labcim_schema_migrations` registra as versões aplicadas. O histórico é forward-only e contínuo:

| Versão | Nome | Conteúdo |
|---|---|---|
| 1 | `legacy_core` | dez tabelas do snapshot legado real do repositório |
| 2 | `approved_schema_2026_08` | seis tabelas, 22 colunas e 23 índices do contrato aprovado atual |
| 3 | `auth_abuse_protection` | tabela e três índices de eventos persistentes de throttling OTP, sem alterar usuários/dados operacionais |

A versão esperada desta release é **3**. Ela preserva as 16 tabelas operacionais aprovadas e acrescenta apenas `auth_rate_limit_events`, tabela de segurança não operacional. Os checksums M1B permanecem: v1 `082096411bef0900a165e443b0efe8ffd61c9db4fa1718203d6cce001c447bf2`; v2 `a07a72c9752d99324b0e8fbb07e510342e253b785da85f0fa74e06ae7981b8a0`.

M1B preserva os tipos e constraints históricos que o SQL atual consegue criar/adicionar. Não adiciona constraints de negócio, não converte timestamps, não normaliza status/e-mail, não reescreve FKs e não altera dados operacionais.

## Comportamento anterior, reconstruído antes da mudança

O primeiro `get_conn()` de uma combinação de configuração chamava `ensure_database_initialized()`. Esse caminho abria o banco, executava `init_db()`, importava `data/LabCim_Base.xlsx` quando presente e quando todas as tabelas operacionais estavam vazias, e sempre executava o seed de POPs.

`init_db()` tentava, em todo startup:

- 16 `CREATE TABLE IF NOT EXISTS`;
- 26 comandos `CREATE INDEX IF NOT EXISTS`, correspondentes a 23 índices únicos;
- 45 verificações/possíveis `ALTER TABLE ADD COLUMN`;
- cinco transformações `UPDATE`: ativação de manutenções com valor nulo, preenchimento de tipo de insumo e status de projeto, e conversão de aliases de perfil para `manager`;
- `COMMIT`.

Consequências exatas por cenário:

| Cenário anterior | Efeito no startup |
|---|---|
| SQLite inexistente | criava diretório/arquivo, schema, índices; podia importar workbook; associava POPs |
| PostgreSQL vazio | criava schema/índices; podia importar workbook; associava POPs |
| schema antigo | fazia reparos oportunistas de tabelas, colunas e índices, além dos cinco `UPDATE`s |
| schema atual | ainda executava DDL condicional, introspecções, cinco `UPDATE`s e seed de POPs |
| workbook presente | importava quando o banco operacional estivesse vazio |
| workbook ausente | pulava a planilha, mas ainda criava/reparava schema e aplicava POPs |

## Estados e política de startup

O inspetor classifica o banco como:

- `missing`: nenhuma tabela de aplicação;
- `unversioned`: há schema, mas não há ledger;
- `current`: versão, checksums, tabelas, colunas críticas, tipos críticos e índices correspondem à release;
- `behind`: ledger válido e versão menor que 3;
- `ahead`: versão maior que 3;
- `unknown`: ledger ilegível/descontínuo, checksum divergente ou estrutura incompatível.

O processo web abre SQLite com `mode=rw`, sem criar arquivo, e faz apenas `verify_schema_compatible()`. Somente `current` inicia a aplicação. Qualquer outro estado falha fechado com mensagem administrativa curta; o navegador não recebe URL, credencial, SQL ou detalhe interno. Um SQLite ausente não é criado nem mesmo em development pelo startup normal.

## Interface administrativa

Os comandos usam `DATABASE_URL` quando configurada; na ausência dela, usam `data/labcim_manager.db`. `--sqlite-path` deve preceder o subcomando quando um arquivo efêmero diferente for desejado.

```bash
python -m labcim_manager.db_migrate status
python -m labcim_manager.db_migrate verify
python -m labcim_manager.db_migrate initialize
python -m labcim_manager.db_migrate upgrade
python -m labcim_manager.db_migrate baseline-existing
python -m labcim_manager.db_migrate baseline-existing --confirm-compatible-schema
python -m labcim_manager.db_migrate seed-base --workbook data/LabCim_Base.xlsx
python -m labcim_manager.db_migrate seed-pops
```

`status` informa estado, versão atual, versão esperada e pendências. `verify` é somente leitura. `initialize` exige alvo sem schema. `upgrade` aplica somente versões pendentes e recusa schema sem ledger, adiantado ou desconhecido.

`seed-base` e `seed-pops` são operações separadas e explícitas. A planilha é recusada em banco operacional não vazio, salvo `--allow-nonempty` conscientemente informado pelo operador. Inicialização/migration nunca importam a planilha nem POPs.

Os comandos nunca imprimem `DATABASE_URL` ou seus componentes secretos. Erros inesperados exibem somente a classe da falha.

## Adoção segura de banco existente

`baseline-existing` serve para snapshots existentes sem ledger. A primeira execução, sem confirmação, inspeciona e não escreve. A inspeção exige o contrato completo de versão 1, 2 ou 3: tabelas, colunas esperadas, tipos críticos coerentes com SQLite/PostgreSQL e índices relevantes.

Schema arbitrário ou evolução parcial é recusado com lista limitada de divergências. Após revisão humana, repetir com `--confirm-compatible-schema` grava apenas os registros de versão compatíveis. O comando não cria tabela funcional, não adiciona coluna/índice e não reinterpreta dados. Snapshots completos v1/v2 são adotados na versão correspondente e depois requerem `upgrade`; um snapshot v3 completo é adotado como atual.

Para produção, executar somente após backup, em janela aprovada e primeiro em staging restaurado. Não usar adoção como forma de ignorar diferenças.

## Transação, concorrência, falha e retry

- SQLite usa `BEGIN IMMEDIATE` com espera de lock zerada; um segundo migrador falha antes de mutar o schema.
- PostgreSQL usa `pg_try_advisory_xact_lock` transacional com identificador fixo do LabCim; conflito é recusado.
- criação do ledger, DDL e registro de versões ocorrem na mesma transação. Em erro, a transação é revertida; uma nova execução reinspeciona o estado e é segura.
- checksum/nome divergente, lacuna no histórico ou artefato estrutural ausente produz `unknown`, não reparo automático.

Não há `downgrade` destrutivo. Rollback operacional de produção é restauração coordenada do backup de banco e storage. DDL que no futuro não for transacional deverá ser isolado e documentado em migration própria antes de ser aceito.

## Procedimentos

### SQLite de desenvolvimento novo

```bash
python -m labcim_manager.db_migrate status
python -m labcim_manager.db_migrate initialize
python -m labcim_manager.db_migrate verify
# opcional e deliberado:
python -m labcim_manager.db_migrate seed-base --workbook data/LabCim_Base.xlsx
python -m streamlit run app.py --server.baseUrlPath=
```

### PostgreSQL de staging novo

Com `DATABASE_URL` fornecida por arquivo/gerenciador restrito, sem ecoá-la:

```bash
python -m labcim_manager.db_migrate status
python -m labcim_manager.db_migrate initialize
python -m labcim_manager.db_migrate verify
```

### PostgreSQL restaurado sem ledger

```bash
python -m labcim_manager.db_migrate baseline-existing
# revisar resultado, backup e aprovação
python -m labcim_manager.db_migrate baseline-existing --confirm-compatible-schema
python -m labcim_manager.db_migrate upgrade
python -m labcim_manager.db_migrate verify
```

## Evidência e limite de M1B

Fixtures SQLite provaram inicialização vazia sem seed, adoção/upgrade do snapshot legado com dados preservados, recusa de versões atrasada/futura, falha/retry e lock concorrente. A tradução PostgreSQL do DDL e o advisory lock têm testes determinísticos. Não havia servidor/CLI PostgreSQL efêmero disponível; portanto, criação e upgrade PostgreSQL reais continuam **DEPLOYMENT PENDING** e devem ser ensaiados em staging antes de produção.
