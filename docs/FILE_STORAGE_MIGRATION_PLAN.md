# LabCim Manager — plano de migração de arquivos e anexos

Status: planejamento M0; nenhum arquivo migrado.

## 1. Backends existentes

### Local

- raiz fixa: `data/uploads` relativa ao CWD;
- chave: `attachments/<entity_type>/<entity_id>/<YYYY>/<MM>/<sha256>_<nome_seguro>`;
- proteção contra traversal em leitura por `resolve()`;
- criado automaticamente no primeiro save;
- não selecionável em produção quando `DATABASE_URL` existe.

### R2

- bucket privado configurado por `R2_*`;
- mesma estrutura de chave;
- download por URL assinada, TTL padrão de 300 segundos;
- SHA-256 salvo em metadata do objeto e na tabela `attachments`;
- obrigatório pelo código atual quando PostgreSQL está configurado e há upload.

### Legado

Algumas tabelas ainda possuem colunas `*_path`. Elas podem conter:

- `attachment:<id>`;
- caminho relativo dentro do repositório;
- caminho local histórico;
- URL HTTP/HTTPS;
- valor vazio.

## 2. Inventário feature → persistência

| Feature | Referência no banco | Entidade/role em `attachments` | Backend/chave | Ação de migração |
|---|---|---|---|---|
| POP legado de equipamento | `equipment.pop_path` | opcional `equipment` / `pop` | asset do repo, URL ou attachment | classificar; manter asset versionado ou materializar no backend escolhido |
| Documentos de equipamento | tabela `attachments` | `equipment` / `pop`, `manual`, `certificate`, `checklist`, `technical_document`, `other` | local/R2 padrão | copiar byte + preservar metadata/ID |
| FDS/FISPQ/SDS | `supplies.safety_doc_path` | `supply` / `safety_doc` | local/R2 padrão | reconciliar campo legado e attachment |
| Ficha técnica/caracterização | `supplies.technical_doc_path` | `supply` / `technical_doc` | local/R2 padrão | reconciliar campo legado e attachment |
| Certificado de análise do lote | `supply_lots.certificate_path` | `supply_lot` / `analysis_certificate` | local/R2 padrão | reconciliar campo legado e attachment |
| Anexo de movimentação | `supply_movements.document_path` | `supply_movement` / `movement_document` | local/R2 padrão | reconciliar campo legado e attachment |
| Checklist preventivo | `maintenance_preventive.checklist_path` | `maintenance_preventive` / `preventive_checklist` | local/R2 padrão | reconciliar campo legado e attachment |
| Certificado preventivo/calibração | `maintenance_preventive.certificate_path` | `maintenance_preventive` / `preventive_certificate` | local/R2 padrão | reconciliar campo legado e attachment |
| Evidência de manutenção corretiva | `maintenance_corrective.attachment_path` | `maintenance_corrective` / `corrective_attachment` | local/R2 padrão | reconciliar campo legado e attachment |
| Planilha de importação temporária | `data/_uploaded_base.xlsx` | nenhuma | arquivo fixo temporário | não migrar; substituir por temporário isolado e limpar em M1 |
| POPs empacotados | `assets/pops/*.pdf` | referenciados por `equipment.pop_path` | Git/release | manter somente se a política institucional aceitar documento operacional versionado no release |

Não foram encontrados uploads para projetos/serviços fora dessas referências.

## 3. Decisão de destino

### Opção A — filesystem da VM

Adequado quando UFRN possui backup confiável de `/var/lib` e volume inicial suficiente. Requer implementar:

- `LABCIM_STORAGE_BACKEND=local` ou contrato equivalente;
- `LABCIM_UPLOAD_ROOT=/var/lib/labcim-manager/uploads`;
- permissão local mesmo com `DATABASE_URL`;
- escrita atômica (`temp` + fsync/rename quando aplicável);
- quota, monitoramento de espaço e backup;
- download autenticado via Streamlit ou endpoint controlado;
- proteção contra symlink/traversal e permissões `0750/0640`.

Essas variáveis são propostas, **não são reconhecidas pelo código M0** e por isso não aparecem no template do ambiente atual.

