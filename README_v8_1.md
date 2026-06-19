# LabCim Manager v8.1

Versão com QR Codes para insumos e melhoria dos QR Codes de equipamentos.

## Implementações

- Página `QR Codes` reorganizada em duas abas:
  - Equipamentos
  - Insumos
- QR Codes de equipamentos:
  - Reserva / agenda
  - Manutenção / suporte
  - POP / documentação operacional, quando houver POP cadastrado
- QR Codes de insumos:
  - Ficha rápida do insumo
  - Saldo atual
  - Lote
  - Validade
  - Localização
  - Responsável
  - Acesso a FDS/FISPQ e ficha técnica quando cadastradas
- Leitura de QR de insumo via URL:
  - `?view=insumo&sid=ID_DO_INSUMO`
- Ao abrir um QR de insumo, o sistema mostra a ficha rápida e orienta o usuário a usar a aba de movimentação.
- ZIP com todos os QR Codes de equipamentos.
- ZIP com todos os QR Codes de insumos.

## Como rodar

```powershell
pip install -r requirements.txt
streamlit run app.py
```

