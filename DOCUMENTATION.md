# Saga Express - Documentação Completa

## Visão Geral

**Saga Express** é um motor de orquestração de SAGAs distribuídas baseado em YAML, construído com FastAPI, SQLAlchemy e suporte para Kafka/Redpanda. O sistema permite definir workflows complexos de microserviços com rollback automático em caso de falhas.

## Arquitetura

### Componentes Principais

1. **API REST (FastAPI)**: Interface para gerenciar configurações de SAGAs e executar workflows
2. **Saga Executor**: Engine que interpreta YAMLs e executa steps sequencialmente
3. **PostgreSQL**: Armazena configurações de SAGAs e histórico de execuções
4. **Redpanda/Kafka**: Suporte para steps assíncronos via mensageria
5. **Alembic**: Gerenciamento de migrations do banco de dados

### Estrutura do Projeto

```
saga-express/
├── app/
│   ├── api/                    # Endpoints REST
│   │   ├── saga_configuration.py
│   │   └── saga_execution.py
│   ├── core/                   # Configurações centrais
│   │   ├── config.py
│   │   └── database.py
│   ├── models/                 # Modelos SQLAlchemy
│   │   ├── saga_configuration.py
│   │   └── saga_execution.py
│   ├── schemas/                # Schemas Pydantic
│   │   ├── saga_configuration.py
│   │   └── saga_execution.py
│   ├── services/               # Lógica de negócio
│   │   └── saga_executor.py
│   └── main.py                 # Aplicação FastAPI
├── alembic/                    # Migrations
├── mock_services/              # Serviços mock para testes
│   ├── order_service.py
│   ├── inventory_service.py
│   └── payment_service.py
├── docker-compose.yml          # Orquestração de containers
├── Dockerfile                  # Imagem da aplicação
├── pyproject.toml              # Dependências (uv)
└── README.md
```

## Funcionalidades

### 1. CRUD de Saga Configurations

#### Criar Configuração
```bash
POST /api/v1/saga-configurations/
Content-Type: application/json

{
  "name": "order-processing-saga",
  "version": "1.0.0",
  "description": "SAGA para processamento de pedidos",
  "yaml_content": "<conteúdo YAML>"
}
```

#### Listar Configurações
```bash
GET /api/v1/saga-configurations/
```

#### Obter Configuração Específica
```bash
GET /api/v1/saga-configurations/{id}
```

#### Atualizar Configuração
```bash
PUT /api/v1/saga-configurations/{id}
Content-Type: application/json

{
  "description": "Nova descrição",
  "yaml_content": "<novo YAML>"
}
```

#### Deletar Configuração
```bash
DELETE /api/v1/saga-configurations/{id}
```

### 2. Enable/Disable Saga Configuration

#### Habilitar
```bash
POST /api/v1/saga-configurations/{id}/enable
```

#### Desabilitar
```bash
POST /api/v1/saga-configurations/{id}/disable
```

### 3. Testar Saga Configuration

```bash
POST /api/v1/saga-executions/test
Content-Type: application/json

{
  "saga_configuration_id": 1,
  "input_data": {
    "order_id": "ORDER-123",
    "customer_id": "CUST-456",
    "items": [
      {"item_id": "ITEM-1", "quantity": 2, "price": 50.0}
    ]
  }
}
```

### 4. Gerenciamento de Execuções

#### Listar Execuções
```bash
GET /api/v1/saga-executions/
```

#### Obter Detalhes da Execução
```bash
GET /api/v1/saga-executions/{id}
```

#### Deletar Execução
```bash
DELETE /api/v1/saga-executions/{id}
```

## Formato YAML da Saga

### Estrutura Básica

```yaml
apiVersion: saga/v1
kind: SagaConfiguration
metadata:
  name: example-saga
  version: "1.0.0"
  description: "Descrição da SAGA"

webhook:
  path: "/saga/example"
  method: POST
  authentication:
    type: none
  timeout: 30s

executions:
  - name: step-1
    type: api  # ou kafka
    endpoint:
      url: "http://service:8000/endpoint"
      method: POST
      headers:
        Content-Type: "application/json"
    body:
      field: "${webhook.input_field}"
    success:
      condition: "response.status == 200"
      extract:
        result_id: "response.body.id"
    error:
      condition: "response.status != 200"
      rollback:
        type: api
        endpoint:
          url: "http://service:8000/rollback"
          method: DELETE
        body:
          id: "${step-1.result_id}"
    timeout: 10s

saga_config:
  rollback_strategy: sequential
  global_timeout: 120s
```

### Tipos de Steps

#### API Step
```yaml
- name: api-step
  type: api
  endpoint:
    url: "http://service:8000/action"
    method: POST
    headers:
      Authorization: "Bearer ${env.TOKEN}"
  body:
    data: "${webhook.data}"
  success:
    condition: "response.status == 200"
    extract:
      result: "response.body.result"
  error:
    condition: "response.status != 200"
    rollback:
      type: api
      endpoint:
        url: "http://service:8000/undo"
        method: POST
```

#### Kafka Step
```yaml
- name: kafka-step
  type: kafka
  endpoint:
    topic: "events.topic"
    partition_key: "${webhook.id}"
    headers:
      event-type: "order.created"
  body:
    event_type: "ORDER_CREATED"
    order_id: "${previous-step.order_id}"
    timestamp: "${current_timestamp}"
  success:
    condition: "kafka.ack_received == true"
  error:
    condition: "kafka.ack_received == false"
    rollback:
      type: kafka
      endpoint:
        topic: "events.topic"
      body:
        event_type: "ORDER_CANCELLED"
```

