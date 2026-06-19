# LabCim Manager v7

Versão com agenda em calendário visual e base inicial construída a partir da `LabCim_Base_v3.xlsx`.

## O que entrou nesta versão

- Calendário semanal visual na página de reservas.
- Calendário mensal visual na página de reservas.
- Agenda linear preservada como visual técnico complementar.
- Eventos de reserva e manutenção aparecem no mesmo calendário.
- Manutenções preventivas/calibrações bloqueantes aparecem como eventos de manutenção.
- Reservas canceladas podem ser exibidas ou ocultadas por filtro.
- Cores visuais por tipo/status:
  - reserva agendada;
  - reserva concluída;
  - reserva cancelada;
  - manutenção/calibração;
  - equipamento em uso restrito.
- `data/LabCim_Base.xlsx` atualizado com a base v3.
- `data/labcim_manager.db` criado a partir da nova base.
- Importador atualizado para ler cabeçalhos no padrão `Nome amigável (campo_do_banco)`.
- Importador atualizado para carregar os novos campos operacionais de equipamentos:
  - status operacional;
  - funcionalidades indisponíveis;
  - capacidade máxima;
  - unidade da capacidade;
  - bloqueio acima da capacidade;
  - gestor técnico.
- Importador atualizado para carregar observações de usuários e projetos.

## Base inicial incluída

- 25 equipamentos.
- 37 usuários.
- 11 projetos.
- MEV01 como uso restrito por EDS temporariamente indisponível.
- CC01 com capacidade máxima de 12 corpos de prova.
- MEV01 com capacidade máxima de 7 amostras.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

No Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Observação

O banco SQLite inicial já está em `data/labcim_manager.db`. Se quiser recriar o banco do zero, apague esse arquivo e rode o app novamente; ele importará `data/LabCim_Base.xlsx` automaticamente.

