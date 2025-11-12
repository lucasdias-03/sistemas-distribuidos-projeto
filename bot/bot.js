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

        await this.subSocket.connect(this.proxyAddress);
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
                // Inscrever para receber mensagens
                this.subSocket.subscribe(this.username);
                this.startListening();

                return true;
            } else {
                return false;
            }
        } catch (error) {
            return false;
        }
    }

    async getChannels() {
        try {
            const response = await this.sendRequest('channels', {});
            if (response.data.users && response.data.users.length > 0) {
                this.channels = response.data.users;
            }
        } catch (error) {
            // Silenciar erro
        }
    }

    async subscribeToChannel(channel) {
        this.subSocket.subscribe(channel);
    }

    async publishMessage(channel, message) {
        try {
            await this.sendRequest('publish', {
                user: this.username,
                channel: channel,
                message: message
            });
        } catch (error) {
            // Silenciar erro
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
            for await (const [, msg] of this.subSocket) {
                try {
                    // Decodificar MessagePack
                    const data = msgpack.decode(msg);

                    // Atualizar relógio lógico
                    if (data.clock) {
                        this.updateClock(data.clock);
                    }
                } catch (e) {
                    // Silenciar erro
                }
            }
        })();
    }

    async runLoop() {
        while (this.running) {
            // 1. Buscar canais disponíveis
            await this.getChannels();

            if (this.channels.length === 0) {
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
                await this.sleep(8000);
            }

            // 4. Aguardar antes de repetir o ciclo
            await this.sleep(15000);
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async start() {
        await this.connect();

        // Fazer login
        const loggedIn = await this.login();
        if (!loggedIn) {
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
bot.start().catch(() => {
    process.exit(1);
});

// Tratamento de encerramento
process.on('SIGINT', () => {
    process.exit(0);
});