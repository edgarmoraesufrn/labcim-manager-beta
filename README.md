# LabCim Manager

Sistema de Gestão de Estoque, Equipamentos, Reservas e Manutenção do LabCim.

## Versão beta

Esta versão inclui:

- login por e-mail com senha volátil;
- perfis `admin`, `manager` e `member`;
- agenda visual de equipamentos;
- reservas;
- manutenção preventiva/corretiva;
- POPs/documentos operacionais;
- módulo de insumos/almoxarifado;
- QR Codes;
- relatórios semestrais/anuais;
- notificações por e-mail quando equipamento entra em manutenção.

## Rodar localmente

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Sem `DATABASE_URL`, o app usa automaticamente SQLite local em `data/labcim_manager.db`. Esse arquivo é mutável, serve apenas para desenvolvimento local e não deve ser enviado ao GitHub.

## Configurar e-mail

Copie:

```text
.streamlit/secrets.toml.example
```

para:

```text
.streamlit/secrets.toml
```

Preencha os dados SMTP. Para Gmail, use senha de app, não a senha normal da conta.

## Observação sobre banco de dados

O LabCim Manager escolhe o backend de banco no startup:

- sem `DATABASE_URL`: usa SQLite local em `data/labcim_manager.db`;
- com `DATABASE_URL`: usa PostgreSQL externo.

Em produção/beta, configure `DATABASE_URL` nos Secrets do Streamlit Cloud ou como variável de ambiente. Não coloque a URL real, senha, token ou qualquer secret no código.

Exemplo seguro para Secrets:

```toml
DATABASE_URL = "postgresql://USUARIO:SENHA@HOST:5432/NOME_DO_BANCO?sslmode=require"
```

O arquivo `data/labcim_manager.db` não deve ser versionado porque é um banco local mutável e pode conter dados operacionais de usuários. O `.gitignore` mantém esse arquivo fora do repositório.

`data/LabCim_Base.xlsx` continua sendo usado apenas como seed inicial quando o banco operacional estiver vazio.

Para testar persistência em produção:

1. Configure `DATABASE_URL` apontando para um PostgreSQL externo.
2. Faça deploy do app.
3. Cadastre um usuário, uma reserva e um insumo ou movimentação de insumo.
4. Reinicie ou redeploye o app.
5. Confirme que os registros continuam aparecendo no sistema.

## Armazenamento de arquivos

O banco PostgreSQL/SQLite guarda apenas metadados dos anexos. PDFs, imagens, planilhas e vídeos enviados pelos usuários não são armazenados no banco.

Comportamento esperado:

- sem `DATABASE_URL` e sem configuração R2: usa armazenamento local em `data/uploads`, apenas para desenvolvimento;
- com `DATABASE_URL` e R2 completo: usa Cloudflare R2;
- com `DATABASE_URL` e R2 ausente/incompleto: o app bloqueia uploads e mostra erro claro, para evitar perda silenciosa de arquivos em produção.

Secrets/variáveis aceitos no formato top-level do Streamlit Cloud:

```toml
DATABASE_URL = "postgresql://USUARIO:SENHA@HOST:5432/NOME_DO_BANCO?sslmode=require"
R2_ACCOUNT_ID = "SEU_ACCOUNT_ID"
R2_ENDPOINT_URL = "https://SEU_ACCOUNT_ID.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID = "SEU_ACCESS_KEY_ID"
R2_SECRET_ACCESS_KEY = "SEU_SECRET_ACCESS_KEY"
R2_BUCKET = "labcim-manager-arquivos"
```

Também são aceitas as seções `[database]` com `url` e `[r2]` com as mesmas chaves R2. Para uploads em produção, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` e `R2_BUCKET` precisam estar configurados; `R2_ACCOUNT_ID` é mantido no exemplo para facilitar a conferência do endpoint.

O bucket R2 deve permanecer privado. Downloads devem ser feitos pelo app via URL assinada temporária. Caminhos e links antigos nos campos `*_path` continuam tratados como modo legado, sem migração destrutiva.

`data/uploads` não deve ser versionado porque contém arquivos enviados por usuários e é efêmero em deploys como Streamlit Cloud.