### Opção B — manter R2

Menor mudança de código, porém requer:

- aprovação institucional do serviço externo;
- egress HTTPS/DNS;
- credenciais com acesso somente ao bucket/prefixo necessário;
- bucket privado, versionamento/retention conforme política;
- backup/restore e inventário independentes;
- teste de URLs assinadas e expiração;
- rotação de chaves.

### Recomendação M0

Escolher filesystem institucional se a política de backup da VM cobrir arquivos e a estimativa de crescimento couber com margem no disco. Caso contrário, manter R2 de forma explícita e aprovada. Não implementar um híbrido implícito.

## 4. Inventário antes da migração

Gerar relatório sem conteúdo dos documentos:

- attachment ID;
- entidade, entity ID e role;
- backend;
- storage key;
- nome original;
- MIME declarado;
- tamanho;
- SHA-256 esperado;
- ativo/inativo;
- campo legado correspondente;
- estado: encontrado, ausente, duplicado, órfão, externo ou inválido.

Também varrer colunas legadas para valores que não começam por `attachment:` e classificá-los. Nunca imprimir credenciais ou parâmetros de URL assinada.

## 5. Cópia segura

1. Fixar snapshot do banco correspondente ao inventário.
2. Tornar origem somente leitura durante a cópia final ou registrar delta.
3. Copiar sem apagar/mover a origem.
4. Preservar `storage_key` quando possível.
5. Calcular SHA-256 no destino e comparar com o banco/origem.
6. Verificar tamanho e contagem por role/backend.
7. Registrar manifesto de migração em local restrito.
8. Atualizar referências somente em transação controlada e após a cópia validada.
9. Reexecutar de forma idempotente.
10. Manter origem durante a janela de rollback.

Para arquivos sem SHA-256 no banco, calcular na origem e destino, sem alterar produção durante o inventário.

## 6. Integridade e órfãos

Verificar:

- attachment aponta para entidade existente;
- todo `attachment:<id>` existe e corresponde à entidade/role esperados;
- todo objeto ativo existe;
- objetos inativos são preservados conforme retenção;
- objeto sem linha no banco é relatado, não apagado automaticamente;
- `original_filename` não contém traversal;
- `storage_key` permanece dentro do prefixo permitido;
- SHA-256 e tamanho conferem;
- URL externa usa HTTPS ou recebe exceção formal;
- asset do release existe no commit implantado.

## 7. Testes funcionais por tipo

Para ao menos um arquivo de cada role:

- upload permitido;
- rejeição de tipo/tamanho proibido;
- download autenticado;
- nome e MIME corretos;
- reload/restart preserva acesso;
- inativação remove da UI sem apagar indevidamente o byte;
- `/manager/` funciona;
- URL R2 expira, se aplicável;
- restauração recupera banco e byte correspondente.

Incluir arquivo pequeno, nome com acentos/espaços, nome malicioso, arquivo no limite e arquivo acima do limite.

## 8. Backup e restore

### Filesystem

- backup coordenado com snapshot lógico do PostgreSQL;
- destino fora da VM;
- criptografia e retenção institucionais;
- restore em raiz isolada;
- reconciliação por manifest/SHA-256 antes da liberação.

### R2

- inventário/versionamento conforme capacidade contratada;
- backup ou replicação aprovados;
- export das configurações não secretas e política do bucket;
- restore coordenado com a tabela `attachments`.

## 9. Rollback

Manter metadata e bytes da origem intactos. Se o destino falhar, reverter a configuração para o backend anterior somente se o banco ainda contiver referências compatíveis. Caso references tenham mudado, restaurar banco e storage como conjunto.

Nenhum coletor deve apagar órfãos durante a migração inicial.

## 10. Gates

- [ ] backend escolhido e aprovado;
- [ ] raiz/bucket e permissões testados;
- [ ] inventário completo;
- [ ] zero attachment ativo ausente, ou exceções aprovadas;
- [ ] hashes/tamanhos reconciliados;
- [ ] campos legados classificados;
- [ ] uploads endurecidos;
- [ ] teste `/manager/` aprovado;
- [ ] backup e restore testados;
- [ ] rollback ensaiado.
