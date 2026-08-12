# LabCim Manager — contrato de ambiente

Este documento contém apenas nomes, finalidades e valores fictícios. Segredos reais devem permanecer fora do Git, preferencialmente em um `EnvironmentFile` restrito ao serviço.

## Aplicação, banco e arquivos

| Variável | Obrigatoriedade | Finalidade | Exemplo seguro | Ambiente |
|---|---|---|---|---|
| `APP_ENV` | Obrigatória em staging/produção | ativa validações explícitas; valores: `development`, `test`, `staging`, `production` | `production` | todos |
| `APP_BASE_URL` | Obrigatória para QR; obrigatória na produção planejada | URL pública completa do Manager, usada em QR e metadata PWA | `https://manager.example.invalid/manager/` | staging/produção |
| `DATABASE_URL` | Obrigatória em produção | conexão PostgreSQL; sua presença **não** seleciona storage | `postgresql://labcim_app:<DB_PASSWORD>@127.0.0.1:5432/labcim_manager` | staging/produção |
| `STORAGE_BACKEND` | Obrigatória em staging/produção | seleção independente: `local` ou `r2` | `local` | todos; default `local` só em development/test |
| `LOCAL_STORAGE_ROOT` | Obrigatória e absoluta quando `STORAGE_BACKEND=local` em staging/produção | raiz persistente externa ao release | `/var/lib/labcim-manager/uploads` | backend local |
| `LOCAL_WORK_ROOT` | Obrigatória em staging/produção | diretório gravável para importações e temporários controlados | `/var/lib/labcim-manager/work` | staging/produção |
| `APP_LOG_LEVEL` | Opcional | nível do logging Python; default `INFO` | `INFO` | todos |

Em produção, `APP_BASE_URL` deve usar HTTPS, não pode apontar para localhost/IP privado e deve terminar exatamente em `/manager/`. Caminhos locais relativos são aceitos somente em development/test e são resolvidos a partir da raiz do projeto, nunca do CWD do processo.

Não existe variável que autorize migration ou seed no startup. `DATABASE_URL` é lida também pela CLI `python -m labcim_manager.db_migrate`, mas nunca é impressa por ela. Na ausência de `DATABASE_URL`, a CLI usa o SQLite do projeto (`data/labcim_manager.db`) ou um `--sqlite-path` explícito. Em staging/produção, fornecer secrets por ambiente/arquivo restrito, executar `status`/`verify` administrativamente e iniciar o serviço somente com schema compatível.

## R2, somente quando selecionado

