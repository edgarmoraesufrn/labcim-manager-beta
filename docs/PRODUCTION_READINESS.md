# LabCim Manager — prontidão para produção UFRN (M0 + fundações M1A/M1B)

Data do levantamento: 2026-08-11

Escopo: auditoria estática e validação local não destrutiva

Decisão atual: **NO-GO para produção**

Esta decisão não significa que os fluxos funcionais do LabCim Manager devam ser refeitos. Ela significa que o estado atual ainda não oferece uma migração controlada, reproduzível, segura e testada para a infraestrutura institucional da UFRN.

## Atualização M1B — 2026-08-12

M1B removeu os dois blockers de ciclo de schema identificados em M1A:

- versões 1 e 2 ordenadas, com nome/checksum e ledger `labcim_schema_migrations`;
- comandos administrativos independentes do Streamlit para `status`, `verify`, `initialize`, `upgrade`, adoção de banco existente e seeds opcionais;
- validação estrutural antes de adotar schema sem ledger;
- transação e exclusão mútua por `BEGIN IMMEDIATE` no SQLite e advisory transaction lock no PostgreSQL;
- startup web somente abre um banco já existente e compatível; não executa DDL, reparo, `UPDATE`, workbook ou POP seed;
- testes efêmeros comprovam banco SQLite novo, snapshot legado preservado, recusa de versões atrasada/futura, ausência de seed automático e falha/retry;
- tradução DDL e locking PostgreSQL foram testados deterministicamente, mas não havia instância efêmera PostgreSQL disponível.

O `CODE BLOCKER` de repositório conhecido que permanece no preflight é o uploader genérico de equipamento sem allowlist. PostgreSQL UFRN, validação/adoção/migration do schema real, restore, Nginx/systemd e browser `/manager/` continuam `DEPLOYMENT PENDING`. Autenticação pública e demais itens de segurança continuam NO-GO. Detalhes operacionais: `DATABASE_SCHEMA_LIFECYCLE.md`.

## Atualização M1A — 2026-08-12

O snapshot histórico abaixo registra o que o M0 encontrou em `1ffe702`. A fundação M1A, iniciada em `a5d1b5a`, alterou as seguintes conclusões de código sem executar deploy:

- runtime declarado como Python 3.12.13 e dependências diretas/transitivas fixadas com hashes;
- configuração explícita por `APP_ENV`, `APP_BASE_URL`, `STORAGE_BACKEND` e `LOCAL_STORAGE_ROOT`;
- banco e storage desacoplados: SQLite + local, PostgreSQL + local e PostgreSQL + R2 são combinações aceitas;
- caminhos de dados/assets ancorados na raiz do projeto em vez do CWD;
- `baseUrlPath=manager`, manifesto/ícones sob `/manager/` e QR sem domínio histórico;
- URLs públicas de produção validadas como HTTPS e exatamente `/manager/`;
- detalhes do Streamlit ocultos no navegador e helper de erro com referência opaca aplicado aos fluxos tocados;
- testes unitários adicionados para configuração, storage, URLs/PWA/QR, caminhos e erros;
- preflight agora separa `CODE BLOCKER`, `ENVIRONMENT REQUIRED`, `DEPLOYMENT PENDING`, `WARNING` e `PASS`.

As resoluções de M0-B03 e da parte controlada pela aplicação em M0-B04/M0-B07 são estruturais, mas dependem de staging. M0-B06 foi apenas parcialmente mitigado: o uploader genérico de equipamento ainda exige política/allowlist, e a revisão ampla de HTML permanece pendente.

Os `CODE BLOCKER` que eram intencionalmente remanescentes ao fim de M1A eram:

1. migrações/versionamento de schema ausentes;
2. startup ainda executa DDL, importação e seed;
3. uploader genérico de equipamento sem allowlist explícita.

Autenticação pública continua **NO-GO** até o sprint dedicado. Nginx, systemd, PostgreSQL UFRN, proxy/browser em `/manager/` e restore continuam `DEPLOYMENT PENDING`, não falhas falsamente atribuídas ao repositório.

## 1. Snapshot auditado

