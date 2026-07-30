# LabCim Manager v7.4

Versão com documentação operacional/POP dos instrumentos.

## Implementações

- Campo `Localização` adicionado à atualização operacional do equipamento.
- Novos campos de documentação operacional:
  - Título do POP
  - Arquivo/link do POP
  - Versão do POP
  - Data de atualização do POP
  - Responsável pelo POP
  - Observações documentais
- Botão para baixar o POP na página de reservas.
- Botão para baixar o POP na página de equipamentos.
- Biblioteca de POPs disponíveis em `assets/pops`.
- Suporte a arquivo PDF local e link externo.
- Banco inicial atualizado com POPs associados a:
  - AUT01 — Autoclave
  - UCA01 — UCA
  - CP01–CP05 — Consistômetros pressurizados
  - FP01–FP02 — Filtros prensa
  - REO01–REO04 — Reômetros
- POPs não associados ainda permanecem disponíveis na biblioteca:
  - Banho termostático
  - Consistômetro atmosférico

## Como rodar

```powershell
pip install -r requirements.txt
streamlit run app.py
```

