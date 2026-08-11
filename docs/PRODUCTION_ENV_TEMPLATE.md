# LabCim Manager — template de ambiente de produção

Somente nomes, finalidade, obrigatoriedade e formatos fictícios são documentados abaixo. Todos os valores sensíveis são placeholders.

## 1. Banco

| Variável | Obrigatória | Finalidade | Exemplo fictício |
|---|---:|---|---|
| `DATABASE_URL` | Sim | conexão PostgreSQL usada pelo app | `postgresql://labcim_app:<DB_PASSWORD>@127.0.0.1:5432/labcim_manager` |

## 2. Streamlit e `/manager/`

| Variável | Obrigatória | Finalidade | Exemplo fictício |
|---|---:|---|---|
| `STREAMLIT_SERVER_ADDRESS` | Sim | impedir exposição direta; somente loopback | `127.0.0.1` |
| `STREAMLIT_SERVER_PORT` | Sim | porta do upstream Nginx | `8501` |
| `STREAMLIT_SERVER_HEADLESS` | Sim | execução sem browser/prompt interativo | `true` |
| `STREAMLIT_SERVER_BASE_URL_PATH` | Sim | publicar sob o prefixo institucional | `manager` |
| `STREAMLIT_SERVER_ENABLE_CORS` | Sim | manter proteção CORS do Streamlit | `true` |
| `STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION` | Sim | manter proteção XSRF | `true` |
| `STREAMLIT_SERVER_COOKIE_SECRET` | Sim | chave de assinatura de cookies; valor estável e aleatório | `<RANDOM_HIGH_ENTROPY_SECRET>` |
| `STREAMLIT_SERVER_MAX_UPLOAD_SIZE` | Sim | limite global em MB, igual ou menor que o Nginx | `<APPROVED_MB>` |
| `STREAMLIT_SERVER_MAX_MESSAGE_SIZE` | Sim | limite WebSocket em MB compatível com upload | `<APPROVED_MB>` |
| `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS` | Sim | impedir traceback/detalhes no navegador | `none` |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | Recomendável | desabilitar telemetria no ambiente institucional | `false` |

## 3. SMTP/autenticação

| Variável | Obrigatória | Finalidade | Exemplo fictício |
|---|---:|---|---|
| `LABCIM_SMTP_HOST` | Sim | host SMTP aprovado | `smtp.example.invalid` |
| `LABCIM_SMTP_PORT` | Sim | porta SMTP/STARTTLS | `587` |
| `LABCIM_SMTP_USER` | Sim | conta do serviço | `labcim-manager@example.invalid` |
| `LABCIM_SMTP_PASSWORD` | Sim | credencial secreta da conta | `<SMTP_PASSWORD>` |
| `LABCIM_SMTP_FROM` | Sim | remetente visível e autorizado | `LabCim Manager <labcim-manager@example.invalid>` |
| `LABCIM_SMTP_TLS` | Sim | habilitar STARTTLS | `true` |
| `LABCIM_AUTH_DEBUG_CODES` | Sim | deve permanecer desabilitado em produção | `false` |

## 4. Storage reconhecido atualmente

| Variável | Obrigatória no código M0 | Finalidade | Exemplo fictício |
|---|---:|---|---|
| `R2_ENDPOINT_URL` | Sim para upload com PostgreSQL | endpoint S3 do R2 | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `R2_ACCESS_KEY_ID` | Sim para upload com PostgreSQL | identificador de acesso | `<R2_ACCESS_KEY_ID>` |
| `R2_SECRET_ACCESS_KEY` | Sim para upload com PostgreSQL | chave secreta | `<R2_SECRET_ACCESS_KEY>` |
| `R2_BUCKET` | Sim para upload com PostgreSQL | bucket privado | `labcim-manager-files` |
| `R2_ACCOUNT_ID` | Não | conferência/identificação do endpoint | `<R2_ACCOUNT_ID>` |

## 5. Processo e diagnóstico

| Variável | Obrigatória | Finalidade | Exemplo fictício |
|---|---:|---|---|
| `TZ` | Sim enquanto timestamps forem ingênuos | manter semântica local consistente | `America/Fortaleza` |
| `PYTHONUNBUFFERED` | Recomendável | enviar logs imediatamente ao journald | `1` |
| `LABCIM_DEBUG_PERF` | Não | painel temporário de performance; manter desligado | `false` |
