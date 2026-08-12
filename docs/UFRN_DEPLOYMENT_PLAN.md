# LabCim Manager — plano de implantação UFRN

Status: fundação de código M1A preparada; **não executar sem aprovação de uma sprint de implantação**.

Dependência: todos os blockers de `PRODUCTION_READINESS.md` resolvidos em staging.

## 1. Arquitetura alvo

```text
Internet
  -> HTTPS :443
      -> Nginx
          -> / e demais rotas do site
              -> Astro estático, repositório separado
          -> /manager/
              -> Streamlit em 127.0.0.1:8501
                  -> PostgreSQL local por socket/loopback
                  -> storage escolhido e persistente
                  -> SMTP institucional/permitido
```

O Streamlit não deve escutar no IPv4 interno nem em `0.0.0.0`. O repositório do site Astro permanece separado. O Nginx é o único processo Internet-facing.

## 2. Layout recomendado

| Caminho | Finalidade | Dono/permissão sugerida |
|---|---|---|
| `/opt/labcim-manager/releases/<commit>` | código imutável de cada release | `root:labcim-manager`, leitura |
| `/opt/labcim-manager/current` | symlink para release ativa | administrado no deploy |
| `/opt/labcim-manager/venv` | virtualenv da release ou runtime versionado | leitura pelo serviço |
| `/etc/labcim-manager/manager.env` | secrets/config fora do Git | `root:labcim-manager`, `0640` |
| `/var/lib/labcim-manager/uploads` | arquivos locais, se esse backend for escolhido | `labcim-manager:labcim-manager`, `0750` |
| `/var/lib/labcim-manager/work` | temporários controlados de import/export | serviço, com quota/limpeza |
| `/var/backups/labcim-manager` | staging local de backups, se aprovado | acesso administrativo restrito |

O código M1A aceita essa raiz por `STORAGE_BACKEND=local` e `LOCAL_STORAGE_ROOT=/var/lib/labcim-manager/uploads`. Dono, permissões, quota e backup ainda exigem validação no host.

## 3. Usuários e rede

1. Criar usuário de sistema dedicado, sem privilégios administrativos e preferencialmente sem login interativo.
2. Executar Streamlit como esse usuário.
3. Escutar somente `127.0.0.1:8501`.
4. PostgreSQL deve aceitar a aplicação apenas pelo socket Unix ou loopback e por um role sem superuser/createdb/createrole.
5. Firewall deve expor apenas portas institucionais necessárias; nunca 8501 ou 5432 publicamente.
6. SSH continua limitado à rede/VPN UFRN, fora do escopo da aplicação.

## 4. Runtime reproduzível

Antes do staging:

- disponibilizar Python 3.12.13, conforme `.python-version`;
- instalar somente pelo `requirements.txt`, que exige o `requirements.lock` com hashes;
- construir virtualenv limpo;
- executar compile, testes SQLite/PostgreSQL e smoke de startup;
- registrar commit, Python, lock e checksums dos artefatos.

O M1A validou instalação limpa e testes locais com Python 3.12.13. Isso ainda não substitui a homologação no Linux/Ubuntu alvo.

## 5. Configuração Streamlit necessária

Preferir variáveis no `EnvironmentFile`, mantendo configuração não secreta no repositório quando estabilizada:

```text
STREAMLIT_SERVER_ADDRESS=127.0.0.1
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_BASE_URL_PATH=manager
STREAMLIT_SERVER_ENABLE_CORS=true
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=none
```

Definir o mesmo limite de upload em Streamlit e Nginx. Não desabilitar CORS/XSRF para “corrigir” o proxy. TLS termina no Nginx, não no Streamlit.

Também definir `APP_ENV=production`, `APP_BASE_URL=https://labcim.quimica.ufrn.br/manager/`, `DATABASE_URL`, `STORAGE_BACKEND` e as variáveis condicionais do backend escolhido. O contrato completo, com exemplos fictícios, está em `PRODUCTION_ENV_TEMPLATE.md`.

## 6. Unidade systemd — especificação para sprint de implantação

A unidade final deve conter, no mínimo:

- `User=labcim-manager` e `Group=labcim-manager`;
- `WorkingDirectory=/opt/labcim-manager/current`;
- `EnvironmentFile=/etc/labcim-manager/manager.env`;
- `ExecStart` apontando ao `streamlit` do virtualenv e `app.py`;
- `Restart=on-failure` com backoff;
- timeout de parada suficiente para encerrar conexões;
- `UMask=0027`;
- hardening systemd compatível com o acesso necessário;
- `ReadWritePaths` apenas para diretórios persistentes/temporários escolhidos;
- logs em stdout/stderr capturados pelo journald.

Não adicionar `ExecStartPre` que chame `init_db()` enquanto o startup ainda altera schema/dados. Migração deve ser uma etapa administrativa separada, com backup e aprovação.

## 7. Nginx — desenho de referência