| Item | Estado encontrado |
|---|---|
| Repositório | `labcim-manager-beta` |
| Branch | `main` |
| Commit inicial do M0 | `1ffe702` |
| Sincronia local | `main...origin/main`, sem divergência registrada no checkout local |
| Entrada da aplicação | `app.py` |
| Framework | Streamlit |
| Gerenciador de dependências | `pip` + `requirements.txt` |
| Python declarado | Não declarado; não há `.python-version`, `runtime.txt` ou metadado de pacote |
| Streamlit declarado | `streamlit>=1.36`, sem versão máxima ou lock |
| Banco local | SQLite em `data/labcim_manager.db` quando `DATABASE_URL` não existe |
| Banco configurável | PostgreSQL via `DATABASE_URL` e `psycopg` |
| Armazenamento local | `data/uploads`, relativo ao diretório de trabalho |
| Armazenamento remoto | Cloudflare R2 via API compatível com S3 |
| Autenticação | código numérico de uso único enviado por SMTP, validade de 10 minutos |
| Testes automatizados | não encontrados |
| Migrações versionadas | não encontradas |
| Empacotamento/deploy | não há unidade systemd, configuração Nginx, container ou pacote Python |

O Android companion não está neste repositório e não foi considerado.

## 2. Arquitetura reconstruída

O sistema é um monólito Streamlit. `app.py` contém UI, autorização por perfil, autenticação, relatórios, exportações, QR Codes, notificações e orquestração de persistência. `labcim_manager/db.py` contém o adaptador SQLite/PostgreSQL, o schema embutido, alterações incrementais de schema e operações de domínio. `labcim_manager/storage.py` contém os backends local e R2.

Fluxo atual:

```text
Navegador
  -> Streamlit (app.py)
      -> conexão por sessão/cache
          -> PostgreSQL, se DATABASE_URL existir
          -> SQLite, caso contrário
      -> anexos
          -> R2, se as quatro variáveis R2 existirem
          -> data/uploads, apenas quando não há DATABASE_URL
      -> SMTP síncrono para códigos de acesso e notificações
```

No snapshot M0, no primeiro uso de uma combinação banco/configuração, `get_conn()` chamava `ensure_database_initialized()`, que:

1. executa `init_db()`;
2. cria tabelas e índices ausentes;
3. adiciona colunas ausentes;
4. normaliza dados com instruções `UPDATE`;
5. importa `data/LabCim_Base.xlsx` se todas as tabelas operacionais estiverem vazias;
6. associa POPs empacotados no repositório.

Esse era o comportamento histórico auditado. Em M1B, `ensure_database_compatible()` passou a abrir apenas banco existente e executar verificação somente leitura; incompatibilidade interrompe o app sem reparar ou semear.

## 3. Estado por área A–O

| Área | Estado | Evidência resumida |
|---|---|---|
| A. Arquitetura | IMPORTANTE | Monólito funcional, mas com UI, autenticação, acesso a dados e operações administrativas concentrados em `app.py`. |
| B. Linux | IMPORTANTE | Código Python é portável, mas todos os caminhos mutáveis são relativos ao CWD e o cabeçalho de `app.py` ainda documenta comandos Windows. |
| C. PostgreSQL | PARCIAL | `psycopg`, placeholders convertidos e `RETURNING id` existem; não há matriz de testes PostgreSQL nem pool de conexões. |
| D. Migração de banco | BLOCKER | Não há migrações versionadas, schema version, exportador/importador SQLite→PostgreSQL nem reconciliação automatizada. |
| E. Arquivos/anexos | BLOCKER | PostgreSQL sem R2 bloqueia uploads; o backend local não pode ser selecionado explicitamente em produção. |
| F. `/manager/` | BLOCKER | `server.baseUrlPath` não está configurado; manifesto PWA usa `start_url` e `scope` em `/`; QR padrão aponta ao Streamlit Cloud. |
| G. Autenticação | BLOCKER | OTP funciona e é fail-closed sem SMTP, mas não há rate limit de solicitação e e-mails ativos duplicados são permitidos. |
| H. Upload/download | BLOCKER | Upload genérico de equipamento não possui allowlist; limite padrão pode chegar a 200 MB; falta validação de conteúdo e teste no subpath. |
| I. QR links | BLOCKER | URL é digitada manualmente e o valor padrão é o domínio antigo; não existe URL pública externa configurável. |
| J. Segurança | BLOCKER | Erros completos do Streamlit ficam habilitados por padrão; há HTML inseguro com valores do banco e endurecimento de upload pendente. |
| K. Ambiente/secrets | IMPORTANTE | Nenhum segredo real de alta confiança foi localizado nos arquivos versionados; configuração aceita env e Streamlit secrets, sem contrato único. |
| L. Logging | IMPORTANTE | Há `notification_log`, mas não há logging estruturado da aplicação, política de retenção ou trilha de eventos de segurança. |
| M. Backup | BLOCKER | O runbook existente descreve Neon/R2; não há rotina nem teste de restore para PostgreSQL/arquivos na VM. |
| N. systemd | BLOCKER | Não há unidade, usuário de serviço, `WorkingDirectory`, política de restart ou diretórios persistentes definidos. |
| O. Nginx | BLOCKER | Não há configuração de proxy, WebSocket, headers encaminhados, timeout, limite de corpo ou TLS para `/manager/`. |

