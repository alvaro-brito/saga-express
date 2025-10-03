# Saga Express

 **Motor de orquestração de SAGAs distribuídas** baseado em YAML, construído com FastAPI, SQLAlchemy e suporte para Kafka/Redpanda.

##  Objetivo

Soluçao criada para resolver o problema de transações distribuidas utilizando Saga Design Pattern, dentro do ecosistema de microserviços de forma simples e com baixo recurso computacional.

##  Features

-  **CRUD completo** para configurações de SAGA
-  **Definições YAML** intuitivas e poderosas
-  **Rollback automático** em caso de falhas
-  **Suporte para API** e **Kafka/Redpanda**
-  **Histórico completo** de execuções
-  **Interpolação de variáveis** entre steps
-  **Múltiplos tipos de autenticação**
-  **Docker Compose** pronto para produção

##  Arquitetura

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   FastAPI   │─────▶│ Saga Executor│─────▶│ PostgreSQL  │
│     API     │      │    Engine    │      │  Database   │
└─────────────┘      └──────────────┘      └─────────────┘
       │                     │
       │                     ▼
       │              ┌─────────────┐
       │              │  Redpanda/  │
       └─────────────▶│    Kafka    │
                      └─────────────┘
```

##  Quick Start

### Com Docker Compose (Recomendado)

```bash
# Iniciar todos os serviços
docker-compose up -d

# Verificar status
curl http://localhost:8000/health

# Acessar Redpanda Console
open http://localhost:8080
```

### Setup Local

```bash
# Criar ambiente virtual com uv
uv venv
source .venv/bin/activate

# Instalar dependências
uv pip install -e .

# Configurar banco de dados
export DATABASE_URL="postgresql://saga_user:saga_password@localhost:5432/saga_db"

# Executar migrations
alembic upgrade head

# Iniciar aplicação
uvicorn app.main:app --reload
```

##  Uso Básico

### 1. Criar uma Configuração de SAGA

```bash
curl -X POST http://localhost:8000/api/v1/saga-configurations/ \
  -H "Content-Type: application/json" \
  -d @examples/test_saga_config.yaml
```

### 2. Listar Configurações

```bash
curl http://localhost:8000/api/v1/saga-configurations/
```

### 3. Executar uma SAGA

```bash
curl -X POST http://localhost:8000/api/v1/saga-executions/test \
  -H "Content-Type: application/json" \
  -d '{
    "saga_configuration_id": 1,
    "input_data": {
      "order_id": "ORDER-123",
      "customer_id": "CUST-456",
      "items": [
        {"item_id": "ITEM-1", "quantity": 2, "price": 50.0}
      ]
    }
  }'
```

### 4. Verificar Execução

```bash
curl http://localhost:8000/api/v1/saga-executions/1
```

##  Exemplo de YAML

```yaml
apiVersion: saga/v1
kind: SagaConfiguration
metadata:
  name: order-processing-saga
  version: "1.0.0"
  description: "SAGA para processamento de pedidos"

executions:
  # Step 1 - Validar pedido
  - name: validate-order
    type: api
    endpoint:
      url: "http://order-service:8000/validate"
      method: POST
    body:
      order_id: "${webhook.order_id}"
      items: "${webhook.items}"
    success:
      condition: "response.status == 200"
      extract:
        validated_order_id: "response.body.order_id"
        total_amount: "response.body.total_amount"
    timeout: 10s

  # Step 2 - Reservar estoque
  - name: reserve-inventory
    type: api
    endpoint:
      url: "http://inventory-service:8000/reserve"
      method: POST
    body:
      order_id: "${validate-order.validated_order_id}"
      items: "${webhook.items}"
    success:
      condition: "response.status == 200"
      extract:
        reservation_id: "response.body.reservation_id"
    error:
      rollback:
        type: api
        endpoint:
          url: "http://inventory-service:8000/cancel"
          method: DELETE
        body:
          reservation_id: "${reserve-inventory.reservation_id}"
    timeout: 15s

  # Step 3 - Processar pagamento
  - name: process-payment
    type: api
    endpoint:
      url: "http://payment-service:8000/charge"
      method: POST
    body:
      amount: "${validate-order.total_amount}"
      order_id: "${validate-order.validated_order_id}"
    success:
      condition: "response.status == 200"
      extract:
        transaction_id: "response.body.transaction_id"
    error:
      rollback:
        type: api
        endpoint:
          url: "http://payment-service:8000/refund"
          method: POST
        body:
          transaction_id: "${process-payment.transaction_id}"
    timeout: 20s

saga_config:
  rollback_strategy: sequential
  global_timeout: 120s
```

##  Testes

```bash
# Teste básico de APIs
uv run python examples/test_saga.py

# Teste completo com serviços mock
uv run python examples/test_saga_full.py

# Teste final simplificado
uv run python examples/test_saga_final.py
```

##  Documentação

Para documentação completa, consulte [DOCUMENTATION.md](DOCUMENTATION.md).

##  Tecnologias

- **FastAPI** - Framework web moderno e rápido
- **SQLAlchemy** - ORM para Python
- **Alembic** - Migrations de banco de dados
- **PostgreSQL** - Banco de dados relacional
- **Redpanda/Kafka** - Mensageria distribuída
- **Pydantic** - Validação de dados
- **httpx** - Cliente HTTP assíncrono
- **uv** - Gerenciador de pacotes Python

##  Estrutura do Projeto

```
saga-express/
├── app/
│   ├── api/              # Endpoints REST
│   ├── core/             # Configurações
│   ├── models/           # Modelos SQLAlchemy
│   ├── schemas/          # Schemas Pydantic
│   ├── services/         # Lógica de negócio
│   └── main.py           # App FastAPI
├── alembic/              # Migrations
├── mock_services/        # Serviços mock
├── docker-compose.yml    # Orquestração
├── Dockerfile            # Imagem da app
└── pyproject.toml        # Dependências
```