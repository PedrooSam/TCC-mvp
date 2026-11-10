# MVP Gestão de Projetos (multitenant)

API de gestão de projetos e tarefas usada no TCC para comparar três estratégias de multitenancy no PostgreSQL:

- **`database`**: um banco por tenant.
- **`schema`**: um schema por tenant, no mesmo banco.
- **`shared`**: tabelas compartilhadas, separadas pela coluna `tenant_id`.

A estratégia é escolhida pela variável de ambiente `TENANT_STRATEGY`. As rotas e os modelos são os mesmos nas três, e só a camada de banco ([app/db.py](app/db.py)) muda de comportamento.

## Stack

- Python 3.10+
- FastAPI + Uvicorn
- SQLAlchemy 2.0
- PostgreSQL (driver `psycopg2`)

## Como rodar

### 1. Subir o PostgreSQL

Com Docker:

```bash
docker run --name tcc-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=app -p 5432:5432 -d postgres:16
```

Se o Postgres já estiver instalado, crie o banco base:

```sql
CREATE DATABASE app;
```

### 2. Instalar as dependências

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar (opcional)

As configurações são lidas do ambiente. O projeto não carrega arquivo `.env`.

| Variável | Padrão | Descrição |
|---|---|---|
| `TENANT_STRATEGY` | `shared` | `database`, `schema` ou `shared` |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/app` | Banco base. Na estratégia `database`, também é usado como referência de host e credenciais. |
| `POOL_SIZE` | `5` | Tamanho do pool de conexões de cada engine |

```powershell
$env:TENANT_STRATEGY = "schema"   # Linux/macOS: export TENANT_STRATEGY=schema
```

### 4. Iniciar a API

Na raiz do repositório:

```bash
uvicorn app.main:app --reload
```

A documentação interativa fica em http://localhost:8000/docs.

## Usando a API

Toda requisição precisa do header **`X-Tenant-ID`**, com letras minúsculas, números ou `_` e até 32 caracteres.

```bash
curl -X POST http://localhost:8000/projects \
  -H "X-Tenant-ID: empresa_a" -H "Content-Type: application/json" \
  -d '{"name": "Projeto 1"}'

curl http://localhost:8000/projects -H "X-Tenant-ID: empresa_a"
```

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/projects` | Cria um projeto |
| `GET` | `/projects` | Lista projetos (`limit`, `offset`) |
| `GET` | `/projects/{id}` | Detalha um projeto, com suas tarefas |
| `PUT` | `/projects/{id}` | Atualiza um projeto |
| `DELETE` | `/projects/{id}` | Remove um projeto e suas tarefas |
| `POST` | `/projects/{id}/tasks` | Cria uma tarefa no projeto |
| `GET` | `/projects/{id}/tasks` | Lista as tarefas do projeto (`limit`, `offset`) |
| `GET` | `/tasks/{id}` | Detalha uma tarefa |
| `PUT` | `/tasks/{id}` | Atualiza uma tarefa |
| `DELETE` | `/tasks/{id}` | Remove uma tarefa |

## Estrutura

```
app/
├── config.py   # Variáveis de ambiente
├── models.py   # Modelos Project e Task (+ TenantMixin)
├── db.py       # Estratégias de multitenancy e get_session()
└── main.py     # Rotas da API
```

## Como as estratégias funcionam

Na primeira requisição de cada tenant, `_provision()` em [app/db.py](app/db.py) cria a estrutura necessária e guarda a engine em cache. Não é preciso rodar nenhum script para criar tabelas.

| | `database` | `schema` | `shared` |
|---|---|---|---|
| Criado na 1ª requisição | Banco `tenant_<id>` + tabelas | Schema `tenant_<id>` + tabelas | Tabelas, uma única vez |
| Como isola | Banco separado, com engine e pool próprios | `schema_translate_map` sobre uma engine compartilhada | Filtro automático por `tenant_id` nos SELECTs do ORM e preenchimento no INSERT |
| Isolamento | Físico | Lógico (namespace) | Apenas na aplicação |
| Conexões | Um pool por tenant | Pool único | Pool único |

## Limitações conhecidas

- **Migrations:** as tabelas são criadas com `create_all`, que não altera tabelas existentes. Depois de mudar um modelo, recrie o banco.
- **Troca de estratégia:** a coluna `tenant_id` só existe na `shared`. Para alternar entre estratégias, recrie o banco `app` ou use um banco base diferente para cada uma.
- **`database`:** cada tenant abre até `POOL_SIZE` conexões, então muitos tenants ativos podem esgotar o `max_connections` do Postgres (100 por padrão). O usuário do banco precisa da permissão `CREATEDB`.
- **`shared`:** o filtro por tenant cobre apenas SELECTs feitos pelo ORM. SQL puro (`text()`) e `update()`/`delete()` em massa não são filtrados.
- **Remoção de tenants:** não há rotina para remover um tenant. Isso é feito manualmente, com `DROP DATABASE` ou `DROP SCHEMA ... CASCADE`.