## 4. BLOCKERS

### M0-B01 — inicialização do app altera schema e dados — **resolvido no código em M1B**

O texto abaixo descreve o achado M0: `ensure_database_initialized()` chamava `init_db()`, importação inicial e seed de POPs durante o startup. M1B removeu esse caminho e moveu DDL/seed para comandos administrativos explícitos.

Critério atendido localmente: migrations versionadas executadas por CLI; processo web verifica versão/estrutura e falha fechado. A aplicação no ambiente UFRN ainda depende de ensaio de staging.

### M0-B02 — origem e procedimento de migração de dados não estão definidos

O repositório suporta SQLite e PostgreSQL, mas não contém o banco operacional. A documentação anterior declara Neon/PostgreSQL e R2, porém não comprova qual ambiente contém os dados autoritativos. Não existe utilitário de migração, relatório de reconciliação ou ensaio de restore.

Critério: declarar a fonte autoritativa, produzir backup imutável, executar migração ensaiada em staging e aprovar contagens, chaves, relações, saldos, anexos e amostras funcionais conforme `DATABASE_MIGRATION_PLAN.md`.

### M0-B03 — estratégia de armazenamento incompatível com PostgreSQL local

`get_active_storage_backend()` usa R2 quando totalmente configurado. Se `DATABASE_URL` estiver definido e R2 não estiver completo, o upload é recusado. O backend local usa `data/uploads` e não possui variável para raiz externa. Assim, a arquitetura PostgreSQL local + filesystem institucional não é suportada hoje.

Critério: decidir formalmente entre R2 e filesystem institucional; se filesystem for escolhido, implementar backend configurável, fora do release, com permissões, backup e teste de restore. Em ambos os casos, migrar e reconciliar metadados e bytes.

### M0-B04 — `/manager/` não está implementado nem validado de ponta a ponta

`.streamlit/config.toml` não define `server.baseUrlPath`. `static/manifest.json` aponta `start_url` e `scope` para `/`, o que abre o site Astro em vez do Manager quando instalado como PWA. A tela de QR usa `https://labcim-manager.streamlit.app` como padrão. Não há teste de WebSocket, assets, login, uploads, downloads, links R2, query params ou health check em `/manager/`.

Critério: configurar `manager`, corrigir manifesto e URL pública, adicionar Nginx que preserve o prefixo e WebSockets e executar a matriz manual da seção 7.

### M0-B05 — autenticação pública precisa de controles contra abuso e ambiguidade

Pontos positivos: código aleatório de seis dígitos, hash SHA-256 no banco, uso único, expiração e bloqueio após tentativas; falha SMTP invalida o código, salvo debug explicitamente habilitado.

Pendências bloqueadoras:

- solicitação de códigos sem limite por IP, e-mail ou janela de tempo;
- resposta diferente para e-mail inexistente, permitindo enumeração;
- coluna `users.email` aceita nulo e duplicatas; `LIMIT 1` torna a identidade ambígua;
- nenhuma política de limpeza/retention para `access_codes`;
- nenhuma auditoria de IP/user-agent e nenhum bloqueio global contra automação;
- `LABCIM_AUTH_DEBUG_CODES=true` expõe o código na tela.

Critério: e-mail ativo normalizado e único, resposta uniforme, rate limiting no proxy e/ou aplicação, política de expiração/limpeza, debug impossível no perfil de produção e teste de login atrás do proxy.

### M0-B06 — upload e divulgação de erros não estão endurecidos

O uploader de documentos de equipamento não restringe tipos. Os demais usam extensões, sem magic-byte/assinatura, antivírus ou limite por categoria. O padrão atual do Streamlit permite 200 MB. Valores vindos do banco são interpolados em alguns blocos `unsafe_allow_html=True`. `client.showErrorDetails` não está definido e o padrão atual do Streamlit é `full`.

