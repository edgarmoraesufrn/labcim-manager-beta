# LabCim Manager v8.8

Hotfix do login por senha volátil.

## Correções

- Removido definitivamente o segundo campo editável de e-mail na validação.
- O usuário digita o e-mail apenas uma vez, ao solicitar a senha volátil.
- Na validação, o sistema usa o e-mail salvo na sessão após o envio do código.
- A tela agora mostra claramente o e-mail que será validado.
- Mensagens de erro do OTP ficaram mais específicas:
  - código não informado;
  - senha volátil ainda não solicitada;
  - código inválido;
  - nenhum código ativo para o e-mail;
  - código expirado;
  - muitas tentativas.
- Validação do código agora busca o par `e-mail + código`, reduzindo ambiguidade quando há mais de um pedido de senha.

## Deploy

Após copiar os arquivos para o repositório local:

```powershell
git add .
git commit -m "Hotfix login OTP v8.8"
git push
```

Depois, no Streamlit Cloud:

- aguarde o redeploy automático; ou
- use `Manage app > Reboot`.

