# LabCim Manager — desenvolvimento local e staging simulado

Este guia cobre somente execução efêmera/local. Não autoriza deploy nem uso de dados UFRN.

## Runtime reproduzível

O runtime suportado é Python **3.12.13**, declarado em `.python-version`. Ele foi escolhido por ser uma versão estável já usada na auditoria e compatível com as versões fixadas de Streamlit, pandas, psycopg, openpyxl, QR/Pillow, Plotly e boto3. Não é uma escolha automática pela versão Python mais nova.

Em Linux/macOS:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Em PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` exige hashes e instala o grafo transitivo resolvido em `requirements.lock`. `requirements.in` contém apenas dependências runtime diretas. Para atualizar o lock, faça uma mudança revisada e regeneração deliberada com `pip-compile --generate-hashes --output-file requirements.lock requirements.in` sob Python 3.12.13; não regenere durante um deploy.

## A. SQLite + storage local na raiz

O default de development é SQLite em `data/labcim_manager.db` e arquivos em `data/uploads`, ambos ancorados na raiz do projeto. O startup não cria mais o arquivo. Inicialize explicitamente uma vez e verifique antes de executar:

```bash
python -m labcim_manager.db_migrate status
python -m labcim_manager.db_migrate initialize
python -m labcim_manager.db_migrate verify
```

Para um arquivo descartável, informe a opção global antes do subcomando: `python -m labcim_manager.db_migrate --sqlite-path /tmp/labcim.db initialize`.

Seed é opcional e separado. Para popular deliberadamente um banco operacional vazio:

```bash
python -m labcim_manager.db_migrate seed-base --workbook data/LabCim_Base.xlsx
python -m labcim_manager.db_migrate seed-pops
```

Nenhum desses dados é importado ao iniciar o Streamlit. Para executar no caminho raiz, sobrescreva o default `/manager/` somente nessa invocação:

```bash
APP_ENV=development STORAGE_BACKEND=local \
  python -m streamlit run app.py --server.baseUrlPath= --server.address=127.0.0.1
```

PowerShell:

```powershell
$env:APP_ENV="development"
$env:STORAGE_BACKEND="local"
python -m streamlit run app.py --server.baseUrlPath= --server.address=127.0.0.1
```

Abra `http://127.0.0.1:8501/`. `APP_BASE_URL` é opcional enquanto nenhum QR for gerado. O manifesto continua intencionalmente instalável sob `/manager/`; não use o modo raiz para homologar instalação PWA. Para diagnóstico local detalhado, uma invocação explícita pode acrescentar `--client.showErrorDetails=full`; não use essa opção em staging/produção.

## B. Simulação local sob `/manager/`

Linux/macOS:

```bash
APP_ENV=staging \
APP_BASE_URL=http://127.0.0.1:8501/manager/ \
STORAGE_BACKEND=local \
LOCAL_STORAGE_ROOT=/tmp/labcim-manager-uploads \
LOCAL_WORK_ROOT=/tmp/labcim-manager-work \
python -m streamlit run app.py
```

PowerShell, usando um diretório temporário absoluto:

```powershell
$env:APP_ENV="staging"
$env:APP_BASE_URL="http://127.0.0.1:8501/manager/"
$env:STORAGE_BACKEND="local"
$env:LOCAL_STORAGE_ROOT="$env:TEMP\labcim-manager-uploads"
$env:LOCAL_WORK_ROOT="$env:TEMP\labcim-manager-work"
python -m streamlit run app.py
```

Abra `http://127.0.0.1:8501/manager/`. O profile versionado mantém loopback, porta 8501, `/manager/`, CORS/XSRF, limite de 50 MB e detalhes de erro ocultos.

## Conceitos das demais combinações

PostgreSQL + local:

```dotenv
APP_ENV=staging
APP_BASE_URL=https://staging.example.invalid/manager/
DATABASE_URL=postgresql://user:<PASSWORD>@127.0.0.1:5432/labcim_staging
STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=/absolute/staging/uploads
LOCAL_WORK_ROOT=/absolute/staging/work
```

PostgreSQL + R2 troca somente a seleção e fornece as quatro credenciais próprias:

```dotenv
STORAGE_BACKEND=r2
R2_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<ACCESS_KEY>
R2_SECRET_ACCESS_KEY=<SECRET_KEY>
R2_BUCKET=labcim-staging-files
```

Esses exemplos são placeholders e não devem ser usados como credenciais. `DATABASE_URL` nunca implica R2.

Antes de iniciar uma simulação PostgreSQL, use o mesmo ambiente restrito e execute `python -m labcim_manager.db_migrate status`. Em banco novo, `initialize` e `verify`; em snapshot restaurado sem ledger, execute `baseline-existing` sem confirmação, revise as divergências e só então repita com `--confirm-compatible-schema`, seguido de `upgrade` e `verify`. Não use a adoção para um schema parcial.

Se o banco estiver atrás, à frente, corrompido/desconhecido ou ausente, a UI se recusa a iniciar e não tenta repará-lo. Essa política é igual em development, staging e production; a conveniência local fica no comando explícito `initialize`.

## Validação local

```bash
python -m compileall app.py labcim_manager tests scripts/production_preflight.py
python -m unittest discover -s tests -v
python scripts/production_preflight.py
```

Sem um arquivo de ambiente real, o preflight deve reportar `ENVIRONMENT REQUIRED`; Nginx, systemd, PostgreSQL UFRN, browser via proxy e restore devem aparecer como `DEPLOYMENT PENDING`. `CODE BLOCKER` significa trabalho de repositório ainda necessário, não credencial ausente.

Para validar apenas a estrutura de um futuro arquivo systemd sem mostrar seus valores:

```bash
python scripts/production_preflight.py --env-file /caminho/restrito/manager.env
```

O preflight não conecta a banco, rede ou storage e não cria arquivos.
