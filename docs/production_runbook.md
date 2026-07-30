# LabCim Manager — Runbook de Produção Beta

## 1. Objetivo

Este documento é um checklist operacional para liberar e acompanhar o LabCim Manager em produção beta controlada. Ele não substitui revisão técnica, mas organiza as conferências mínimas de ambiente, permissões, persistência, backup e recuperação.

## 2. Secrets obrigatórios

Configure os secrets no Streamlit Cloud ou como variáveis de ambiente, sem registrar valores reais no repositório:

- `DATABASE_URL`
- `R2_ENDPOINT_URL`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`
- `smtp_host` ou `[email].smtp_host` ou `LABCIM_SMTP_HOST`
- `smtp_port` ou `[email].smtp_port` ou `LABCIM_SMTP_PORT`
- `smtp_user` ou `[email].smtp_user` ou `LABCIM_SMTP_USER`
- `smtp_password` ou `[email].smtp_password` ou `LABCIM_SMTP_PASSWORD`
- `smtp_from` ou `[email].smtp_from` ou `LABCIM_SMTP_FROM`
- `smtp_tls` ou `[email].smtp_tls` ou `LABCIM_SMTP_TLS`

## 3. Flags opcionais

- `LABCIM_DEBUG_PERF`: ativa painel técnico de performance para diagnóstico controlado.
- `R2_ACCOUNT_ID`: opcional, útil para conferir o endpoint R2.

## 4. Flags proibidas/perigosas em produção

- `LABCIM_AUTH_DEBUG_CODES=true` não deve estar ativo em produção. Essa flag permite exibir código de acesso volátil quando SMTP falha ou em diagnóstico, portanto deve ficar ausente ou `false`.

## 5. Checklist antes de liberar

- `DATABASE_URL` configurado para PostgreSQL/Neon.
- R2 configurado com bucket privado.
- SMTP funcionando com senha de app ou credencial apropriada.
- `LABCIM_AUTH_DEBUG_CODES` ausente ou `false`.
- Login testado.
- Perfil `member` testado.
- Perfil `manager` testado.
- Perfil `admin` testado.
- Reboot/redeploy testado.
- Persistência após reboot testada para banco e arquivos.

## 6. Testes por perfil

### member

- Fazer login.
- Criar reserva própria.
- Cancelar a própria reserva `scheduled`.
- Reportar problema em equipamento.
- Consultar documentos operacionais.
- Registrar saída/consumo de insumo.
- Confirmar ausência da página Relatórios.
- Confirmar ausência da lista completa de usuários.
- Confirmar ausência do CSV completo de estoque.
- Confirmar ausência do cadastro estrutural de insumos.
- Confirmar ausência do CSV de histórico de movimentações.
- Confirmar ausência de ZIP em massa de QR Codes.

### manager

- Criar e alterar reservas de terceiros.
- Usar fluxo completo de manutenção.
- Editar equipamentos e documentos.
- Gerenciar insumos e lotes.
- Gerenciar projetos e serviços/análises.
- Acessar relatórios e exportações.
- Gerar ZIP em massa de QR Codes.

### admin

- Criar e editar usuários/perfis.
- Importar base com backup prévio.
- Conferir permissões.
- Acessar relatórios e exportações.

## 7. Testes de infraestrutura

- Enviar arquivo para R2.
- Baixar arquivo do R2 por URL assinada.
- Solicitar código de login por SMTP.
- Fazer reboot/redeploy no Streamlit Cloud.
- Confirmar persistência no Neon.
- Confirmar persistência de arquivo no R2.
- Gerar QR individual.
- Gerar ZIP de QR Codes com perfil `manager` ou `admin`.

## 8. Backup e recuperação

### Neon

- Fazer backups e restores pelo painel do Neon ou mecanismo oficial disponível na conta.
- Registrar data, hora, commit e responsável antes de mudanças grandes.
- Validar restore em ambiente seguro antes de sobrescrever produção.

### R2

- Registrar nome do bucket e política de acesso.
- Manter o bucket privado.
- Preservar arquivos junto com os metadados da tabela `attachments`.
- Restaurar banco e R2 de forma coordenada para evitar anexos sem referência ou referências sem arquivo.

## 9. Rollback pós-deploy

- Identificar último commit ou PR estável.
- Reverter o PR problemático ou voltar a `main` para commit estável.
- Fazer redeploy no Streamlit Cloud.
- Validar login, conexão com banco, upload/download R2 e principais fluxos por perfil.

## 10. Procedimento em caso de falha

### Login falhando

- Conferir SMTP e `LABCIM_AUTH_DEBUG_CODES`.
- Confirmar que o usuário está ativo e com role válido.
- Conferir `notification_log` se necessário.

### SMTP falhando

- Conferir host, porta, usuário, senha, remetente e TLS.
- Confirmar se o provedor exige senha de app.
- Manter fail-closed; não ativar debug de código em produção.

### R2 falhando

- Conferir endpoint, bucket e chaves.
- Confirmar que o bucket está privado.
- Testar upload e download de um anexo pequeno.

### Banco indisponível

- Conferir `DATABASE_URL`.
- Verificar disponibilidade do Neon.
- Confirmar se a connection string pooled está ativa.

### App lento

- Conferir Neon, Streamlit Cloud e tamanho dos relatórios.
- Usar `LABCIM_DEBUG_PERF` apenas temporariamente.
- Desativar a flag ao fim do diagnóstico.

### Dados inconsistentes

- Não editar banco manualmente sem backup.
- Registrar tela, horário, usuário e ação.
- Restaurar em ambiente seguro antes de aplicar qualquer correção em produção.

## 11. O que não fazer em produção

- Não ativar debug de código de login.
- Não usar importação de base sem backup prévio.
- Não apagar secrets sem registrar.
- Não alterar banco manualmente sem backup.
- Não fazer deploy de branch não revisada.
- Não tornar bucket R2 público.
- Não versionar secrets, banco local ou uploads.

## 12. Registro de liberação

- Data:
- Versão/commit:
- Responsável:
- Secrets conferidos:
- Testes `member` executados:
- Testes `manager` executados:
- Testes `admin` executados:
- Testes de SMTP:
- Testes de Neon:
- Testes de R2:
- Reboot/redeploy validado:
- Pendências:
