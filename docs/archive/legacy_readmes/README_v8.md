# LabCim Manager v8

Versão com módulo de Insumos/Almoxarifado.

## Implementações

- Nova página `Insumos` no menu principal.
- Cadastro simples de insumos:
  - nome do insumo;
  - nome comercial;
  - fabricante;
  - categoria;
  - estado físico;
  - função/aplicação;
  - modo de adição;
  - unidade de controle;
  - saldo;
  - estoque mínimo;
  - lote;
  - validade;
  - localização;
  - responsável;
  - FDS/FISPQ;
  - ficha técnica/caracterização;
  - dados técnicos opcionais.
- Movimentação de estoque:
  - entrada;
  - saída;
  - descarte;
  - ajuste positivo;
  - ajuste negativo.
- Histórico completo de movimentações.
- Alertas de:
  - estoque baixo;
  - insumo vencido;
  - insumo vencendo em até 60 dias;
  - insumo sem FDS/FISPQ.
- Exportação CSV do estoque e do histórico.
- Painel inicial com contagem de insumos e alertas críticos.

## Filosofia do módulo

O módulo foi desenhado para controle operacional simples, sem burocratizar a rotina do laboratório. O cadastro mínimo permite rastrear o que existe, quanto existe, onde está, quando vence e quem é o responsável. Os campos técnicos e documentais ficam disponíveis para os insumos que exigirem maior rastreabilidade.

## Como rodar

```powershell
pip install -r requirements.txt
streamlit run app.py
```

