const zmq = require('zeromq');
const msgpack = require('@msgpack/msgpack');

class MessageBot {
    constructor() {
        this.socket = new zmq.Request();
        this.subSocket = new zmq.Subscriber();
        this.username = `bot_${Math.random().toString(36).substring(7)}`;
        this.brokerAddress = process.env.BROKER_ADDRESS || 'tcp://broker:5555';
        this.proxyAddress = process.env.PROXY_ADDRESS || 'tcp://proxy:5558';
        this.channels = [];
        this.running = true;
        
        // Relógio lógico
        this.logicalClock = 0;
        
        // Mensagens pré-definidas que o bot pode enviar
        this.messages = [
            "Olá! Sou um bot automatizado 🤖",
            "Teste de mensagem automática",
            "Sistema funcionando perfeitamente!",
            "Enviando mais uma mensagem...",
            "Bot ativo e operacional",
            "Checando conectividade do sistema",
            "Mensagem de teste #" + Math.floor(Math.random() * 1000),
            "Heartbeat - sistema OK",
            "Processando dados...",
            "Tudo funcionando como esperado!"
        ];
    }
    
    incrementClock() {
        this.logicalClock++;
        return this.logicalClock;
    }
    
    updateClock(receivedClock) {
        this.logicalClock = Math.max(this.logicalClock, receivedClock) + 1;
        return this.logicalClock;
    }

    async connect() {
        await this.socket.connect(this.brokerAddress);
        console.log(`Bot conectado ao broker em ${this.brokerAddress} (MessagePack + Relógio Lógico)`);
        
        await this.subSocket.connect(this.proxyAddress);
        console.log(`Bot conectado ao proxy em ${this.proxyAddress}`);
    }

    async sendRequest(service, data) {
        const clock = this.incrementClock();
        const message = {
            service: service,
            data: {
                ...data,
                timestamp: new Date().toISOString(),
                clock: clock
            }
        };

        // Enviar com MessagePack
        await this.socket.send(msgpack.encode(message));
        
        // Receber com MessagePack
        const [response] = await this.socket.receive();
        const decoded = msgpack.decode(response);
        
        // Atualizar relógio lógico
        if (decoded.data && decoded.data.clock) {
            this.updateClock(decoded.data.clock);
        }
        
        return decoded;
    }

    async login() {
        try {
            const response = await this.sendRequest('login', {
                user: this.username
            });

            if (response.data.status === 'sucesso') {
                console.log(`✓ Bot logado como: ${this.username}`);
                
                // Inscrever para receber mensagens
                this.subSocket.subscribe(this.username);
                this.startListening();
                
                return true;
            } else {
                console.error(`✗ Erro no login: ${response.data.description}`);
                return false;
            }
        } catch (error) {
            console.error('Erro ao fazer login:', error.message);
            return false;
        }
    }

    async getChannels() {
        try {
            const response = await this.sendRequest('channels', {});
            if (response.data.users && response.data.users.length > 0) {
                this.channels = response.data.users;
                console.log(`Canais disponíveis: ${this.channels.join(', ')}`);
            } else {
                console.log('Nenhum canal disponível ainda.');
            }
        } catch (error) {
            console.error('Erro ao buscar canais:', error.message);
        }
    }

    async subscribeToChannel(channel) {
        this.subSocket.subscribe(channel);
        console.log(`Bot inscrito no canal: ${channel}`);
    }

    async publishMessage(channel, message) {
        try {
            const response = await this.sendRequest('publish', {
                user: this.username,
                channel: channel,
                message: message
            });

            if (response.data.status === 'OK') {
                console.log(`✓ Publicado no canal '${channel}': ${message}`);
            } else {
                console.error(`✗ Erro ao publicar: ${response.data.message}`);
            }
        } catch (error) {
            console.error('Erro ao publicar mensagem:', error.message);
        }
    }

    getRandomMessage() {
        return this.messages[Math.floor(Math.random() * this.messages.length)];
    }

    getRandomChannel() {
        if (this.channels.length === 0) return null;
        return this.channels[Math.floor(Math.random() * this.channels.length)];
    }

    startListening() {
        // Listener assíncrono para mensagens
        (async () => {
            for await (const [topic, msg] of this.subSocket) {
                try {
                    // Decodificar MessagePack
                    const data = msgpack.decode(msg);
                    const topicStr = topic.toString();
                    
                    // Atualizar relógio lógico
                    if (data.clock) {
                        this.updateClock(data.clock);
                    }
                    
                    if (topicStr === this.username) {
                        console.log(`[MENSAGEM PRIVADA de ${data.from}]: ${data.message} | Clock: ${data.clock || 'N/A'}`);
                    } else {
                        console.log(`[CANAL: ${topicStr}] ${data.user}: ${data.message} | Clock: ${data.clock || 'N/A'}`);
                    }
                } catch (e) {
                    console.error('Erro ao processar mensagem:', e.message);
                }
            }
        })();
    }

    async runLoop() {
        console.log('\n=== Bot iniciando loop de publicações ===\n');
        
        while (this.running) {
            // 1. Buscar canais disponíveis
            await this.getChannels();
            
            if (this.channels.length === 0) {
                console.log('Aguardando criação de canais...');
                await this.sleep(5000);
                continue;
            }
            
            // 2. Escolher canal aleatório
            const channel = this.getRandomChannel();
            
            // Inscrever no canal se ainda não estiver
            await this.subscribeToChannel(channel);
            
            // 3. Enviar 10 mensagens
            for (let i = 0; i < 10; i++) {
                const message = this.getRandomMessage();
                await this.publishMessage(channel, message);
                
                // Aguardar um pouco entre mensagens
                await this.sleep(2000);
            }
            
            // 4. Aguardar antes de repetir o ciclo
            console.log('\nCiclo completo. Aguardando próximo ciclo...\n');
            await this.sleep(5000);
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async start() {
        console.log('=================================');
        console.log('Bot Automatizado de Mensagens');
        console.log('=================================\n');

        await this.connect();

        // Fazer login
        const loggedIn = await this.login();
        if (!loggedIn) {
            console.error('Falha no login. Encerrando bot.');
            process.exit(1);
        }

        // Aguardar um pouco para o sistema estar pronto
        await this.sleep(3000);

        // Iniciar loop de publicações
        await this.runLoop();
    }
}

// Iniciar bot
const bot = new MessageBot();
bot.start().catch((error) => {
    console.error('Erro fatal:', error);
    process.exit(1);
});

// Tratamento de encerramento
process.on('SIGINT', () => {
    console.log('\nEncerrando bot...');
    process.exit(0);
});