# LabCim Manager — plano de migração de banco para UFRN

Status: planejamento M0; nenhuma migração executada.

## 1. Estado atual

`labcim_manager/db.py` implementa dois dialetos atrás de `DatabaseConnection`:

- SQLite quando `DATABASE_URL` não está configurada;
- PostgreSQL via `psycopg` quando `DATABASE_URL` existe.

O schema possui 16 tabelas:

```text
equipment
users
projects
project_services
bookings
booking_status_history
maintenance_preventive
maintenance_corrective
maintenance_status_history
supplies
supply_lots
supply_movements
equipment_spare_parts
attachments
access_codes
notification_log
```

Há índices para serviços, reservas, históricos, lotes, movimentos e anexos. Há FKs em parte das relações, mas não existem ações `ON DELETE`, constraints de status/booleanos/quantidades ou unicidade de e-mail. Datas e horas são armazenadas como `TEXT`.

Não há Alembic, tabela de versão, DDL versionado ou ferramenta de migração. `init_db()` é o mecanismo atual de criação/evolução e roda no startup.

## 2. Decisão obrigatória: fonte autoritativa

Antes de escrever qualquer migrador, responder e registrar:

1. O sistema em uso está em Neon/PostgreSQL, SQLite local, ambos ou nenhum?
2. Qual cópia recebeu a última escrita operacional?
3. Existem anexos R2 associados a esse banco?
4. Existe janela possível de read-only/cutoff?
5. Quem aprova contagens e amostras por domínio?

Nunca combinar silenciosamente duas fontes. Se houver divergência, produzir relatório por tabela/chave e uma decisão de merge separada.

## 3. Rota A — PostgreSQL/Neon para PostgreSQL UFRN

Esta é a rota preferida se Neon for a fonte autoritativa:

1. Registrar versões de origem e destino.
2. Criar backup consistente em formato custom do PostgreSQL, sem expor a URL em histórico de shell.
3. Preservar dump bruto, checksum e log fora do repositório.
4. Restaurar primeiro em staging UFRN ou ambiente equivalente.
5. Usar role owner controlado e evitar restaurar privilégios/owners cloud que não existam localmente.
6. Não iniciar o app antes de separar `init_db()` do startup.
7. Comparar schema restaurado com o schema versionado aprovado para a release.
8. Reconciliar dados conforme a seção 7.
9. Executar testes funcionais com storage correspondente.
10. Ensaiar rollback/restore antes do cutover.

Não usar `data/LabCim_Base.xlsx` para “completar” um restore PostgreSQL.

## 4. Rota B — SQLite para PostgreSQL UFRN

Se SQLite for a fonte autoritativa, criar uma ferramenta de migração dedicada e testada. Não apontar o app ao banco vazio esperando que o startup faça a conversão; ele apenas cria/atualiza o banco selecionado e importa três domínios da planilha seed.

Ordem de carga recomendada, preservando IDs:

1. `equipment`, `users`;
2. `projects`;
3. `project_services`;
4. `supplies`;
5. `supply_lots`;
6. `bookings`;
7. `maintenance_preventive`, `maintenance_corrective`;
8. `supply_movements`;
9. `equipment_spare_parts`;
10. históricos;
11. `attachments`;
12. `access_codes` e `notification_log`, conforme política de retenção.

Depois da carga, ajustar as sequences/identities PostgreSQL para `max(id)+1`. Converter e validar explicitamente:

- inteiros booleanos `0/1`;
- floats e saldos;
- strings vazias versus `NULL`;
- UTF-8 e acentuação;
- timestamps ISO sem timezone;
- FKs e IDs órfãos;
- e-mails normalizados/duplicados;
- códigos de status fora das listas atuais.

O migrador deve ter `--dry-run`, transação única ou checkpoints documentados, relatório JSON/CSV sem dados sensíveis e nunca apagar a origem.

## 5. Schema versionado antes da carga

M1 deve introduzir:

- uma tabela de versão ou ferramenta de migração consolidada;
- baseline PostgreSQL derivada e revisada do schema atual;
- migrations forward-only, pequenas e transacionais quando possível;
- comando administrativo explícito;
- aplicação web que somente verifica compatibilidade;
- testes de banco novo, upgrade de snapshot anterior e rollback operacional por restore.

