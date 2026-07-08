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
