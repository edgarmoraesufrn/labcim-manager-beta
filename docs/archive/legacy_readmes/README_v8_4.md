# LabCim Manager v8.4

Versão com perfil `manager` e base `LabCim_Base_v4.xlsx`.

## Implementações

- Perfil intermediário alterado de `operator` para `manager`.
- Rótulo do perfil intermediário alterado para `Gerente`.
- Compatibilidade automática:
  - usuários antigos com `operator`, `operador` ou `gerente` são convertidos para `manager`.
- Permissões atualizadas:
  - `member`: pode agendar, relatar manutenção e movimentar estoque de insumos;
  - `manager`: pode fazer tudo que o membro faz e também cadastrar/editar equipamentos, usuários, projetos e cadastros estruturais;
  - `admin`: acesso completo.
- Cadastro estrutural de insumos restringido a `manager`/`admin`.
- Movimentação de estoque liberada para membros.
- Importador da base melhorado:
  - evita duplicação de usuários ao reimportar;
  - atualiza usuários por e-mail, telefone ou nome;
  - atualiza projetos por código ou nome;
  - normaliza perfis de acesso;
  - converte telefones numéricos da planilha para texto sem `.0`.
- Base atualizada para `LabCim_Base_v4.xlsx`.

## Dados importados da v4

- Equipamentos: 25
- Usuários: 40
- Projetos: 11
- Perfis:
  - admin: 4
  - manager: 14
  - member: 22

## Como rodar

```powershell
pip install -r requirements.txt
streamlit run app.py
```