Critério: allowlist por categoria, limites menores coerentes em Streamlit/Nginx, nomes e MIME validados no servidor, política de malware, HTML escapado e detalhes de erro ocultos no navegador.

### M0-B07 — runtime institucional ainda não é reproduzível nem isolado

Não há versão de Python, lock de dependências, unidade systemd ou configuração Nginx. O Streamlit não está explicitamente preso a `127.0.0.1`. Caminhos dependem do CWD.

Critério: runtime testado e fixado, dependências travadas com hashes, usuário não root, diretórios e permissões definidos, Streamlit somente em loopback, systemd e Nginx validados em staging.

### M0-B08 — backup/restore institucional não foi exercitado

Banco e anexos formam um conjunto lógico. Restaurar apenas um lado produz referências quebradas ou objetos órfãos. O runbook atual só cobre Neon/R2.

Critério: política aprovada de RPO/RTO, backups automatizados e criptografados conforme política UFRN, retenção/monitoramento e ao menos um restore completo testado em ambiente isolado.

## 5. IMPORTANTES

- **M0-I01 — constraints insuficientes:** faltam `CHECK`s de status/booleanos/quantidades, unicidade de e-mail e de vários códigos de domínio; relações genéricas de `attachments` não possuem FK para a entidade alvo.
- **M0-I02 — constraints históricas não recompostas:** a migration 2 preserva o comportamento incremental aprovado e adiciona colunas sem reconstruir tabelas; assim, não adiciona FKs/constraints que exigiriam reescrita e validação de dados. Essa harmonização continua fora de M1B.
- **M0-I03 — timestamps ingênuos:** datas e horas são `TEXT`, geradas com `datetime.now()`/`datetime.utcnow()`, sem offset. O timezone do serviço afetará autenticação, reservas e relatórios.
- **M0-I04 — conexões PostgreSQL:** há uma conexão duradoura por sessão Streamlit e conexões adicionais em caches, sem pool ou limites explícitos. Leituras podem manter transações abertas. Há caminhos de erro, como conflito em `create_equipment`, sem `rollback()`.
- **M0-I05 — atomicidade banco/arquivo:** o arquivo é salvo antes do registro em `attachments`; falha de banco deixa objeto órfão. Upload, criação da entidade e atualização do campo legado usam commits separados.
- **M0-I06 — importação administrativa:** `data/_uploaded_base.xlsx` é um nome global sobrescrito antes da confirmação. Duas sessões podem interferir. A importação faz upsert e commit único, mas a UI não garante rollback ao capturar toda exceção.
- **M0-I07 — caminhos relativos (resolvido no código em M1A):** banco/assets são ancorados no projeto e raízes mutáveis podem ser externalizadas; permissões reais continuam pendentes.
- **M0-I08 — logging:** faltam IDs de correlação, eventos de autenticação, latência/erro de storage e política de retenção para `notification_log`, que contém e-mails e conteúdo de mensagens.
- **M0-I09 — SMTP síncrono:** envio acontece no request, com timeout de 20 segundos; notificações para vários destinatários são sequenciais e podem bloquear a sessão.
- **M0-I10 — exclusão e retenção de arquivos:** inativação preserva o byte, o que favorece auditoria, mas não há política de retenção, legal hold, descarte seguro nem coletor de órfãos.
- **M0-I11 — dados de demonstração (startup resolvido em M1B):** `data/LabCim_Base.xlsx` permanece versionado, mas só pode ser importado por comando/UI administrativo explícito; sua classificação e uso em produção ainda exigem decisão formal.
- **M0-I12 — superfícies antigas:** documentação e exemplos ainda promovem Streamlit Cloud/Neon/R2, criando risco operacional durante a migração.

## 6. OPCIONAIS

- Dividir gradualmente `app.py` por módulo de domínio, sem redesenho funcional.
- Adicionar métricas de processo, banco, fila SMTP e storage após estabilizar logs.
- Avaliar pool de conexões somente depois de medir concorrência real.
- Criar verificador de objetos órfãos e relatório de integridade periódico.
- Automatizar testes de navegador para a matriz `/manager/` após o primeiro teste manual aprovado.

## 7. Matriz obrigatória de validação de `/manager/`

Executar em staging com a versão travada do Streamlit:

