# 🗳️ Teste de Eleição - Algoritmo Bully

Este documento explica como testar o algoritmo de eleição Bully implementado no sistema.

## 📋 Pré-requisitos

1. Sistema rodando com Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Servidor de referência ativo (porta 5559)

3. Pelo menos 2 servidores ativos (recomendado: 3)

## 🎯 Como Funciona a Eleição

O sistema utiliza o **Algoritmo Bully** para eleição de coordenador:

### Funcionamento:
1. **Ranks**: Cada servidor recebe um rank único do servidor de referência
2. **Coordenador**: Servidor com maior rank é o coordenador
3. **Detecção de Falha**: Quando um servidor não consegue comunicar com o coordenador
4. **Processo de Eleição**:
   - Servidor detecta falha e inicia eleição
   - Envia mensagem "ELECTION" para servidores com rank maior
   - Se receber "OK", aguarda anúncio do coordenador
   - Se nenhum responder, torna-se o coordenador
5. **Anúncio**: Novo coordenador anuncia via tópico 'servers'

### Implementação:
- **Servidor de Referência** ([referencia/reference.py](referencia/reference.py)):
  - Atribui ranks únicos aos servidores
  - Mantém lista de servidores ativos via heartbeat
  - Remove servidores inativos após 30s sem heartbeat

- **Servidores** ([servidor/server.py](servidor/server.py)):
  - Método `start_election()` (linha 176): Inicia eleição
  - Método `handle_election_request()` (linha 261): Responde a eleições
  - Método `become_coordinator()` (linha 237): Torna-se coordenador
  - Thread `listen_to_servers_topic()` (linha 413): Escuta anúncios

## 🚀 Opções de Teste

### Opção 1: Teste Automático

Script que automaticamente:
- Lista os servidores
- Para o coordenador atual
- Aguarda eleição
- Mostra o novo coordenador
- Reinicia o servidor original

```bash
python test_election.py
```

**Saída esperada:**
```
🗳️  TESTE DE ELEIÇÃO - ALGORITMO BULLY
======================================================================

📋 Passo 1: Verificando servidores registrados...

✅ Encontrados 3 servidores:
   • servidor_1         (Rank: 1)
   • servidor_2         (Rank: 2)
   • servidor_3         (Rank: 3)

👑 Coordenador esperado (maior rank): servidor_3

💥 Passo 3: Simulando falha do coordenador...
🔴 Parando servidor servidor_3...
✅ Servidor servidor_3 parado com sucesso!

⏳ Aguardando processo de eleição (15 segundos)...

🔍 Passo 5: Verificando novo coordenador...

✅ Servidores ativos após eleição:
   • servidor_1         (Rank: 1)
   • servidor_2         (Rank: 2)

👑 Novo coordenador esperado: servidor_2

📊 Consultando servidores sobre o coordenador atual:
   • servidor_1 → Coordenador: servidor_2
   • servidor_2 → Coordenador: servidor_2

✅ SUCESSO! Eleição funcionou corretamente!
```

### Opção 2: Teste Manual Interativo

Script interativo que permite:
- Ver lista de servidores ativos
- Escolher qual servidor desligar
- Ver o processo de eleição
- Iniciar servidores novamente

```bash
python test_election_manual.py
```

**Interface:**
```
🗳️  TESTE INTERATIVO DE ELEIÇÃO - ALGORITMO BULLY
============================================================
📋 SERVIDORES REGISTRADOS NO SERVIDOR DE REFERÊNCIA
============================================================

Total: 3 servidores ativos

  1.    servidor_1         | Rank: 1
  2.    servidor_2         | Rank: 2
  3. 👑 servidor_3         | Rank: 3

👑 Coordenador esperado: servidor_3 (maior rank)

------------------------------------------------------------
OPÇÕES:
  1-N) Desligar servidor (número da lista)
  s)   Iniciar servidor
  r)   Atualizar lista
  l)   Ver logs dos servidores
  q)   Sair
------------------------------------------------------------

Escolha uma opção:
```

