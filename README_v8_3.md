# LabCim Manager v8.3

Versão com cadastro mestre e níveis preliminares de acesso.

## Implementações

- Frase inicial atualizada:
  - `Sistema de Gestão de Estoque, Equipamentos, Reservas e Manutenção do LabCim`
- Perfil de acesso na barra lateral:
  - Membro: consulta e reservas.
  - Operador: atualizações operacionais.
  - Administrador: cadastros estruturais.
- Aba `Equipamentos` reorganizada:
  - Consulta geral para todos.
  - Atualização operacional para operador/administrador.
  - Cadastro mestre para administrador:
    - novo equipamento;
    - editar equipamento existente;
    - status, localização, capacidade, responsável, gestor técnico e POP.
- Aba `Usuários` com cadastro e edição:
  - novo usuário;
  - editar usuário existente;
  - perfil de acesso;
  - vínculo, orientador, treinamento e status ativo.
- Aba `Projetos` com cadastro e edição:
  - novo projeto;
  - editar projeto existente;
  - fonte de financiamento;
  - data de início;
  - data de fim;
  - status ativo.
- Banco de dados atualizado com migrações leves:
  - `projects.start_date`;
  - `projects.end_date`;
  - `projects.updated_at`;
  - `users.updated_at`.

## Observação

O controle de perfil ainda é preliminar e selecionado pela interface. Na próxima etapa, ele deve ser conectado ao login/senha volátil por e-mail ou WhatsApp.

## Como rodar

```powershell
pip install -r requirements.txt
streamlit run app.py
```

