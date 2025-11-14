# Sistema de Mensagens Distribuído

Sistema completo de mensagens instantâneas com arquitetura distribuída, replicação de dados, sincronização de relógios e eleição de coordenador.

## 📋 Visão Geral

Este projeto implementa um sistema de mensagens distribuído com as seguintes características:

- ✅ **3 Servidores** com balanceamento de carga (round-robin)
- ✅ **Replicação Total** de dados entre servidores
- ✅ **Pub/Sub** para mensagens em canais e mensagens privadas
- ✅ **Relógio Lógico de Lamport** para ordenação de eventos
- ✅ **Sincronização de Relógio Físico** (Algoritmo de Berkeley)
- ✅ **Eleição de Coordenador** (Algoritmo Bully)
- ✅ **Serialização MessagePack** para eficiência
- ✅ **2 Bots** automatizados para testes
- ✅ **1 Cliente** interativo

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    Cliente / Bots                       │
└───────────────────┬─────────────────────────────────────┘
                    │
             ┌──────▼──────┐
             │   Broker    │ (Round-Robin)
             └──────┬──────┘
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │Server 1 │ │Server 2 │ │Server 3 │
   │(Rank 1) │ │(Rank 2) │ │(Rank 3) │
   └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │
        └───────────┼───────────┘
                    │
             ┌──────▼──────┐
             │    Proxy    │ (Pub/Sub)
             └──────┬──────┘
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   Cliente        Bot 1       Bot 2

        Tópico 'servers'
             ┌──────┐
        ┌────┤Replic├────┐
        ▼    └──────┘    ▼
   Server 1          Server 2,3
```

## 🚀 Início Rápido

### Pré-requisitos

- Docker 20.10+
- Docker Compose 1.29+
- Python 3.8+ (para scripts de gerenciamento)

### Instalação e Inicialização

```bash
# 1. Clone o repositório
git clone <repo-url>
cd sistemas-distribuidos-projeto

# 2. Inicie o sistema (constrói e inicia todos os serviços)
python on.py

# Ou manualmente:
docker-compose up --build
```

### Parar o Sistema

```bash
# Usando script
python off.py

# Ou manualmente
docker-compose down
```

### Verificar Status

```bash
# Ver status completo do sistema
python status.py

# Ver status dos containers
docker-compose ps

# Ver logs de um servidor específico
docker logs -f servidor_1
```

## 📁 Estrutura do Projeto

```
sistemas-distribuidos-projeto/
├── broker/              # Broker (balanceador de carga) - Go
├── proxy/               # Proxy Pub/Sub - Go
├── referencia/          # Servidor de referência - Python
├── servidor/            # Servidores de mensagens - Python
├── cliente/             # Cliente interativo - Node.js
├── bot/                 # Bots automatizados - Node.js
├── data/                # Dados persistidos
│   ├── servidor_1/      # Dados do servidor 1
│   ├── servidor_2/      # Dados do servidor 2
│   └── servidor_3/      # Dados do servidor 3
├── docker-compose.yml   # Configuração dos containers
├── on.py               # Script para iniciar sistema
├── off.py              # Script para parar sistema
├── status.py           # Script para verificar status
└── README.md           # Este arquivo
```

## 🔧 Funcionalidades

### 1. Sistema de Mensagens

- **Login de usuários**: Cadastro e autenticação
- **Canais públicos**: Criação e inscrição em canais
- **Mensagens privadas**: Comunicação direta entre usuários
- **Publicações em canais**: Broadcast para todos inscritos

### 2. Replicação de Dados

- **Replicação Eager**: Propagação imediata de escritas
- **Replicação Total**: Todos os servidores têm todos os dados
- **Sincronização Inicial**: Novos servidores sincronizam ao iniciar
- **Ordenação por Relógio Lógico**: Garante ordem consistente

📖 Veja [REPLICACAO.md](REPLICACAO.md) para detalhes completos.

### 3. Relógios

#### Relógio Lógico (Lamport)
- Implementado em todos os processos
- Incrementado antes de cada envio
- Atualizado ao receber: `max(local, received) + 1`

#### Relógio Físico (Berkeley)
- Coordenador coleta tempos de todos os servidores
- Calcula média e ajusta relógios
- Sincronização a cada 10 mensagens processadas

📖 Veja [PARTE4_RELOGIOS.md](PARTE4_RELOGIOS.md) para detalhes completos.

### 4. Eleição de Coordenador (Bully)

- Baseada em rank (maior rank = prioridade)
- Eleição automática ao iniciar
- Reeleição automática se coordenador falhar
- Anúncio via tópico `servers`

### 5. Servidor de Referência

- Atribui ranks aos servidores
- Mantém lista de servidores ativos
- Recebe heartbeats periódicos
- Remove servidores inativos (>30s sem heartbeat)

## Como Usar

### Iniciar Sistema

```bash
python on.py
```

O script irá:
1. Verificar Docker e Docker Compose
2. Construir imagens (primeira vez demora mais)
3. Iniciar todos os serviços
4. Aguardar serviços ficarem prontos
5. Oferecer opções interativas

### Conectar ao Cliente Interativo

```bash
# Durante inicialização, escolha opção 1
# Ou conecte manualmente:
docker-compose up cliente
```

Menu do cliente:
```
=== Menu ===
1. Listar usuários
2. Criar canal
3. Listar canais
4. Inscrever em canal
5. Publicar em canal
6. Enviar mensagem privada
0. Sair
```

### Testar Replicação

```bash
# 1. Fazer login e criar canal
docker-compose up cliente

# 2. Verificar dados em todos os servidores
cat data/servidor_1/users.json
cat data/servidor_2/users.json
cat data/servidor_3/users.json

