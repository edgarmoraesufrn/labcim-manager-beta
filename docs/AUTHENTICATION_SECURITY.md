# LabCim Manager — segurança da autenticação

Status: controles M1C implementados e testados localmente. A validação de SMTP, cabeçalhos do proxy, PostgreSQL e comportamento concorrente real continua obrigatória em staging autorizado.

## Snapshot anterior ao M1C

O fluxo anterior já gerava seis dígitos com `secrets.randbelow`, mantinha expiração de dez minutos, uso único, invalidava desafios anteriores do mesmo usuário, consumia o desafio em sucesso e guardava autenticação na sessão server-side. A sessão era revalidada pelo ID do usuário e o perfil vinha do banco; query parameters não definiam identidade/perfil.

Os gaps eram: resposta explícita para e-mail inexistente, ausência de limite de solicitação, lookup ambíguo diante de duplicatas normalizadas, hash SHA-256 sem segredo, limite de erro com comportamento difícil de provar, fallback de revalidação por `LIMIT 1`, logs dispersos e uma opção de desenvolvimento que podia exibir OTP após falha SMTP. M1C preserva as propriedades positivas e substitui esses pontos conforme o modelo abaixo.

## Modelo e propriedades

O login continua passwordless por OTP numérico de seis dígitos. A identidade canônica é sempre `lower(trim(email))`; a mesma regra é usada em solicitação, lookup, desafio persistido, verificação, criação/edição de usuário e importação administrativa.

Fluxo:

1. normalizar o endereço e registrar a tentativa persistente por hashes de identidade e origem;
2. aplicar limites na janela, sem consultar antes se a conta existe;
3. procurar exatamente um usuário ativo com a identidade normalizada;
4. quando elegível, invalidar desafios pendentes, gerar o OTP com `secrets.randbelow`, armazenar somente HMAC-SHA-256 do e-mail+OTP e enviar por SMTP;
5. validar somente o desafio ativo mais recente, dentro da validade e abaixo do teto de erros;
6. consumir o desafio em sucesso, expiração, limite de erros ou falha de entrega;
7. criar sessão apenas após sucesso e revalidar usuário ativo e perfil pelo banco a cada rerun autenticado.

A resposta pública à solicitação é sempre: “Se o endereço estiver elegível, um código de acesso será enviado.” Isso vale para identidade conhecida, desconhecida, inativa, ambígua, limitada e falha operacional. A interface não exibe OTP de debug.

## Configuração e limites

| Variável | Default | Intervalo aceito | Efeito |
|---|---:|---:|---|
| `LABCIM_OTP_TTL_SECONDS` | 600 | 60–1800 | validade do desafio |
| `LABCIM_OTP_MAX_VERIFY_ATTEMPTS` | 5 | 3–10 | erros por desafio |
| `LABCIM_OTP_REQUEST_WINDOW_SECONDS` | 900 | 60–86400 | janela móvel de solicitação |
| `LABCIM_OTP_MAX_REQUESTS_PER_WINDOW` | 3 | 1–20 | teto por identidade normalizada |
| `LABCIM_OTP_MAX_REQUESTS_PER_ORIGIN` | 20 | 1–200 | teto suplementar por origem disponível |
| `LABCIM_OTP_GLOBAL_MAX_REQUESTS` | 100 | 10–2000 | teto global por instância/banco |
| `LABCIM_OTP_HASH_SECRET` | cookie secret | segredo | HMAC dos OTPs |

Em staging/produção é obrigatório configurar `LABCIM_OTP_HASH_SECRET` ou `STREAMLIT_SERVER_COOKIE_SECRET`, com pelo menos 32 caracteres. Valor inválido ou segredo ausente impede o startup antes da conexão ao banco. Os limites usam `auth_rate_limit_events`, migration v3, e portanto sobrevivem a reruns e sessões do Streamlit. Eventos antigos são descartados após sete dias no momento de nova solicitação.

A dimensão de origem lê `X-Forwarded-For`/`X-Real-IP`; ela só é confiável quando o proxy institucional remove valores do cliente e define seus próprios cabeçalhos. Mesmo sem origem confiável, os tetos por identidade e global permanecem ativos. Redis não é necessário no desenho inicial de uma instância.

## Duplicatas e operação

Não há normalização destrutiva nem merge automático de usuários existentes. Duas ou mais linhas com o mesmo `lower(trim(email))` tornam aquela identidade ambígua: nenhuma recebe OTP. Novos usuários e alterações com identidade já ocupada são recusados; a importação administrativa também recusa iniciar se houver conflito histórico.

Diagnóstico seguro:

```bash
python -m labcim_manager.db_migrate diagnose-email-identities
```

O comando informa referências hash, IDs e quantidade ativa, sem imprimir endereços. Para resolução, um administrador autorizado pode consultar no console restrito:

```sql
SELECT LOWER(TRIM(email)) AS normalized_email,
       COUNT(*) AS user_count,
       SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS active_count
FROM users
WHERE email IS NOT NULL AND TRIM(email) <> ''
GROUP BY LOWER(TRIM(email))
HAVING COUNT(*) > 1
ORDER BY LOWER(TRIM(email));
```

Preservar backup, confirmar com responsáveis e corrigir explicitamente cada cadastro. Não criar índice único sobre dados reais antes de o diagnóstico retornar zero; M1C não reescreve dados históricos.

## SMTP, sessão e logs

Cada clique aceito conta antes da elegibilidade e do SMTP, reduzindo abuso inclusive com endereços desconhecidos. Falha SMTP consome o desafio e mantém resposta neutra. Erros usam referência opaca; stack traces ficam apenas no log do servidor. Eventos estruturados contêm referência, tipo, timestamp do logger, hash truncado da identidade/origem, resultado e motivo. Nunca contêm OTP, senha SMTP ou string de conexão.

O sucesso mantém somente `auth_user` com ID, nome, e-mail e perfil autoritativo. Logout remove autenticação, perfil legado, endereço pendente e campos de código/login. Query parameters fornecem apenas dicas de navegação; não estabelecem identidade nem perfil.

## Limitações e troubleshooting

- O OTP tem seis dígitos; os controles compensatórios são validade curta, teto de cinco erros, uso único e throttling.
- Os timestamps existentes são texto local ingênuo; manter `TZ=America/Fortaleza` até uma migration futura aprovada.
- O teto global é compartilhado por todas as solicitações e pode exigir ajuste institucional após observar staging.
- Uma corrida extrema de criação de usuários deve ser reavaliada antes de múltiplas instâncias; a primeira implantação é de instância única.
- Confirmar em staging: entrega/latência SMTP, invalidation após falha, restart, concorrência PostgreSQL, cabeçalho de origem sob Nginx e ausência de enumeração por timing perceptível.

Em incidentes, procurar `security_event reference=...`, consultar resultados agregados em `auth_rate_limit_events` e `notification_log`, nunca solicitar ao usuário o OTP nem copiar secrets para tickets.
