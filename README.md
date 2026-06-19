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

O banco SQLite local (`data/labcim_manager.db`) é mutável e não deve ser enviado ao GitHub.  
Em um deploy novo, o app recria a base inicial a partir de `data/LabCim_Base.xlsx`.

Para produção, recomenda-se migrar o banco para PostgreSQL/Supabase/Neon.

