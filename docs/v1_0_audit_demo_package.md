# LabCim Manager v1.0 — Pacote de Demonstração para Auditoria EMBRAPII

## 1. Objetivo da demonstração

O objetivo da demonstração é mostrar que o LabCim Manager já existe, está operacional e estrutura governança, rastreabilidade e controle operacional do laboratório. A apresentação não deve ser tratada como teste real ao vivo, nem como momento para cadastrar, remover ou alterar dados.

Mensagem central:

> O LabCim não está apenas executando projetos; está criando infraestrutura própria para gerir, rastrear e escalar sua operação.

## 2. Posicionamento institucional

O LabCim Manager foi desenvolvido internamente para integrar processos operacionais do laboratório em uma camada digital simples e rastreável. A plataforma reduz a dependência de planilhas soltas, mensagens, arquivos locais e memória institucional, fortalecendo a profissionalização da gestão do polo.

Mais do que um aplicativo administrativo, o sistema representa uma camada de governança: conecta equipamentos, documentos, reservas, manutenção, insumos, lotes, projetos, serviços e relatórios em uma cadeia operacional mais clara.

## 3. O que mostrar na auditoria

Roteiro sugerido de 7 a 10 minutos:

1. Tela inicial / Dashboard
   - Objetivo: mostrar que existe uma porta de entrada operacional e uma visão administrativa para gestão.
   - Mensagem: "O sistema separa a experiência operacional do usuário comum da visão de gestão."
   - Evitar: discutir dados sensíveis ou abrir painéis que não foram revisados previamente.

2. Equipamentos
   - Objetivo: mostrar cadastro, status operacional, localização, responsável e documentação associada.
   - Mensagem: "Cada equipamento passa a ter uma ficha operacional rastreável."
   - Evitar: editar status, inativar equipamento ou alterar dados reais.

3. Documentos/POPs
   - Objetivo: demonstrar que documentos operacionais ficam associados ao equipamento.
   - Mensagem: "A documentação sai de pastas soltas e fica conectada ao item operacional."
   - Evitar: upload ao vivo ou abertura de documento confidencial.

4. QR Codes
   - Objetivo: mostrar acesso rápido a reserva, manutenção e documentação.
   - Mensagem: "O QR Code aproxima o sistema do uso diário no laboratório."
   - Evitar: gerar pacotes em massa se isso não for necessário para a demonstração.

5. Reservas
   - Objetivo: mostrar agenda, solicitante, equipamento e histórico de status.
   - Mensagem: "A reserva deixa de ser uma combinação informal e entra em uma trilha rastreável."
   - Evitar: criar, cancelar ou concluir reserva real.

6. Manutenção
   - Objetivo: demonstrar preventiva/corretiva, tickets, histórico e anexos.
   - Mensagem: "Falhas e ações corretivas passam a compor histórico técnico do equipamento."
   - Evitar: alterar status ou inativar registros durante a auditoria.

7. Insumos e lotes
   - Objetivo: mostrar estoque, movimentação, lote, validade e certificado.
   - Mensagem: "O controle de insumos passa a rastrear origem, saldo, validade e consumo."
   - Evitar: cadastrar insumo, fazer entrada, descarte ou ajuste ao vivo.

8. Projetos e serviços/análises
   - Objetivo: mostrar vínculo entre projeto, serviço, reserva e consumo.
   - Mensagem: "O sistema aproxima operação laboratorial e rastreabilidade por projeto."
   - Evitar: abrir projeto confidencial ou dado de parceiro sem revisão.

9. Relatórios e Excel profissional
   - Objetivo: mostrar consolidação institucional e exportação padronizada.
   - Mensagem: "A operação registrada alimenta relatórios de gestão e prestação de contas."
   - Evitar: gerar relatório novo com filtro improvisado; prefira Excel preparado previamente.

10. Fechamento institucional
    - Objetivo: conectar o sistema à maturidade do polo.
    - Mensagem: "A plataforma é uma v1.0 operacional, construída para evoluir com o laboratório."
    - Evitar: prometer funcionalidades ainda não implementadas.

## 4. Roteiro falado sugerido

"Além dos resultados técnicos e de captação, o LabCim vem estruturando sua própria infraestrutura digital de gestão. Esta plataforma organiza processos que antes ficavam distribuídos em planilhas, mensagens e controles locais.

