# LabCim Manager — segurança de uploads e downloads

Status: allowlists e validação central implementadas em M1C. Antivírus institucional, quotas, permissões e restore continuam controles de infraestrutura/staging.

## Snapshot anterior ao M1C

Antes da mudança, 13 dos 14 pickers possuíam filtros de extensão espalhados na UI, mas o uploader de equipamento aceitava qualquer tipo. Nenhum save conferia assinatura de conteúdo, MIME, tamanho específico da aplicação ou nomes com caminho; o backend removia apenas diretórios via `Path.name` e chaves repetíveis combinavam hash/nome. O limite efetivo era apenas o teto global do Streamlit. Downloads locais já verificavam contenção sob a raiz; referências R2 não exigiam o prefixo de anexos. A importação administrativa gravava todas as sessões no mesmo `_uploaded_base.xlsx` antes do clique e não tinha cleanup garantido.

## Inventário e políticas

Toda seleção de arquivo usa `policy_extensions(...)`; toda persistência passa novamente por `validate_upload(...)`. O seletor do navegador é conveniência, não fronteira de segurança.

| Superfície | Política | Extensões permitidas | Chave/destino | Download |
|---|---|---|---|---|
| documentos de equipamento/POP complementar | `equipment_document` | PDF, PNG, JPG/JPEG, DOCX, XLSX | `attachments/equipment/...` | local sob raiz ou URL R2 assinada |
| certificado de lote | `certificate` | PDF, PNG, JPG/JPEG, XLSX | `attachments/supply_lot/...` | mesma fronteira |
| FDS/FISPQ/SDS | `safety_document` | PDF, PNG, JPG/JPEG | `attachments/supply/...` | mesma fronteira |
| ficha técnica/caracterização | `technical_document` | PDF, PNG, JPG/JPEG, DOCX, XLSX | `attachments/supply/...` | mesma fronteira |
| comprovante de movimentação | `movement_document` | PDF, PNG, JPG/JPEG, XLSX | `attachments/supply_movement/...` | mesma fronteira |
| evidência corretiva | `maintenance_evidence` | PDF, PNG, JPG/JPEG, MP4, MOV | `attachments/maintenance_corrective/...` | mesma fronteira |
| checklist/certificado preventivo | `maintenance_document` | PDF, PNG, JPG/JPEG | `attachments/maintenance_preventive/...` | mesma fronteira |
| importação administrativa | `base_workbook` | XLSX | temporário único sob `LOCAL_WORK_ROOT/imports/...` | não publicado |

Não há outro picker genérico. Campos de link/arquivo legado não são uploads novos e permanecem limitados a `assets/pops` ou ao histórico `data/uploads` para leitura local.

## Validação

A fronteira central:

- normaliza o nome com Unicode NFKC;
- rejeita vazio, controles, `/`, `\`, absoluto POSIX/Windows, drive, `..` e nome acima de 180 caracteres;
- rejeita extensões não listadas e segmentos de dupla extensão perigosos (`exe`, scripts, HTML/SVG, instaladores e archives, entre outros);
- confere MIME declarado quando fornecido;
- confere assinatura simples de PDF, PNG, JPEG, MP4/MOV e estrutura OOXML ZIP com `[Content_Types].xml` e diretório `xl/` ou `word/`;
- rejeita vazio e conteúdo que contradiz extensão/tipo.

Isso bloqueia disfarces triviais, mas não substitui análise de malware. Se a UFRN exigir antivírus/CDR, integrar como controle separado antes do go-live, sem tratar a validação atual como scanner.

## Tamanho, nomes e armazenamento

`LABCIM_UPLOAD_MAX_BYTES` tem default de 25 MiB e aceita 1–50 MiB. O app valida o limite antes de criar o registro de domínio e novamente antes de armazenar. O Streamlit mantém teto global de 50 MB; configure-o maior ou igual ao limite da aplicação e alinhe o Nginx.

O nome original só vira metadata de apresentação depois de sanitizado. A chave real é gerada no servidor:

```text
attachments/<entidade>/<id>/<ano>/<mês>/<sha256>_<uuid>_<nome-seguro>
```

O UUID impede overwrite mesmo com entidade, nome e bytes idênticos. Não renomear objetos históricos em M1C.

Backend local resolve a chave e exige que o caminho permaneça sob `LOCAL_STORAGE_ROOT`. R2 aceita leitura/URL assinada somente para chaves relativas no namespace `attachments/`, sem barras invertidas ou componentes `.`/`..`. Uma referência adulterada no banco não permite leitura local arbitrária nem outro prefixo do bucket.

## Importação administrativa

O XLSX é validado somente após clique explícito por Administrador. Cada execução recebe diretório UUID sob `LOCAL_WORK_ROOT/imports`, criado sem reutilização; sessões concorrentes não compartilham `_uploaded_base.xlsx`. O diretório é removido em `finally`, inclusive após erro ou rerun. A importação também falha fechada diante de identidades de e-mail históricas ambíguas.

## Operação e limitações

- Validar em staging os formatos reais produzidos pelos equipamentos, navegadores e Office/LibreOffice.
- Confirmar permissões, quota, atomicidade/backup local ou políticas/credenciais R2.
- Testar arquivos próximos ao limite por Nginx, WebSocket, Streamlit e aplicação.
- Backups devem tratar banco e bytes como conjunto lógico; executar restore e reconciliar SHA-256/amostras.
- Conteúdo macro-enabled, executável, SVG e archives não é aceito. Solicitação de novo formato requer revisão de risco, assinatura e caso operacional antes de alterar a política.

Mensagens ao usuário são concisas. Logs não incluem bytes, URLs assinadas ou secrets; falhas internas usam referência opaca.
