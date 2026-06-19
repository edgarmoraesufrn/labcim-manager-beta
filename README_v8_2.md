# LabCim Manager v8.2

Versão com módulo de relatórios semestrais e anuais.

## Implementações

- Nova página `Relatórios`.
- Relatórios por:
  - semestre atual;
  - semestre anterior;
  - ano atual;
  - ano anterior;
  - semestre específico;
  - ano específico;
  - intervalo personalizado.
- Indicadores consolidados:
  - reservas registradas, concluídas e canceladas;
  - amostras previstas/registradas;
  - horas reservadas;
  - equipamentos utilizados;
  - usuários solicitantes;
  - preventivas/calibrações;
  - tickets corretivos;
  - downtime corretivo;
  - movimentações de insumos;
  - saídas/consumo de insumos;
  - insumos em alerta.
- Gráficos de apoio:
  - reservas por mês;
  - equipamentos mais utilizados;
  - reservas por status;
  - preventivas por status;
  - movimentações de insumos por tipo.
- Ranking de responsáveis/executantes.
- Alertas de estoque e validade no relatório.
- Tabelas auditáveis para reservas, manutenção, insumos, estoque e equipamentos.
- Exportação do relatório completo em Excel, com abas separadas.
- Exportação individual de tabelas em CSV.

## Como rodar

```powershell
pip install -r requirements.txt
streamlit run app.py
```

