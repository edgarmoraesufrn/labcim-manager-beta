# LabCim Manager v8.7 — Hotfix de login OTP

## Alterações

- Removido o pré-preenchimento do e-mail por lista de usuários na tela de login.
- Login simplificado: o usuário digita manualmente o e-mail cadastrado.
- Validação do código OTP mais robusta.
- Busca do código por e-mail + hash do código, evitando falhas quando há mais de um código recente.
- Mensagens de erro mais específicas: código expirado, já usado, incorreto ou inexistente.

## Deploy

Após substituir os arquivos, executar:

```powershell
git add .
git commit -m "Hotfix login OTP v8.7"
git push
```

O Streamlit Cloud deve redeployar automaticamente.