Não transformar automaticamente todas as colunas `TEXT` de data em `timestamptz` na mesma janela do primeiro cutover. Primeiro inventariar valores inválidos e definir semântica de timezone.

## 6. Correções prévias de integridade

Antes de criar constraints novas, auditar e corrigir em staging:

- e-mails ativos duplicados após `lower(trim(email))`;
- usuários ativos sem e-mail que deveriam autenticar;
- `role` fora de `member/manager/admin`;
- FKs órfãs;
- reservas com início maior ou igual ao fim;
- reservas conflitantes por equipamento;
- saldos negativos;
- saldo do insumo versus somatório de movimentos;
- saldo dos lotes versus movimentos por lote;
- serviços ligados a projeto diferente do informado em reserva/movimento;
- anexos com entidade inexistente;
- status inválidos;
- datas/timestamps que não parseiam;
- IDs duplicados ou sequences defasadas.

Constraint nova só deve ser aplicada depois de relatório limpo e aprovação do responsável funcional.

## 7. Reconciliação obrigatória

Gerar antes e depois:

### Contagens

Contagem de todas as 16 tabelas, separando ativos/inativos quando aplicável.

### Chaves

- `min(id)`, `max(id)`, quantidade e duplicatas;
- equipamentos por `equipment_code`;
- usuários por e-mail normalizado;
- projetos/serviços por código;
- lotes por insumo/código;
- attachments por backend/role/entity.

### Relações

- consulta de órfãos para cada FK;
- `attachments.entity_type/entity_id` contra a tabela esperada;
- campos legados `attachment:<id>` contra `attachments.id`;
- associação projeto/serviço;
- associação supply/lot.

### Saldos e domínio

- saldo global de cada insumo;
- saldo de cada lote;
- totais por tipo de movimento;
- reservas por status e período;
- manutenções por tipo/status;
- histórico de status presente para amostras selecionadas.

### Conteúdo

Para tabelas estáveis, calcular digest determinístico por linha após normalização documentada. Para dados sensíveis, guardar apenas os hashes e totais em local restrito.

## 8. Transações e concorrência a testar

- duas reservas simultâneas para o mesmo equipamento/período;
- duas saídas simultâneas no limite do saldo;
- troca concorrente de status;
- falha de insert após upload;
- conflito de `equipment_code` e recuperação da conexão PostgreSQL;
- indisponibilidade temporária do banco e reconexão do Streamlit;
- limites de conexões com várias sessões.

O código usa advisory lock PostgreSQL para reserva e updates condicionais para saldo; esses caminhos ainda precisam de teste real PostgreSQL.

## 9. Cutover proposto

1. Aprovar staging e restore.
2. Anunciar janela e tornar origem somente leitura.
3. Registrar horário de cutoff.
4. Fazer backup final e checksum.
5. Migrar/restaurar no destino.
6. Executar reconciliação automatizada.
7. Migrar/verificar storage com o mesmo snapshot lógico.
8. Executar smoke por perfil.
9. Aprovar abertura do Nginx.
10. Manter origem intacta durante a janela de rollback definida.

## 10. Rollback

Se qualquer gate falhar:

- não abrir o destino para escrita;
- preservar logs e relatórios;
- restaurar o serviço anterior se ele ainda for a origem autoritativa;
- descartar/recriar apenas o **ambiente de staging/destino recém-criado** conforme procedimento aprovado, nunca a origem;
- repetir a migração a partir do backup imutável.

Não executar downgrade destrutivo de schema em produção.

## 11. Gates de aprovação

- [ ] fonte autoritativa declarada;
- [ ] backup final e restore testados;
- [ ] migrations versionadas;
- [ ] app não altera schema/dados no startup;
- [ ] contagens e relações reconciliadas;
- [ ] e-mails ativos únicos;
- [ ] testes concorrentes PostgreSQL aprovados;
- [ ] sequences verificadas;
- [ ] storage reconciliado;
- [ ] rollback ensaiado;
- [ ] aprovação funcional e técnica registrada.
