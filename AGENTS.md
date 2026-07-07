# LabCim Manager — instruções para agentes

## Contexto do projeto
O LabCim Manager é um app Streamlit em Python para gestão operacional do LabCim. O objetivo do sistema é ser simples, rastreável e pouco burocrático.

## Princípios
- Priorizar simplicidade operacional.
- Não implementar funcionalidades fora do escopo da tarefa.
- Não aumentar burocracia sem justificativa clara.
- Preservar rastreabilidade de dados.
- Evitar exclusões definitivas quando cancelamento/inativação for mais seguro.

## Banco de dados
- SQLite deve ser usado apenas para desenvolvimento local.
- PostgreSQL deve ser usado em produção apenas via DATABASE_URL.
- Nunca colocar DATABASE_URL real, senha, token ou secret no código.
- Nunca versionar data/labcim_manager.db.
- Não recriar tabelas com perda de dados.
- Não apagar dados existentes.
- LabCim_Base.xlsx deve ser usado apenas como seed inicial quando o banco operacional estiver vazio.

## Validação mínima
Depois de alterações em código Python, rodar:
python -m compileall app.py labcim_manager

Quando houver mudanças em banco de dados, verificar pelo menos:
- criação/leitura de usuário;
- criação/leitura de reserva;
- criação/leitura de insumo ou movimento de insumo;
- table_counts;
- importação inicial da base quando aplicável.

## Entrega
Antes de concluir uma tarefa, resumir:
- arquivos alterados;
- comandos executados;
- resultado dos comandos;
- riscos restantes;
- como testar manualmente.
