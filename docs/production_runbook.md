# LabCim Manager — runbook preliminar de produção UFRN

Status: **NO-GO**. Este documento organiza gates futuros; não autoriza deploy, acesso à VM, banco real ou configuração de infraestrutura.

## 1. Identidade da release

Antes de qualquer staging, registrar commit, branch, Python 3.12.13, checksum de `requirements.lock`, operador, janela e plano de rollback. Criar ambiente limpo e instalar com:

```bash
python3.12 -m venv /caminho/isolado/venv
/caminho/isolado/venv/bin/python -m pip install --upgrade pip
/caminho/isolado/venv/bin/python -m pip install -r requirements.txt
```

Não regenerar o lock no servidor.

## 2. Configuração e secrets

Manter secrets fora do release. Conferir sem imprimir valores:

- `APP_ENV=production` e `APP_BASE_URL` HTTPS terminando em `/manager/`;
- `DATABASE_URL` PostgreSQL;
- `STORAGE_BACKEND=local` com raiz absoluta ou `r2` com credenciais completas, além de `LOCAL_WORK_ROOT` absoluto;
- cookie/OTP HMAC secret estável, SMTP, limites OTP/upload validados e `TZ=America/Fortaleza`;
- defaults Streamlit versionados: loopback, porta 8501, `manager`, CORS/XSRF, limite 50 MB e erros ocultos.

O contrato e exemplos fictícios ficam em `PRODUCTION_ENV_TEMPLATE.md`. Permissões pretendidas: environment file `0640`, uploads `0750/0640`, `UMask=0027`; validar no host, nunca aplicar `0777`.

## 3. Preflight

Executar de forma offline antes de qualquer conexão externa:

```bash
python scripts/production_preflight.py --env-file /etc/labcim-manager/manager.env
```

Interpretação:

- `CODE BLOCKER`: requer mudança/revisão de repositório;
- `ENVIRONMENT REQUIRED`: configuração ausente ou ainda não fornecida ao checker;
- `DEPLOYMENT PENDING`: validação que só pode ocorrer no ambiente autorizado;
- `WARNING`: risco/revisão não conclusiva;
- `PASS`: invariante efetivamente observado.

Após M1C, migrations/startup não mutante, autenticação antiabuso e uploads passam nos gates locais. O resultado continua NO-GO pelas validações institucionais reais pendentes; preflight não equivale a deploy, pentest ou ensaio de restore.

## 4. Gates de staging

- branch/commit revisados e árvore limpa;
- migrations versionadas executadas por comando administrativo, não pelo processo web;
- autenticação pública M1C validada novamente com SMTP e proxy reais;
- banco/storage de staging sem dados reais ou com cópia sanitizada formalmente autorizada;
- usuário de serviço sem login/privilégios, Streamlit somente em `127.0.0.1:8501`;
- Nginx `/manager/`, WebSocket, health, limites e TLS revisados;
- storage escolhido com quota, persistência e política institucional;
- SMTP autorizado, segredos OTP e limites validados;
- `python -m labcim_manager.db_migrate diagnose-email-identities` retorna zero antes de habilitar login/seed/import;
- backup completo e restore ensaiado antes do cutover.

## 5. Procedimento administrativo de schema

Nunca anexar migration ou seed ao `ExecStartPre`. Com o serviço parado e backup identificado, carregar o ambiente restrito sem ecoar valores e executar:

```bash
python -m labcim_manager.db_migrate status
python -m labcim_manager.db_migrate verify
```

Para PostgreSQL realmente vazio, `initialize` cria apenas o schema e o ledger; não importa dados. Para schema versionado atrasado, usar `upgrade`. Para restore compatível sem ledger:

```bash
python -m labcim_manager.db_migrate baseline-existing
# revisar contrato e aprovação; o comando acima não grava
python -m labcim_manager.db_migrate baseline-existing --confirm-compatible-schema
python -m labcim_manager.db_migrate upgrade
python -m labcim_manager.db_migrate verify
```

Interromper se o estado for `ahead`, `unknown`, parcial ou se a validação divergir. Não marcar manualmente a versão, não editar o ledger e não tentar DDL improvisado. Os locks recusam um segundo migrador concorrente. Falha transacional faz rollback; preservar o erro no journal, manter o serviço parado, reinspecionar com `status` e só repetir após corrigir a causa.

Seed de workbook/POPs só pode ser executado por decisão explícita em banco adequado; nunca faz parte de initialize, upgrade ou startup. Produção restaurada não deve receber seed.

Rollback de release que alterou schema é restore coordenado do backup compatível de banco e storage. Não há comando de downgrade.

## 6. Smoke funcional obrigatório

Validar health e UI em `/manager/`, assets/PWA sem requests na raiz, WebSocket, login/logout, perfis `member`/`manager`/`admin`, reservas, manutenção, insumos/lotes, relatórios, QR, upload/download e persistência após restart. Para QR, confirmar destino `https://labcim.quimica.ufrn.br/manager/?...`; para PWA, confirmar que instalação abre o Manager e não o site institucional.

## 7. Falhas e apresentação segura

O usuário deve receber mensagem curta e referência de evento. Usar essa referência no journal; não copiar traceback, connection string, OTP, segredo ou URL assinada para navegador/ticket. `APP_LOG_LEVEL=INFO` é o default. Um operador pode habilitar diagnóstico detalhado somente em desenvolvimento isolado.

Para autenticação e uploads, seguir `AUTHENTICATION_SECURITY.md` e `UPLOAD_SECURITY.md`. Confirmar que Nginx sobrescreve `X-Forwarded-For`/`X-Real-IP`, que os limites do Nginx/Streamlit são coerentes com `LABCIM_UPLOAD_MAX_BYTES` e que banco e anexos são restauráveis como conjunto.

## 8. Backup, restore e rollback

Banco e anexos são um conjunto lógico. Registrar RPO/RTO, destino fora da VM, criptografia, retenção, monitoramento e sequência. Restaurar em ambiente isolado, reconciliar contagens/hashes e executar smoke antes de aprovar. Manter release/origem anterior imutável durante a janela; não apagar órfãos nem reverter schema por DDL improvisado.

## 9. Registro de liberação futura

- data/janela:
- commit e checksum do lock:
- responsáveis e aprovações:
- backend de storage:
- preflight anexado:
- migrations e backup registrados:
- restore aprovado:
- testes por perfil e `/manager/`:
- decisão GO/NO-GO:
- rollback e observações:

Enquanto algum `CODE BLOCKER` ou gate institucional permanecer, a decisão é NO-GO.