O foco não é substituir a competência técnica do grupo, mas criar rastreabilidade para essa competência. Cada reserva, movimentação, manutenção, documento e relatório passa a fazer parte de uma cadeia rastreável.

Aqui conseguimos ver equipamentos, documentos operacionais, QR Codes, reservas, manutenção, insumos, lotes, projetos, serviços e relatórios em um mesmo ambiente. Isso ajuda a reduzir informalidade, aumenta a previsibilidade da operação e fortalece a governança do laboratório.

A versão 1.0 já está operacional; melhorias como senha individual, dashboards gerenciais avançados e empacotamento mobile estão planejadas para versões futuras. A ideia é evoluir de forma incremental, mantendo simplicidade operacional e rastreabilidade."

## 5. O que não fazer durante a auditoria

- Não criar usuário ao vivo.
- Não pedir código de login ao vivo.
- Não alterar senha.
- Não fazer upload ao vivo.
- Não cadastrar insumo novo.
- Não excluir ou inativar dados.
- Não alterar reserva real.
- Não mexer em permissões.
- Não mostrar secrets.
- Não abrir projeto confidencial.
- Não executar importação de base.
- Não prometer funcionalidade que ainda não existe.

## 6. Dados seguros para demonstração

- Equipamentos com nomes claros.
- Documentos/POPs seguros para exibição.
- QR Code de exemplo.
- Reservas fictícias ou não sensíveis.
- Manutenção de exemplo.
- Insumos/lotes sem informação confidencial.
- Projetos/serviços sem dados sensíveis de parceiros.
- Relatórios com dados revisados.
- Excel exportado previamente.

## 7. Plano A, B e C

Plano A:

- App rodando ao vivo no Streamlit Cloud.
- Sessão já testada antes da apresentação.
- Navegador com abas principais preparadas.

Plano B:

- Screenshots das telas principais, preparados antes da auditoria.
- Sequência de imagens seguindo o roteiro da demonstração.
- Narrativa mantida mesmo sem navegação ao vivo.

Plano C:

- Excel profissional exportado.
- QR Code impresso ou salvo.
- Runbook de produção.
- Release notes v1.0.

## 8. Checklist pré-apresentação

- App abre.
- Login já testado.
- Usuário de demonstração preparado.
- Streamlit Cloud redeployado.
- Neon respondendo.
- R2 respondendo.
- SMTP não será usado ao vivo.
- Navegador já logado ou sessão preparada.
- Internet testada.
- Backup/exportação importante realizada.
- Excel baixado.
- Screenshots preparados.
- QR físico impresso ou salvo.
- Abas sensíveis revisadas.
- Dados confidenciais ocultos.
- Plano B disponível offline.

## 9. Demonstração por perfil

- `member`: operação simples, com foco em reserva, consulta, reporte de problema e saída/consumo de insumos.
- `manager`: gestão operacional, com acesso a equipamentos, manutenção, lotes, projetos, serviços, relatórios e exportações.
- `admin`: governança e permissões, com gestão de usuários e importação.

Recomendação: conduzir a apresentação principalmente como `manager` ou `admin`, porque esses perfis mostram a visão de governança. Se houver tempo, mostrar rapidamente que o `member` tem uma experiência simplificada e menos exposta.

## 10. Mensagem de fechamento

"O desempenho técnico e a captação mostram a força do polo. O LabCim Manager acrescenta uma camada de governança para sustentar esse crescimento: organiza a operação, preserva rastreabilidade e transforma registros do dia a dia em informação de gestão.

Não é um sistema perfeito nem finalizado; é uma v1.0 operacional, construída internamente e preparada para melhoria contínua. O ponto estratégico é que o LabCim está criando infraestrutura própria para executar, rastrear e escalar sua operação, com potencial de se tornar um case nacional de maturidade operacional em laboratório."

## 11. Pendências planejadas para v1.1

- Senha individual com fallback para código volátil.
- Dashboards gerenciais avançados.
- Refinamentos de UX.
- Eventual empacotamento Android/Google Play.
- Treinamento ampliado.

## 12. Checklist pós-auditoria

- Registrar feedback dos auditores.
- Registrar perguntas feitas.
- Registrar telas que geraram mais interesse.
- Registrar eventuais bugs percebidos.
- Decidir prioridades da v1.1.
- Não implementar mudanças sem nova sprint.
