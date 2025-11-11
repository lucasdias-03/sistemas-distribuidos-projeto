# Plano de Testes - Sistema de Mensagens

## Preparação

```bash
# Iniciar o sistema
docker-compose up --build

# Em outro terminal, acessar o cliente interativo
docker exec -it cliente node client.js
```

---

## Teste 1: Criação de Usuários e Canais

### Objetivo
Validar que usuários e canais são criados e listados corretamente.

### Passos
1. Faça login com o nome "Alice"
2. Escolha opção `1` - Listar usuários
   - ✅ Deve mostrar "Alice" na lista
3. Escolha opção `2` - Criar canal
   - Digite "canal-geral"
   - ✅ Deve exibir "Canal criado com sucesso"
4. Escolha opção `3` - Listar canais
   - ✅ Deve mostrar "canal-geral" na lista

### Validação de Persistência
```bash
# Verificar arquivos JSON
cat data/servidor/users.json
# ✅ Deve conter "Alice"

cat data/servidor/channels.json
# ✅ Deve conter "canal-geral"

cat data/servidor/logins.json
# ✅ Deve conter registro de login de "Alice" com timestamp
```

---

## Teste 2: Publicação em Canais

### Objetivo
Validar que mensagens são publicadas em canais e recebidas por inscritos.

### Setup - Cliente 1 (Alice)
```bash
docker exec -it cliente node client.js
```
1. Login como "Alice"
2. Opção `4` - Inscrever em canal
   - Digite "canal-geral"
   - ✅ Deve confirmar inscrição

### Setup - Cliente 2 (Bob)
```bash
# Em outro terminal
docker run -it --rm --network sistemas-distribuidos-projeto_mensagens-net \
  -e BROKER_ADDRESS=tcp://broker:5555 \
  -e PROXY_ADDRESS=tcp://proxy:5558 \
  $(docker build -q ./cliente) node client.js
```
1. Login como "Bob"
2. Opção `4` - Inscrever em canal
   - Digite "canal-geral"

### Teste de Publicação
**No terminal do Bob:**
1. Opção `5` - Publicar em canal
2. Canal: "canal-geral"
3. Mensagem: "Olá a todos!"

**Validação:**
- ✅ Bob deve ver confirmação "Mensagem publicada"
- ✅ Alice deve receber automaticamente: `[CANAL: canal-geral] Bob: Olá a todos!`
- ✅ Alice deve ver o timestamp da mensagem

### Validação de Persistência
```bash
cat data/servidor/publications.json
# ✅ Deve conter:
# - channel: "canal-geral"
# - user: "Bob"
# - message: "Olá a todos!"
# - timestamp
```

---

## Teste 3: Mensagens Privadas

### Objetivo
Validar envio e recebimento de mensagens privadas entre usuários.

### Setup
Use os mesmos 2 clientes do Teste 2 (Alice e Bob já logados)

### Teste
**No terminal da Alice:**
1. Opção `6` - Enviar mensagem privada
2. Destinatário: "Bob"
3. Mensagem: "Oi Bob, tudo bem?"

**Validação:**
- ✅ Alice deve ver confirmação "Mensagem enviada"
- ✅ Bob deve receber automaticamente: `[MENSAGEM PRIVADA de Alice]: Oi Bob, tudo bem?`
- ✅ Bob deve ver o timestamp da mensagem

**No terminal do Bob (responder):**
1. Opção `6` - Enviar mensagem privada
2. Destinatário: "Alice"
3. Mensagem: "Oi Alice! Estou bem, obrigado!"

**Validação:**
- ✅ Alice deve receber a mensagem privada de Bob

### Validação de Persistência
```bash
cat data/servidor/messages.json
# ✅ Deve conter AMBAS as mensagens:
# 1. src: "Alice", dst: "Bob", message: "Oi Bob, tudo bem?"
# 2. src: "Bob", dst: "Alice", message: "Oi Alice! Estou bem, obrigado!"
# ✅ Ambas com timestamps
```

---

## Teste 4: Tratamento de Erros

### Teste 4.1: Publicar em Canal Inexistente

**Passos:**
1. Opção `5` - Publicar em canal
2. Canal: "canal-que-nao-existe"
3. Mensagem: "teste"

**Validação:**
- ✅ Deve exibir erro: "Canal não existe"

### Teste 4.2: Mensagem para Usuário Inexistente

**Passos:**
1. Opção `6` - Enviar mensagem privada
2. Destinatário: "usuario-inexistente"
3. Mensagem: "teste"