O bloco abaixo é um modelo para staging, não um arquivo aplicado:

```nginx
map $http_upgrade $labcim_connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 443 ssl;
    server_name labcim.quimica.ufrn.br;

    root /srv/labcim-site/current;

    location = /manager {
        return 308 /manager/;
    }

    location /manager/ {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $labcim_connection_upgrade;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        client_max_body_size <LIMITE_APROVADO>m;
    }

    location / {
        try_files $uri $uri/ /404.html;
    }
}
```

Com `baseUrlPath=manager`, `proxy_pass` sem URI final preserva `/manager/...` para o upstream. Confirmar esse comportamento no Nginx empacotado pelo Ubuntu alvo. O upgrade explícito é necessário para WebSockets segundo a documentação oficial do Nginx: <https://nginx.org/en/docs/http/websocket.html>.

Não aplicar CSP/HSTS ou headers de frame de forma cega. Streamlit usa iframes para components; testar a política antes de endurecer. HSTS depende da política TLS do domínio institucional inteiro.

## 8. PostgreSQL

- banco e role dedicados;
- senha somente no arquivo de ambiente ou autenticação local aprovada;
- privilégios mínimos após a migração;
- encoding UTF-8 e locale/timezone formalmente definidos;
- acesso externo desabilitado salvo necessidade institucional documentada;
- `statement_timeout`, `idle_in_transaction_session_timeout` e limites de conexão avaliados;
- monitoramento de espaço, conexões, locks, backup e falhas.

O app guarda timestamps como texto sem offset. Até a correção/migração, o processo e a interpretação operacional devem usar `America/Fortaleza` de maneira consistente.

## 9. Storage

Escolher uma opção antes do staging:

### Opção A — filesystem institucional (recomendada se integrado ao backup da VM)

O contrato M1A já externaliza a raiz e permite local com PostgreSQL. Antes de produção ainda é necessário validar escrita, permissões/quota, política de escrita atômica e backup coordenado com PostgreSQL.

### Opção B — manter R2 privado

É selecionável explicitamente e mantém dependência externa, credenciais, egress e URLs assinadas. Confirmar política UFRN, conectividade, residência/retenção e restore coordenado.

Detalhes em `FILE_STORAGE_MIGRATION_PLAN.md`.

## 10. Observabilidade

- journald para stdout/stderr do Streamlit e aplicação;
- erros completos somente no journal, nunca no navegador;
- rotação/limite por política institucional;
- alertas para service down, health check, disco, falha de backup, PostgreSQL e taxa de erro SMTP/storage;
- evitar secrets, OTPs, URLs assinadas e corpos sensíveis nos logs;
- definir retenção do `notification_log` no banco.

O endpoint de health é interno do Streamlit e pode variar por versão. Depois de travar a versão, validar o candidato `/manager/_stcore/health` tanto em loopback como pelo proxy. A documentação atual usa `/_stcore/health` em deploys de referência: <https://docs.streamlit.io/deploy/tutorials/docker>.

## 11. Backup e recuperação

Definir com a equipe UFRN:

- RPO/RTO;
- frequência de `pg_dump`/backup físico;
- criptografia, destino fora da VM e retenção;
- backup incremental/completo dos anexos;
- ordem e consistência lógica entre banco e arquivos;
- monitoramento de jobs e espaço;
- restore periódico em ambiente isolado;
- runbook de perda total da VM.

Nenhum deploy será aprovado apenas porque o backup “rodou”; um restore completo deve ser demonstrado.

## 12. Sequência de implantação

1. **M1A — fundação reproduzível:** runtime, lock, configuração, storage e subpath preparados no repositório.
2. **M1B — banco/startup:** implementar migrações versionadas e remover mutações do startup.
3. **Hardening dedicado:** autenticação pública, uploads e revisão de HTML/erros restantes.
4. **Build reproduzível:** gerar ambiente Linux limpo e SBOM/lista de versões.
5. **Staging isolado:** PostgreSQL e storage sem dados reais ou com cópia sanitizada.
6. **Teste `/manager/`:** executar a matriz de `PRODUCTION_READINESS.md` e perfis `member/manager/admin`.
7. **Ensaio de migração:** backup, carga, reconciliação, restore e rollback.
8. **Revisão institucional:** segurança, DNS/TLS, e-mail, backup e janela de mudança.
9. **Cutover aprovado:** somente em sprint própria, com responsáveis, comunicação e rollback.
10. **Pós-cutover:** smoke funcional, observação de logs/métricas e confirmação de backup.

## 13. Rollback esperado

- manter release anterior imutável;
- não reverter schema por DDL destrutivo durante incidente;
- restaurar banco e storage como conjunto quando houver alteração de dados incompatível;
- voltar symlink/config Nginx apenas com compatibilidade de schema confirmada;
- registrar horário, commit, backup e decisão.

Este documento não autoriza executar qualquer comando na VM.
