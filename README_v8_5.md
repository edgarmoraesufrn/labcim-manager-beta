# LabCim Manager v8.5

Versão beta com acesso real por e-mail e notificações de manutenção.

## Implementações

- Login por e-mail com senha volátil:
  - usuário seleciona e-mail cadastrado ou digita manualmente;
  - sistema gera código de 6 dígitos;
  - código expira em 10 minutos;
  - código só pode ser usado uma vez;
  - limite de tentativas por código;
  - sessão assume automaticamente o perfil cadastrado do usuário (`admin`, `manager`, `member`).
- Removido o seletor manual de perfil da barra lateral.
- Barra lateral mostra:
  - usuário logado;
  - e-mail;
  - perfil;
  - botão `Sair`.
- Modo beta local:
  - se SMTP não estiver configurado, o sistema mostra o código na tela para teste;
  - em produção, configurar SMTP para envio real por e-mail.
- Novas tabelas:
  - `access_codes`;
  - `notification_log`.
- Notificações por e-mail quando equipamento entra em manutenção:
  - ao marcar equipamento como `Em manutenção`;
  - ao registrar preventiva/calibração bloqueante;
  - destinatários incluem gerentes/admins, responsável/gestor técnico quando identificado e usuários com reservas futuras quando configurado.
- Log de notificações:
  - registra envio, erro ou pendência por falta de SMTP.

## Configuração de SMTP

Crie ou edite `.streamlit/secrets.toml`:

```toml
[email]
smtp_host = "smtp.seudominio.br"
smtp_port = 587
smtp_user = "usuario@seudominio.br"
smtp_password = "COLE_AQUI_A_SENHA_DE_APP"
smtp_from = "LabCim Manager <usuario@seudominio.br>"
smtp_tls = true
```

Também é possível usar variáveis de ambiente:

- `LABCIM_SMTP_HOST`
- `LABCIM_SMTP_PORT`
- `LABCIM_SMTP_USER`
- `LABCIM_SMTP_PASSWORD`
- `LABCIM_SMTP_FROM`
- `LABCIM_SMTP_TLS`

## Como rodar

```powershell
pip install -r requirements.txt
streamlit run app.py
```
