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

- Streamlit Cloud como aplicação web.
- PostgreSQL/Neon para persistência de dados em produção.
- Cloudflare R2 para armazenamento persistente e privado de arquivos.
- SQLite e armazenamento local para desenvolvimento.
- Excel completo gerado sob demanda.
- QR Codes e pacotes ZIP gerados sob demanda.

## Documentação

- [Runbook de produção beta](docs/production_runbook.md)
- [Pacote de demonstração v1.0 para auditoria](docs/v1_0_audit_demo_package.md)
- [Release notes v1.0](docs/v1_0_release_notes.md)
- [Documentação histórica](docs/archive/legacy_readmes/)

## Status

Versão operacional v1.0, preparada para apresentação institucional e melhoria contínua.

## Roadmap

- v1.1: senha individual com fallback para código volátil.
- v1.1: dashboards gerenciais avançados.
- v1.1: refinamentos a partir de uso real e auditoria.
- v1.2: empacotamento Android/Google Play.