```

## 📊 Monitoramento

### Status do Sistema

```bash
python status.py
```

Mostra:
- Status de todos os containers
- Consistência de dados replicados
- Coordenador atual
- Sincronização de relógio
- Atividades recentes

### Verificar Dados Replicados

```bash
# Usuários
cat data/servidor_1/users.json
cat data/servidor_2/users.json
cat data/servidor_3/users.json

# Canais
cat data/servidor_1/channels.json

# Mensagens (ordenadas por clock)
cat data/servidor_1/messages.json | jq '.data.messages | sort_by(.clock)'

# Publicações (ordenadas por clock)
cat data/servidor_1/publications.json | jq '.data.publications | sort_by(.clock)'
```

### Verificar Eleição

```bash
# Ver eleição nos logs
docker logs servidor_3 | grep ELEIÇÃO

# Ver anúncio de coordenador
docker logs servidor_1 | grep "Novo coordenador"
```

### Verificar Sincronização Berkeley

```bash
# Logs do coordenador (coleta tempos)
docker logs servidor_3 | grep BERKELEY

# Logs dos outros servidores (sincronizam)
docker logs servidor_1 | grep SYNC
docker logs servidor_2 | grep SYNC
```

## 🧪 Testes

### Teste 1: Replicação Básica

```bash
# 1. Iniciar sistema
python on.py

# 2. Conectar cliente e fazer login como "teste1"
docker-compose up cliente

# 3. Verificar replicação
cat data/servidor_1/users.json  # Deve ter "teste1"
cat data/servidor_2/users.json  # Deve ter "teste1"
cat data/servidor_3/users.json  # Deve ter "teste1"
```

### Teste 2: Sincronização Inicial

```bash
# 1. Iniciar apenas servidor_1
docker-compose up -d broker proxy referencia servidor_1

# 2. Fazer login e criar dados
docker-compose up cliente

# 3. Iniciar servidor_2
docker-compose up -d servidor_2

# 4. Verificar sincronização
docker logs servidor_2 | grep SYNC
cat data/servidor_2/users.json  # Deve ter dados!
```

### Teste 3: Falha e Recuperação

```bash
# 1. Sistema completo rodando
python on.py

# 2. Criar dados

# 3. Parar servidor_1
docker stop servidor_1

# 4. Criar mais dados (vão para servidor_2 ou servidor_3)

# 5. Reiniciar servidor_1
docker start servidor_1

# 6. Verificar que servidor_1 sincronizou
docker logs servidor_1 | grep SYNC
cat data/servidor_1/users.json  # Deve ter TODOS os dados
```

### Teste 4: Eleição de Coordenador

```bash
# 1. Ver coordenador atual
python status.py

# 2. Parar coordenador (servidor_3)
docker stop servidor_3

# 3. Ver nova eleição
docker logs servidor_2 | grep ELEIÇÃO
# servidor_2 deve se tornar coordenador

# 4. Reiniciar servidor_3
docker start servidor_3
# servidor_3 volta mas servidor_2 continua coordenador
```

## 🔍 Troubleshooting

### Containers não iniciam

```bash
# Ver logs de erro
docker-compose logs

# Reconstruir imagens
docker-compose build --no-cache

# Limpar e reiniciar
docker-compose down -v
python on.py
```

### Dados inconsistentes

```bash
# Verificar status de replicação
python status.py

# Ver logs de replicação
docker logs servidor_1 | grep REPLICAÇÃO

# Forçar ressincronização (reiniciar servidores)
docker-compose restart servidor_1 servidor_2 servidor_3
```

### Eleição não acontece

```bash
# Verificar se servidores estão inscritos no tópico 'servers'
docker logs servidor_1 | grep "Inscrito no tópico"

# Ver logs de eleição
docker logs servidor_3 | grep ELEIÇÃO

# Forçar eleição (parar coordenador)
docker stop servidor_3
```

### Sincronização de relógio não funciona

```bash
# Verificar se há coordenador
python status.py

# Ver logs de Berkeley
docker logs servidor_3 | grep BERKELEY
```


## 🛠️ Tecnologias Utilizadas

- **Broker/Proxy**: Go + ZeroMQ
- **Servidores/Referência**: Python + ZeroMQ + MessagePack
- **Cliente/Bots**: Node.js + ZeroMQ + MessagePack
- **Containerização**: Docker + Docker Compose
- **Persistência**: JSON (arquivos locais)

## 📈 Características Avançadas

- ✅ Balanceamento de carga (round-robin)
- ✅ Replicação total com consistência eventual
- ✅ Ordenação causal com relógio lógico
- ✅ Sincronização de relógio físico (Berkeley)
- ✅ Eleição de líder (Bully)
- ✅ Detecção de falhas (heartbeat)
- ✅ Recuperação automática (sincronização inicial)
- ✅ Serialização eficiente (MessagePack)
- ✅ Pub/Sub para mensagens
- ✅ Deduplicação de operações

## 🎯 Resultados Esperados

Ao executar o sistema:

1. **Eleição**: servidor com maior rank torna-se coordenador
2. **Replicação**: Todas as operações replicadas em todos os servidores
3. **Consistência**: Dados idênticos em `data/servidor_1/`, `data/servidor_2/`, `data/servidor_3/`
4. **Berkeley**: Coordenador sincroniza relógios a cada 10 mensagens
5. **Tolerância a Falhas**: Sistema continua funcionando se 1 servidor cair
6. **Recuperação**: Servidor reiniciado sincroniza automaticamente

## 👥 Autores

Projeto desenvolvido para a disciplina de Sistemas Distribuídos.

## 📄 Licença

Este projeto é parte de um trabalho acadêmico.
