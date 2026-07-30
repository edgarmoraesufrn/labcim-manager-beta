# LabCim Manager v1.0 — Release Notes

## 1. Visão geral

O LabCim Manager v1.0 é a primeira versão operacional integrada para gestão, rastreabilidade e governança do LabCim. A versão consolida módulos essenciais do laboratório em uma plataforma web simples, com foco em controle operacional, persistência de dados, documentos, relatórios e responsabilidades por perfil.

## 2. Principais capacidades

- Autenticação por código volátil.
- Perfis `member`, `manager` e `admin`.
- Cadastro e gestão de equipamentos.
- Documentos/POPs associados a equipamentos.
- QR Codes para equipamentos, documentação, manutenção e insumos.
- Reservas de equipamentos.
- Manutenção preventiva e corretiva.
- Insumos e almoxarifado.
- Peças de reposição associadas a equipamentos.
- Controle de lotes.
- Projetos.
- Serviços/análises.
- Relatórios operacionais e gerenciais.
- Excel profissional com identidade LabCim.
- PostgreSQL/Neon para persistência de dados.
- Cloudflare R2 para persistência de arquivos.
- Runbook de produção.

## 3. Governança e segurança

- Revalidação do usuário autenticado no banco.
- Permissões por perfil.
- Importação de base restrita a `admin`.
- Relatórios e exportações formais restritos a `manager/admin`.
- Fluxo `member` simplificado.
- Estoque para `member` restrito a saída/consumo.
- CSV completo de estoque restrito a `manager/admin`.
- CSV de histórico de movimentações restrito a `manager/admin`.
- ZIP em massa de QR Codes restrito a `manager/admin`.
- Dashboard de `member` simplificado para reduzir exposição de dados administrativos.

## 4. Rastreabilidade

A v1.0 estabelece uma cadeia rastreável entre operação e gestão:

- Reservas com histórico de status.
- Manutenção com histórico de status e justificativas.
- Movimentações de estoque com responsável, data, projeto/serviço e anexo opcional.
- Lotes com validade, saldo e certificado de análise.
- Anexos e documentos persistidos como metadados no banco e arquivos no R2.
- Vínculo entre projetos, serviços/análises, reservas e consumo de insumos.
- Relatórios e Excel consolidando dados operacionais.

## 5. Infraestrutura

- PostgreSQL/Neon como banco persistente em produção.
- Cloudflare R2 como armazenamento persistente e privado de arquivos.
- Streamlit Cloud como aplicação web.
- Excel completo gerado sob demanda.
- ZIP de QR Codes gerado sob demanda.
- SQLite e armazenamento local preservados para desenvolvimento.

## 6. Limitações conhecidas

- Login por senha individual ainda não implementado.
- Dashboards gerenciais avançados ficam para v1.1.
- App Android/Google Play fica para etapa posterior.
- Backend guards profundos ficam para evolução futura.
- A operação depende de internet, Streamlit Cloud, Neon e R2.

## 7. Roadmap pós-v1.0

- v1.1: senha individual com fallback para código volátil.
- v1.1: dashboards gerenciais avançados.
- v1.1: refinamentos a partir da auditoria.
- v1.2: empacotamento Android/Google Play.
- v1.2: política de privacidade e Data Safety para publicação mobile.

## 8. Instrução para tag/release GitHub

Não executar antes do merge da Sprint 11C.

Após merge da Sprint 11C:

1. Confirmar `main` atualizada.
2. Rodar validação final:

```bash
python -m compileall app.py labcim_manager
git diff --check
git status
```

3. Criar tag:

```bash
git tag -a v1.0.0 -m "LabCim Manager v1.0.0"
```

4. Fazer push da tag:

```bash
git push origin v1.0.0
```

5. Criar GitHub Release:

- Título: `LabCim Manager v1.0.0`
- Corpo: resumo destas release notes.

## 9. Checklist final para declarar v1.0

- PR 11C mergeado.
- Streamlit redeployado.
- Login testado.
- Perfil `member` testado.
- Perfil `manager` testado.
- Perfil `admin` testado.
- R2 testado.
- Neon testado.
- Excel exportado.
- QR individual testado.
- QR ZIP `manager/admin` testado.
- Runbook revisado.
- Demo package revisado.