## 📊 Observando a Eleição nos Logs

Para ver a eleição acontecendo em tempo real:

```bash
docker-compose logs -f servidor_1 servidor_2 servidor_3 | grep "ELEIÇÃO"
```

**Mensagens esperadas:**
```
servidor_2  | [ELEIÇÃO] Iniciando eleição... (Rank: 2)
servidor_2  | [ELEIÇÃO] Servidor servidor_3 não respondeu: [Errno 111] Connection refused
servidor_2  | [ELEIÇÃO] 'servidor_2' é o novo COORDENADOR!
servidor_2  | [ELEIÇÃO] Coordenador anunciado no tópico 'servers'

servidor_1  | [ELEIÇÃO] Novo coordenador anunciado: servidor_2
```

## 🧪 Cenários de Teste

### Cenário 1: Coordenador Falha
1. Sistema tem 3 servidores (ranks 1, 2, 3)
2. Servidor 3 é o coordenador
3. Parar servidor 3
4. **Resultado**: Servidor 2 assume como coordenador

### Cenário 2: Servidor Não-Coordenador Falha
1. Sistema tem 3 servidores (ranks 1, 2, 3)
2. Servidor 3 é o coordenador
3. Parar servidor 1
4. **Resultado**: Nenhuma eleição, servidor 3 continua coordenador

### Cenário 3: Coordenador Volta
1. Sistema tem 2 servidores (ranks 1, 2)
2. Servidor 2 é coordenador
3. Iniciar servidor 3 (rank maior)
4. **Resultado**: Servidor 3 inicia eleição e assume coordenador

### Cenário 4: Múltiplas Falhas
1. Sistema tem 3 servidores
2. Parar servidor 3 → Servidor 2 assume
3. Parar servidor 2 → Servidor 1 assume
4. **Resultado**: Servidor 1 é o último coordenador

## 🔍 Verificação Manual

Você também pode verificar manualmente usando os scripts do sistema:

```bash
# Ver status dos servidores
python status.py

# Desligar um servidor específico
docker-compose stop servidor_3

# Aguardar eleição (10-15 segundos)

# Ver status novamente
python status.py

# Reiniciar servidor
docker-compose start servidor_3
```

## 📝 Notas Importantes

1. **Tempo de Eleição**: A eleição pode levar 5-15 segundos para completar

2. **Heartbeat**: Servidores enviam heartbeat a cada 5 segundos

3. **Timeout**: Servidor de referência remove servidores sem heartbeat após 30s

4. **Detecção de Falha**: Servidores detectam falha ao tentar sincronizar relógio

5. **Mensagens de Eleição**:
   - Procure por `[ELEIÇÃO]` nos logs
   - `start_election()` → Inicia processo
   - `handle_election_request()` → Responde OK
   - `become_coordinator()` → Anuncia coordenador

## 🐛 Troubleshooting

### Problema: "Nenhum servidor encontrado"
**Solução**:
```bash
docker-compose up -d
# Aguarde 5 segundos para servidores registrarem
```

### Problema: "Erro ao conectar com servidor de referência"
**Solução**:
```bash
docker-compose ps
# Verifique se container 'referencia' está rodando
docker-compose logs referencia
```

### Problema: Eleição não acontece
**Possíveis causas**:
1. Servidores não estão detectando a falha
2. Timeout muito curto
3. Problemas de rede no Docker

**Verificação**:
```bash
# Ver logs detalhados
docker-compose logs -f --tail=100 servidor_1 servidor_2 servidor_3

# Verificar se servidores estão se comunicando
docker-compose exec servidor_1 ping servidor_2
```

## 📚 Referências

- **Algoritmo Bully**: H. Garcia-Molina (1982)
- **Implementação**:
  - [servidor/server.py](servidor/server.py) - linhas 176-281
  - [referencia/reference.py](referencia/reference.py) - linhas 37-100