### Interpolação de Variáveis

O sistema suporta interpolação de variáveis usando a sintaxe `${path.to.value}`:

- `${webhook.field}`: Dados de entrada
- `${step-name.field}`: Dados de steps anteriores
- `${step-name.response.body.field}`: Response de API calls
- `${current_timestamp}`: Timestamp atual
- `${env.VAR_NAME}`: Variáveis de ambiente

### Condições

Suporta comparações simples e compostas:

```yaml
# Simples
condition: "response.status == 200"

# Composta (AND)
condition: "response.status == 200 && response.body.valid == true"

# Composta (OR)
condition: "response.status == 200 || response.status == 201"
```

### Rollback

O rollback é executado em ordem reversa quando um step falha:

1. **sequential**: Executa rollbacks um por vez (padrão)
2. **parallel**: Executa todos rollbacks em paralelo

```yaml
saga_config:
  rollback_strategy: sequential
  global_timeout: 120s
```

## Banco de Dados

### Tabelas

#### saga_configurations
- `id`: Primary key
- `name`: Nome único da configuração
- `version`: Versão da configuração
- `description`: Descrição
- `yaml_content`: Conteúdo YAML completo
- `status`: active | disabled
- `created_at`: Data de criação
- `updated_at`: Data de atualização

#### saga_executions
- `id`: Primary key
- `saga_configuration_id`: Foreign key
- `correlation_id`: UUID único da execução
- `status`: pending | running | completed | failed | rolled_back
- `input_data`: JSON com dados de entrada
- `output_data`: JSON com dados de saída
- `error_message`: Mensagem de erro (se houver)
- `started_at`: Início da execução
- `completed_at`: Fim da execução

#### saga_execution_steps
- `id`: Primary key
- `saga_execution_id`: Foreign key
- `step_name`: Nome do step
- `step_type`: api | kafka
- `status`: pending | running | completed | failed | rolled_back | skipped
- `request_data`: JSON com dados da requisição
- `response_data`: JSON com dados da resposta
- `error_message`: Mensagem de erro (se houver)
- `started_at`: Início do step
- `completed_at`: Fim do step

## Instalação e Execução

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Redpanda/Kafka (opcional, para steps Kafka)
- Docker e Docker Compose (para ambiente completo)

### Setup Local

```bash
# Clonar repositório
cd saga-express

# Criar ambiente virtual com uv
uv venv
source .venv/bin/activate

# Instalar dependências
uv pip install -e .

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações

# Executar migrations
alembic upgrade head

# Iniciar aplicação
uvicorn app.main:app --reload
```

### Docker Compose

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f saga-express

# Parar serviços
docker-compose down
```

## Testes

### Executar Suite de Testes

```bash
# Teste básico de APIs
uv run python examples/test_saga.py

# Teste completo com serviços mock
uv run python examples/ test_saga_full.py

# Teste final simplificado
uv run python examples/ test_saga_final.py
```

### Serviços Mock

O projeto inclui 3 serviços mock para testes:

1. **Order Service** (porta 8001): Valida pedidos
2. **Inventory Service** (porta 8002): Gerencia estoque
3. **Payment Service** (porta 8003): Processa pagamentos

```bash
# Iniciar serviços mock manualmente
cd mock_services
uv run uvicorn order_service.py --host 0.0.0.0 --port 8001 --reload &
uv run uvicorn inventory_service.py --host 0.0.0.0 --port 8001 --reload &
uv run uvicorn payment_service.py --host 0.0.0.0 --port 8001 --reload &
```

## Monitoramento

### Health Check

```bash
GET /health
```

### Métricas

A aplicação expõe métricas básicas:

- Total de configurações ativas
- Total de execuções
- Taxa de sucesso/falha
- Tempo médio de execução

### Logs

Logs são gravados em:
- Console (desenvolvimento)
- Arquivo `server.log` (produção)

## Segurança

### Autenticação

O sistema suporta múltiplos tipos de autenticação para webhooks:

- `none`: Sem autenticação
- `bearer`: Token Bearer
- `basic`: Basic Auth
- `api-key`: API Key customizada

### Secrets

Secrets podem ser referenciados no YAML:

```yaml
headers:
  Authorization: "Bearer ${env.API_TOKEN}"
```

## Troubleshooting

### Problema: Execução falha com "Name or service not known"

**Solução**: Verificar se os serviços estão acessíveis. Em Docker, usar nomes de serviço. Localmente, usar `localhost`.

### Problema: Rollback não é executado

**Solução**: Verificar se o step tem configuração de `rollback` definida no YAML.

### Problema: Variáveis não são interpoladas

**Solução**: Verificar sintaxe `${path.to.value}` e se o valor existe no contexto.

### Problema: Kafka step falha

**Solução**: Verificar se Redpanda/Kafka está rodando e acessível.

## Roadmap

- [ ] Suporte para steps paralelos
- [ ] Interface web para gerenciamento
- [ ] Retry automático configurável
- [ ] Métricas avançadas (Prometheus)
- [ ] Tracing distribuído (Jaeger)
- [ ] Webhooks para notificações
- [ ] Suporte para mais tipos de autenticação
- [ ] Agendamento de execuções
- [ ] Versionamento de configurações