| Variável | Obrigatoriedade | Finalidade | Exemplo seguro | Ambiente |
|---|---|---|---|---|
| `R2_ENDPOINT_URL` | Obrigatória para `STORAGE_BACKEND=r2` | endpoint S3 compatível | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` | backend R2 |
| `R2_ACCESS_KEY_ID` | Obrigatória para R2 | identificador de acesso | `<R2_ACCESS_KEY_ID>` | backend R2 |
| `R2_SECRET_ACCESS_KEY` | Obrigatória para R2 | chave secreta | `<R2_SECRET_ACCESS_KEY>` | backend R2 |
| `R2_BUCKET` | Obrigatória para R2 | bucket privado | `labcim-manager-files` | backend R2 |
| `R2_ACCOUNT_ID` | Opcional | identificação operacional da conta | `<R2_ACCOUNT_ID>` | backend R2 |

As variáveis R2 são irrelevantes para `STORAGE_BACKEND=local`. PostgreSQL + local é uma combinação suportada.

## Streamlit e `/manager/`

Valores não secretos já possuem defaults seguros em `.streamlit/config.toml`. O ambiente do servidor pode fixá-los novamente sem alterar o contrato.

| Variável | Obrigatoriedade | Finalidade | Exemplo seguro | Ambiente |
|---|---|---|---|---|
| `STREAMLIT_SERVER_COOKIE_SECRET` | Obrigatória em produção | assinatura estável de cookies | `<RANDOM_HIGH_ENTROPY_SECRET>` | produção |
| `STREAMLIT_SERVER_ADDRESS` | Default versionado | escutar apenas em loopback | `127.0.0.1` | staging/produção |
| `STREAMLIT_SERVER_PORT` | Default versionado | porta do upstream Nginx | `8501` | staging/produção |
| `STREAMLIT_SERVER_BASE_URL_PATH` | Default versionado | publicar sob `/manager/` | `manager` | staging/produção |
| `STREAMLIT_SERVER_HEADLESS` | Default versionado | execução não interativa | `true` | staging/produção |
| `STREAMLIT_SERVER_ENABLE_CORS` | Default versionado | proteção CORS do Streamlit | `true` | todos |
| `STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION` | Default versionado | proteção XSRF | `true` | todos |
| `STREAMLIT_SERVER_MAX_UPLOAD_SIZE` | Default versionado | limite global em MB | `50` | todos |
| `STREAMLIT_SERVER_MAX_MESSAGE_SIZE` | Default versionado | limite WebSocket em MB | `50` | todos |
| `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS` | Default versionado | omitir detalhes internos no browser | `none` | staging/produção |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | Default versionado | desabilitar telemetria | `false` | todos |

Desenvolvedores podem sobrescrever apenas `baseUrlPath` e detalhes de erro em uma invocação local, conforme `LOCAL_STAGING_GUIDE.md`.

## SMTP e autenticação existente

| Variável | Obrigatoriedade | Finalidade | Exemplo seguro | Ambiente |
|---|---|---|---|---|
| `LABCIM_SMTP_HOST` | Obrigatória para login por e-mail | host SMTP aprovado | `smtp.example.invalid` | staging/produção |
| `LABCIM_SMTP_PORT` | Obrigatória para SMTP | porta SMTP/STARTTLS | `587` | staging/produção |
| `LABCIM_SMTP_USER` | Obrigatória para SMTP | conta do serviço | `labcim-manager@example.invalid` | staging/produção |
| `LABCIM_SMTP_PASSWORD` | Obrigatória para SMTP | credencial secreta | `<SMTP_PASSWORD>` | staging/produção |
| `LABCIM_SMTP_FROM` | Obrigatória para SMTP | remetente autorizado | `LabCim Manager <labcim-manager@example.invalid>` | staging/produção |
| `LABCIM_SMTP_TLS` | Obrigatória para SMTP | política STARTTLS | `true` | staging/produção |
| `LABCIM_AUTH_DEBUG_CODES` | Obrigatória em produção | deve ser explicitamente `false` | `false` | produção |

## Processo e diagnóstico

| Variável | Obrigatoriedade | Finalidade | Exemplo seguro | Ambiente |
|---|---|---|---|---|
| `TZ` | Obrigatória enquanto timestamps forem ingênuos | semântica local consistente | `America/Fortaleza` | staging/produção |
| `PYTHONUNBUFFERED` | Recomendada | entrega imediata de logs ao journald | `1` | staging/produção |
| `LABCIM_DEBUG_PERF` | Opcional | diagnóstico temporário de performance | `false` | development/staging |

## Exemplo estrutural não utilizável

```dotenv
APP_ENV=production
APP_BASE_URL=https://manager.example.invalid/manager/
DATABASE_URL=postgresql://labcim_app:<DB_PASSWORD>@127.0.0.1:5432/labcim_manager
STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=/var/lib/labcim-manager/uploads
LOCAL_WORK_ROOT=/var/lib/labcim-manager/work
APP_LOG_LEVEL=INFO
STREAMLIT_SERVER_COOKIE_SECRET=<RANDOM_HIGH_ENTROPY_SECRET>
LABCIM_AUTH_DEBUG_CODES=false
TZ=America/Fortaleza
```

O exemplo é deliberadamente inválido por conter placeholders. Não o copie como credencial.
