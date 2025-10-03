# Saga Express - Guia de Início Rápido

##  Objetivo

Este guia vai te ajudar a ter o **Saga Express** rodando em menos de 5 minutos!

##  Pré-requisitos

- Python 3.11+
- PostgreSQL 14+ (ou Docker)
- uv (gerenciador de pacotes Python)

##  Instalação Rápida

### Opção 1: Setup Local (Sem Docker)

```bash
# 1. Extrair o projeto
cd saga-express

# 2. Criar ambiente virtual
uv venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# 3. Instalar dependências
uv pip install -e .

# 4. Configurar PostgreSQL
# Criar banco de dados
sudo -u postgres psql -c "CREATE DATABASE saga_db;"
sudo -u postgres psql -c "CREATE USER saga_user WITH PASSWORD 'saga_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE saga_db TO saga_user;"

# 5. Configurar variáveis de ambiente
export DATABASE_URL="postgresql://saga_user:saga_password@localhost:5432/saga_db"
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"

# 6. Executar migrations
alembic upgrade head

# 7. Iniciar aplicação
uvicorn app.main:app --reload
```

### Opção 2: Docker Compose (Recomendado)

```bash
# 1. Extrair o projeto
cd saga-express

# 2. Iniciar todos os serviços
docker-compose up -d

# 3. Aguardar serviços iniciarem (30 segundos)
sleep 30

# 4. Verificar status
curl http://localhost:8000/health
```

##  Verificar Instalação

```bash
# Health check
curl http://localhost:8000/health

# Resposta esperada:
# {"status":"healthy"}
```

### Opção 3: Docker Compose + saga-express local

## Executar docker somente os componentes necessários

```bash
# 1. Extrair o projeto
cd saga-express

# 2. Iniciar o docker-compose
docker-compose up -d postgres redpanda-0 console

# 3. Aguardar serviços iniciarem (30 segundos)
sleep 30

# 4. Iniciar serviço
./run.sh

```


##  Executar Testes

### Teste 1: APIs Básicas

```bash
uv run python examples/test_saga.py
```

**Resultado esperado:**
```
✓ Health check
✓ Saga configuration created
✓ Found 1 saga configuration(s)
✓ All API tests passed successfully!
```

### Teste 2: Serviços Mock

```bash
# Iniciar serviços mock
cd mock_services
uv run uvicorn order_service.py --host 0.0.0.0 --port 8001 --reload &
uv run uvicorn inventory_service.py --host 0.0.0.0 --port 8001 --reload &
uv run uvicorn payment_service.py --host 0.0.0.0 --port 8001 --reload &
cd ..

# Executar teste completo
uv run examples/test_saga_full.py
```

**Resultado esperado:**
```
✓ Order Service is running
✓ Inventory Service is running
✓ Payment Service is running
✓ SUCCESS - All steps completed!
```

### Teste 3: Teste Simplificado

```bash
uv run python examples/test_saga_final.py
```

**Resultado esperado:**
```
✓ Created saga configuration ID: X
Executing saga...
Status: completed
Steps: 4
  ✓ validate-order: completed
  ✓ reserve-inventory: completed
  ✓ process-payment: completed
  ✓ confirm-inventory: completed
✓ SUCCESS - All steps completed!
```

##  Criar Sua Primeira SAGA

### 1. Criar arquivo YAML

Crie um arquivo `my-saga.yaml`:

```yaml
apiVersion: saga/v1
kind: SagaConfiguration
metadata:
  name: my-first-saga
  version: "1.0.0"
  description: "Minha primeira SAGA"

webhook:
  path: "/saga/my-first"
  method: POST
  authentication:
    type: none
  timeout: 30s

executions:
  - name: step-1
    type: api
    endpoint:
      url: "http://localhost:8001/validate"
      method: POST
      headers:
        Content-Type: "application/json"
    body:
      data: "${webhook.data}"
    success:
      condition: "response.status == 200"
      extract:
        result: "response.body.result"
    timeout: 10s

saga_config:
  rollback_strategy: sequential
  global_timeout: 60s
```

### 2. Criar configuração via API

```bash
# Ler conteúdo do YAML
YAML_CONTENT=$(cat my-saga.yaml)

# Criar configuração
curl -X POST http://localhost:8000/api/v1/saga-configurations/ \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"my-first-saga\",
    \"version\": \"1.0.0\",
    \"description\": \"Minha primeira SAGA\",
    \"yaml_content\": \"$YAML_CONTENT\"
  }"
```

### 3. Executar SAGA

```bash
curl -X POST http://localhost:8000/api/v1/saga-executions/test \
  -H "Content-Type: application/json" \
  -d '{
    "saga_configuration_id": 1,
    "input_data": {
      "data": "test"
    }
  }'
```

### 4. Verificar resultado

```bash
curl http://localhost:8000/api/v1/saga-executions/1
```

##  Próximos Passos

1. **Explorar a API**: Acesse http://localhost:8000/docs para ver a documentação interativa (Swagger UI)

2. **Ler a documentação completa**: Consulte [DOCUMENTATION.md](DOCUMENTATION.md) para entender todos os recursos

3. **Customizar o YAML**: Adicione mais steps, configure rollbacks, use interpolação de variáveis

4. **Integrar com seus serviços**: Substitua os serviços mock pelos seus microserviços reais

5. **Monitorar execuções**: Use as APIs de listagem e detalhamento para acompanhar as execuções

##  Problemas Comuns

### Erro: "Connection refused" ao acessar localhost:8000

**Solução**: Verifique se o servidor está rodando:
```bash
ps aux | grep uvicorn
```

Se não estiver, inicie:
```bash
uvicorn app.main:app --reload
OU
./run.sh
```

### Erro: "Database connection failed"

**Solução**: Verifique se o PostgreSQL está rodando e as credenciais estão corretas:
```bash
sudo systemctl status postgresql
psql -U saga_user -d saga_db -h localhost
```

### Erro: "Module not found"

**Solução**: Certifique-se de que o ambiente virtual está ativado e as dependências instaladas:
```bash
source .venv/bin/activate
uv pip install -e .
```

### Serviços mock não respondem

**Solução**: Verifique se estão rodando nas portas corretas:
```bash
curl http://localhost:8001/
curl http://localhost:8002/
curl http://localhost:8003/
```

Se não estiverem, inicie manualmente:
```bash
cd mock_services
python order_service_8001.py &
python inventory_service_8002.py &
python payment_service_8003.py &
```

##  Suporte

Se encontrar problemas:

1. Verifique os logs: `tail -f server.log`
2. Consulte a [documentação completa](DOCUMENTATION.md)
3. Verifique as issues no repositório
4. Abra uma nova issue com detalhes do problema


