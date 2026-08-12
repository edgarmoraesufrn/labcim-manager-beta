# LabCim Manager — plano de migração de arquivos e anexos

Status: contrato de backend implementado no M1A; nenhum arquivo real foi migrado.

## 1. Contrato atual

Banco e arquivos são selecionados independentemente:

| Banco | `STORAGE_BACKEND` | Estado de código |
|---|---|---|
| SQLite | `local` | suportado |
| PostgreSQL | `local` | suportado |
| PostgreSQL | `r2` | suportado |

`DATABASE_URL` escolhe somente SQLite/PostgreSQL. `STORAGE_BACKEND` escolhe somente `local`/`r2`. Em staging e produção não há fallback de storage: a seleção deve ser explícita.

### Local

- raiz definida por `LOCAL_STORAGE_ROOT`;
- staging/produção exigem caminho absoluto, por exemplo `/var/lib/labcim-manager/uploads`;
- development/test usam `data/uploads` sob a raiz do projeto por default;
- chaves portáveis: `attachments/<entidade>/<id>/<AAAA>/<MM>/<sha256>_<nome_seguro>`;
- escrita cria apenas os diretórios pais da chave validada;
- `resolve()` impede traversal para fora da raiz;
- nenhuma permissão `0777` é aplicada.

### R2

- selecionado somente por `STORAGE_BACKEND=r2`;
- exige `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` e `R2_BUCKET`;
- mantém bucket privado, mesma estrutura de chave, SHA-256 em metadata e URLs de download assinadas;
- configuração R2 incompleta falha sem fallback silencioso para disco.

## 2. Referências existentes

Algumas tabelas ainda contêm colunas `*_path`. Os valores podem ser `attachment:<id>`, caminho relativo dentro do release, caminho local histórico, URL HTTP(S) ou vazio. Assets empacotados, como `assets/pops/*.pdf`, continuam resolvidos a partir da raiz do projeto e não do CWD.

| Feature | Referência | Destino a reconciliar |
|---|---|---|
| documentos/POPs de equipamento | `equipment.pop_path` e `attachments` | backend escolhido ou asset versionado aprovado |
| FDS/FISPQ/SDS e ficha técnica | campos de `supplies` e `attachments` | backend escolhido |
| certificado de lote | `supply_lots.certificate_path` | backend escolhido |
| anexo de movimentação | `supply_movements.document_path` | backend escolhido |
| manutenção preventiva/corretiva | campos de path e `attachments` | backend escolhido |
| import temporário | `data/_uploaded_base.xlsx` | não migrar; arquivo operacional temporário |

## 3. Decisão institucional pendente

Escolher filesystem institucional se o volume estiver coberto por backup, restore, quota e monitoramento da UFRN. Escolher R2 somente com aprovação institucional para dependência externa, residência/retenção, egress e gestão de credenciais. Não criar híbrido implícito.

O M1A implementa a seleção; não toma a decisão operacional e não copia bytes.

## 4. Inventário antes de qualquer migração

Gerar relatório sem conteúdo dos documentos: attachment ID, entidade/role, backend, storage key, nome, MIME, tamanho, SHA-256, status, campo legado e estado encontrado/ausente/duplicado/órfão/externo/inválido. Nunca imprimir credenciais ou parâmetros de URL assinada.

Também classificar valores legados que não começam por `attachment:`. Nenhum inventário deve apagar órfãos.

## 5. Cópia e reconciliação seguras

1. Fixar snapshot do banco correspondente ao inventário.
2. Tornar a origem somente leitura durante a cópia final ou registrar delta.
3. Copiar sem apagar nem mover a origem.
4. Preservar `storage_key` quando possível.
5. Comparar SHA-256 e tamanho entre origem, destino e banco.
6. Atualizar referências somente em transação controlada após a cópia validada.
7. Tornar o procedimento idempotente e manter origem durante a janela de rollback.
8. Restaurar banco e storage como um conjunto quando houver rollback.

## 6. Validação obrigatória futura

- upload/download de cada role de documento;
- nome com acentos/espaços e tentativa de traversal;
- tipo/tamanho permitido, no limite e acima do limite;
- persistência após restart;
- `/manager/` e autorização do download;
- expiração de URL assinada, se R2;
- inventário sem attachment ativo ausente ou com exceção formal;
- backup e restore completos em ambiente isolado.

## 7. Gates

- [ ] backend aprovado institucionalmente;
- [ ] raiz/bucket, dono e permissões testados;
- [ ] inventário e origem autoritativa confirmados;
- [ ] hashes/tamanhos reconciliados;
- [ ] campos legados classificados;
- [ ] upload allowlist e validação de conteúdo endurecidos;
- [ ] teste funcional sob `/manager/` aprovado;
- [ ] backup/restore e rollback ensaiados.
