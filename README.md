# LabCim Manager v1.0

Gestão integrada, rastreabilidade e governança operacional do LabCim.

## Visão geral

O LabCim Manager é uma plataforma web para gestão operacional do laboratório. A aplicação integra equipamentos, documentos, reservas, manutenção, insumos, peças, lotes, projetos, serviços/análises e relatórios em um fluxo único e rastreável.

O foco da v1.0 é organizar a operação diária, reduzir dependência de controles dispersos e fortalecer a governança do polo com simplicidade operacional.

## Principais módulos

- Equipamentos e documentos/POPs.
- QR Codes.
- Reservas.
- Manutenção preventiva e corretiva.
- Insumos, peças de reposição e lotes.
- Projetos e serviços/análises.
- Relatórios e Excel profissional.
- Perfis `member`, `manager` e `admin`.

## Infraestrutura

O código atual suporta Streamlit, PostgreSQL via `DATABASE_URL`, SQLite local, Cloudflare R2 e armazenamento local de desenvolvimento. A infraestrutura histórica era Streamlit Cloud + Neon + R2.

A migração institucional para Nginx + Streamlit em `/manager/` + PostgreSQL na UFRN está em preparação. A auditoria M0 classificou o estado atual como **NO-GO para produção** até que os blockers documentados sejam resolvidos e validados em staging. Nenhum deploy UFRN foi executado.

## Documentação

- [Prontidão para produção UFRN — M0](docs/PRODUCTION_READINESS.md)
- [Plano de implantação UFRN](docs/UFRN_DEPLOYMENT_PLAN.md)
- [Plano de migração do banco](docs/DATABASE_MIGRATION_PLAN.md)
- [Plano de migração de arquivos](docs/FILE_STORAGE_MIGRATION_PLAN.md)
- [Template de ambiente de produção](docs/PRODUCTION_ENV_TEMPLATE.md)
- [Runbook de produção](docs/production_runbook.md)
- [Pacote de demonstração v1.0 para auditoria](docs/v1_0_audit_demo_package.md)
- [Release notes v1.0](docs/v1_0_release_notes.md)
- [Documentação histórica](docs/archive/legacy_readmes/)

## Status

Versão operacional v1.0 para o ambiente histórico. Migração de produção UFRN em fase de auditoria/hardening; consulte o documento de prontidão antes de qualquer implantação.

## Roadmap

- v1.1: senha individual com fallback para código volátil.
- v1.1: dashboards gerenciais avançados.
- v1.1: refinamentos a partir de uso real e auditoria.
- v1.2: empacotamento Android/Google Play.