| Caso | Resultado esperado |
|---|---|
| `GET /manager` | 301/308 para `/manager/` |
| `GET /manager/` | UI carrega sem request em `/_stcore/*` na raiz |
| WebSocket | conexão em `/manager/_stcore/stream`, sem loop 301/404 |
| Health | endpoint da versão travada responde por loopback e via proxy; candidato atual: `/manager/_stcore/health` |
| Assets Streamlit | JS/CSS/imagens retornam 200 sob o prefixo |
| PWA | manifesto, ícones, `start_url` e `scope` ficam em `/manager/` |
| Login | solicitar código, falha uniforme, validar, recarregar e sair |
| Query params | `?view=reserva`, `manutencao`, `pop`, `insumo`, `eq` e `sid` persistem durante o login |
| QR | todo QR novo usa `https://labcim.quimica.ufrn.br/manager/?...` |
| Upload local/R2 | tipos e tamanhos permitidos funcionam; rejeições são seguras |
| Download local | `st.download_button` funciona pelo prefixo e após reload |
| Download R2 | URL assinada usa HTTPS, expira e não torna o bucket público |
| Exportações | CSV, XLSX, PNG e ZIP baixam com nomes corretos |
| Erros | navegador recebe mensagem genérica; detalhe vai somente ao journald |
| Site Astro | `/` e rotas do site continuam independentes do Manager |

O Streamlit documenta `server.baseUrlPath`, CORS/XSRF e configuração por variáveis `STREAMLIT_*`: <https://docs.streamlit.io/develop/api-reference/configuration/config.toml>. O Nginx exige encaminhamento explícito dos headers de upgrade para WebSocket: <https://nginx.org/en/docs/http/websocket.html>.

## 8. Validação executada

| Validação | Resultado |
|---|---|
| `python -m compileall -q app.py labcim_manager scripts` | PASS com Python 3.12.13 |
| Compilação isolada do preflight | PASS |
| Smoke efêmero SQLite | PASS: schema, import da planilha seed, usuário, reserva, insumo/movimento e contagens |
| Smoke efêmero de autenticação | PASS: criação, expiração futura, verificação e uso único do registro OTP |
| Smoke efêmero de storage local | PASS: escrita/leitura em diretório temporário e bloqueio de traversal |
| Preflight no estado M0 | NO-GO esperado, exit `2`: 36 blockers, 3 warnings, 5 passes |
| Preflight com ambiente fictício completo | Configuração reconhecida; blockers de código/release permaneceram |
| Teste de não divulgação do preflight | PASS: sentinelas de senha/chave não apareceram na saída |
| AST/TOML/JSON/UTF-8/links Markdown | PASS em 26 arquivos de texto auditados |
| `git diff --check` | PASS |
| Testes automatizados existentes | Não encontrados |
| Linter/type checker configurado | Não encontrado |
| Teste PostgreSQL real | Não executado: não havia driver/servidor PostgreSQL no runtime de auditoria |
| Import/startup completo do Streamlit | M1A validou runtime limpo; M1B adicionou regressão estática do caminho de startup e testes de compatibilidade efêmeros |
| Testes M1B | PASS: 39 testes totais; 18 cobrem schema/CLI/startup/seed/locks/falha-retry |
| Streamlit AppTest com schema atual | PASS em cópia efêmera, sem erros; um aviso de depreciação conhecido |
| Paridade estrutural com `init_db()` histórico | PASS: mesmas 16 tabelas, colunas e 23 índices, além do ledger |

Nenhum banco ou diretório de uploads persistente foi criado no repositório. Instalar as dependências abertas mais recentes apenas para obter um startup verde não seria uma homologação reproduzível; isso deve ocorrer depois do lock em M1.

## 9. Resultado do M0

O suporte PostgreSQL é real, mas **parcialmente pronto para produção**: operações principais usam SQL parametrizado, migrations versionadas e locking; ainda falta executar a matriz em PostgreSQL efêmero/staging real e validar conexão/schema UFRN.

O armazenamento é real, mas **não atende ainda à arquitetura local proposta** sem manter R2. A autenticação é funcional para beta controlado, mas **não deve ser exposta publicamente** antes dos controles de abuso e unicidade de identidade.

Próxima sprint recomendada após M1B: hardening dedicado de autenticação/upload, seguido de PostgreSQL staging/restore e validação controlada. Não iniciar deploy de produção enquanto o preflight retornar `CODE BLOCKER` ou os gates institucionais estiverem pendentes.

Nenhuma conexão com a VM UFRN, alteração de infraestrutura, migração de dados ou modificação de banco de produção foi realizada neste M0.
