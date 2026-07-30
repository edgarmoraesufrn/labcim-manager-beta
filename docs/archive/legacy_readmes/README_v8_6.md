# LabCim Manager v8.6

Versão preparada para publicação beta em GitHub + Streamlit.

## Implementações

- Adicionado `.gitignore` para evitar envio de:
  - `.streamlit/secrets.toml`;
  - `data/labcim_manager.db`;
  - ambientes virtuais;
  - caches Python;
  - uploads temporários.
- Adicionado `.streamlit/secrets.toml.example` com configuração SMTP para Gmail.
- Adicionado `README.md` principal para GitHub.
- Adicionado `DEPLOY_BETA.md` com passo a passo de publicação.
- Mantido o envio por e-mail via `st.secrets` ou variáveis de ambiente.

## Segurança

- Não foi incluída nenhuma senha no código.
- Para Gmail, usar senha de app do Google.
- A senha normal da conta Google não deve ser usada no `smtp_password`.

## Observação de arquitetura

SQLite local é suficiente para teste beta controlado, mas não é a solução definitiva para produção em Streamlit Cloud.

Para uso permanente, recomenda-se PostgreSQL externo.