**Validação:**
- ✅ Deve exibir erro: "Usuário não existe"

### Teste 4.3: Tentativa de Login Duplicado

**Passos:**
1. Abra um terceiro terminal
2. Tente fazer login com "Alice" (já logada)

**Validação:**
- ✅ Deve exibir erro: "Usuário já cadastrado"

---

## Teste 5: Bots Automatizados

### Objetivo
Validar que os bots estão funcionando e publicando mensagens automaticamente.

### Validação
```bash
# Ver logs dos bots
docker logs bot-1
docker logs bot-2

# ✅ Deve mostrar:
# - Login bem-sucedido com nome aleatório (ex: bot_abc123)
# - Busca de canais disponíveis
# - Inscrição em canais
# - Publicações sendo feitas
# - Mensagens recebidas de outros bots
```

### Verificar Recebimento pelos Clientes

**No terminal de Alice ou Bob (já inscritos em "canal-geral"):**
- ✅ Devem receber mensagens dos bots automaticamente
- ✅ Formato: `[CANAL: canal-geral] bot_xyz: <mensagem>`

### Verificar Réplicas
```bash
docker ps | grep bot
# ✅ Deve mostrar 2 containers de bot rodando
```

---

## Teste 6: Persistência e Recuperação

### Objetivo
Validar que dados são persistidos e recuperados após reinicialização.

### Passos
1. Anote os dados atuais:
   ```bash
   cat data/servidor/users.json
   cat data/servidor/channels.json
   cat data/servidor/publications.json
   ```

2. Reinicie o servidor:
   ```bash
   docker-compose restart servidor
   ```

3. Faça login com um cliente novo
4. Liste usuários e canais

**Validação:**
- ✅ Todos os usuários anteriores ainda existem
- ✅ Todos os canais anteriores ainda existem
- ✅ Novas publicações são adicionadas ao arquivo (não sobrescritas)

---

## Teste 7: Múltiplos Inscritos em Canal

### Objetivo
Validar que múltiplos usuários recebem a mesma publicação.

### Setup
Abra 3 terminais com clientes diferentes:
- Alice
- Bob
- Carol

Todos se inscrevem em "canal-teste"

### Teste
**Carol publica:**
- Mensagem: "Teste com múltiplos inscritos"

**Validação:**
- ✅ Alice recebe a mensagem
- ✅ Bob recebe a mensagem
- ✅ Carol NÃO recebe (publicador não recebe própria mensagem via SUB)

---

## Teste 8: Proxy Pub/Sub Funcionando

### Objetivo
Validar que o proxy está encaminhando mensagens corretamente.

### Validação
```bash
# Ver logs do proxy
docker logs proxy

# ✅ Deve mostrar:
# - "Iniciando Proxy Pub/Sub..."
# - "XSUB escutando na porta 5557 (publishers/servidores)"
# - "XPUB escutando na porta 5558 (subscribers/clientes)"
# - "Proxy Pub/Sub rodando..."
```

### Teste de Conectividade
```bash
# Verificar se as portas estão abertas
docker exec broker sh -c "nc -zv proxy 5557"
docker exec cliente sh -c "nc -zv proxy 5558"

# ✅ Ambos devem retornar "succeeded" ou "open"
```

---

## Checklist Final

Após executar todos os testes, verifique:

- [ ] Usuários são criados e persistidos
- [ ] Canais são criados e persistidos
- [ ] Publicações em canais funcionam
- [ ] Mensagens privadas funcionam
- [ ] Inscrições em canais funcionam
- [ ] Múltiplos inscritos recebem mensagens
- [ ] Erros são tratados corretamente (canal/usuário inexistente)
- [ ] Bots automatizados estão funcionando (2 réplicas)
- [ ] Dados são persistidos em JSON
- [ ] Arquivo publications.json está correto
- [ ] Arquivo messages.json é criado ao enviar mensagem privada
- [ ] Proxy Pub/Sub está rodando nas portas 5557/5558
- [ ] Sistema recupera dados após reinicialização

---

## Comandos Úteis

```bash
# Ver logs em tempo real
docker-compose logs -f

# Ver logs de um serviço específico
docker logs -f servidor
docker logs -f proxy
docker logs -f broker

# Limpar dados persistidos (CUIDADO!)
rm -rf data/servidor/*.json

# Reiniciar apenas um serviço
docker-compose restart servidor

# Ver containers rodando
docker ps

# Entrar em um container
docker exec -it <container> sh
```
