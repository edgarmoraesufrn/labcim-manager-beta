# Publicação beta: GitHub + Streamlit Community Cloud

## 1. Antes de publicar

Não coloque senha normal do Gmail no código.

Para o Gmail:

1. Acesse a conta `labcim.manager@gmail.com`.
2. Ative a verificação em duas etapas.
3. Gere uma senha de app.
4. Use a senha de app como `smtp_password`.

Recomenda-se usar repositório privado, pois a base contém nomes, e-mails e telefones dos usuários.

## 2. Arquivos que devem ir para o GitHub

Inclua:

- `app.py`
- `requirements.txt`
- `labcim_manager/`
- `assets/`
- `data/LabCim_Base.xlsx`
- `.streamlit/config.toml`
- `.streamlit/secrets.toml.example`
- `README.md`
- `README_v8_5.md` e posteriores

Não inclua:

- `.streamlit/secrets.toml`
- `data/labcim_manager.db`
- `.venv/`
- `__pycache__/`

O `.gitignore` já está preparado para isso.

## 3. Criar repositório local

Na pasta do projeto:

```powershell
git init
git add .
git status
git commit -m "Beta LabCim Manager"
git branch -M main
```

## 4. Criar repositório no GitHub

Crie um repositório privado, por exemplo:

```text
labcim-manager-beta
```

Depois conecte:

```powershell
git remote add origin https://github.com/SEU_USUARIO/labcim-manager-beta.git
git push -u origin main
```

## 5. Publicar no Streamlit Community Cloud

1. Acesse o Streamlit Community Cloud.
2. Clique em `New app`.
3. Escolha o repositório `labcim-manager-beta`.
4. Branch: `main`.
5. Main file path: `app.py`.
6. Abra `Advanced settings`.
7. Em `Secrets`, cole:

```toml
[email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = "labcim.manager@gmail.com"
smtp_password = "COLE_AQUI_A_SENHA_DE_APP_DO_GOOGLE"
smtp_from = "LabCim Manager <labcim.manager@gmail.com>"
smtp_tls = true

# PostgreSQL externo para persistência em produção/beta.
# Substitua por uma URL real apenas nos Secrets do Streamlit Cloud.
DATABASE_URL = "postgresql://USUARIO:SENHA@HOST:5432/NOME_DO_BANCO?sslmode=require"

# Cloudflare R2 privado para PDFs e anexos persistentes.
R2_ACCOUNT_ID = "SEU_ACCOUNT_ID"
R2_ENDPOINT_URL = "https://SEU_ACCOUNT_ID.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID = "SEU_ACCESS_KEY_ID"
R2_SECRET_ACCESS_KEY = "SEU_SECRET_ACCESS_KEY"
R2_BUCKET = "labcim-manager-arquivos"
```

O app também aceita `[database]` com `url` e `[r2]` com as mesmas chaves R2. O formato top-level acima é o mais direto para conferir no painel de Secrets do Streamlit Cloud.

8. Clique em `Deploy`.

## 6. Atenção sobre persistência

O Streamlit Community Cloud não deve ser tratado como armazenamento definitivo para SQLite local. Para produção/beta, use PostgreSQL externo via `DATABASE_URL`.

Comportamento esperado:

- sem `DATABASE_URL`, o app usa SQLite local em `data/labcim_manager.db`;
- com `DATABASE_URL`, o app usa PostgreSQL externo;
- sem `DATABASE_URL` e sem R2, uploads usam `data/uploads` apenas para desenvolvimento local;
- com `DATABASE_URL`, uploads exigem R2 completo e não caem silenciosamente para armazenamento local;
- `data/LabCim_Base.xlsx` é importado apenas quando o banco operacional está vazio;
- `data/labcim_manager.db` e `data/uploads` não devem ser versionados, pois são mutáveis e podem conter dados de uso.

O banco guarda apenas metadados dos anexos na tabela `attachments`. Os arquivos reais ficam no R2 em produção. O bucket deve permanecer privado; o app gera URL assinada temporária para download quando necessário. Campos antigos `*_path` continuam aceitos como modo legado para links/caminhos já cadastrados.

Opções comuns de PostgreSQL externo:

- Supabase;
- Neon PostgreSQL;
- Render PostgreSQL;
- outro PostgreSQL institucional.

Para validar persistência:

1. Configure `DATABASE_URL` e os secrets R2 nos Secrets.
2. Faça deploy.
3. Cadastre usuário, reserva e insumo/movimentação com anexo pequeno.
4. Reinicie ou redeploye o app.
5. Confirme que os dados continuam no app, os metadados aparecem no PostgreSQL e o arquivo existe no bucket R2.
6. Confirme que a URL direta do objeto no bucket privado não abre sem assinatura.
