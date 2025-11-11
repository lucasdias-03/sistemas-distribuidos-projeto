const zmq = require('zeromq');

class MessageBot {
    constructor() {
        this.socket = new zmq.Request();
        this.subSocket = new zmq.Subscriber();
        this.username = `bot_${Math.random().toString(36).substring(7)}`;
        this.brokerAddress = process.env.BROKER_ADDRESS || 'tcp://broker:5555';
        this.proxyAddress = process.env.PROXY_ADDRESS || 'tcp://proxy:5558';
        this.channels = [];
        this.running = true;
        
        // Mensagens pré-definidas que o bot pode enviar
        this.messages = [
            "Olá! Sou um bot automatizado 🤖",
            "Teste de mensagem automtica",
            "Enviando mais uma mensagem...",
            "Bot ativo e operacional",
            "Checando conectividade do sistema",
            "Mensagem de teste #" + Math.floor(Math.random() * 1000),
            "Heartbeat - sistema OK",
            "Processando dados...",
            "Tudo funcionando como esperado!"
        ];
    }

    async connect() {
        await this.socket.connect(this.brokerAddress);
        console.log(`Bot conectado ao broker em ${this.brokerAddress}`);
        
        await this.subSocket.connect(this.proxyAddress);
        console.log(`Bot conectado ao proxy em ${this.proxyAddress}`);
    }

    async sendRequest(service, data) {
        const message = {
            service: service,
            data: {
                ...data,
                timestamp: new Date().toISOString()
            }
        };

        await this.socket.send(JSON.stringify(message));
        const [response] = await this.socket.receive();
        return JSON.parse(response.toString());
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
            if (response.data.channels && response.data.channels.length > 0) {
                this.channels = response.data.channels;
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
                    const data = JSON.parse(msg.toString());
                    const topicStr = topic.toString();
                    
                    if (topicStr === this.username) {
                        console.log(`[MENSAGEM PRIVADA de ${data.from}]: ${data.message}`);
                    } else {
                        console.log(`[CANAL: ${topicStr}] ${data.user}: ${data.message}`);
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

                // Aguardar entre mensagens (5-10 segundos)
                await this.sleep(5000 + Math.random() * 5000);
            }

            // 4. Aguardar antes de repetir o ciclo (30-60 segundos)
            const waitTime = 30000 + Math.random() * 30000;
            console.log(`\nCiclo completo. Aguardando ${Math.round(waitTime/1000)}s até o próximo ciclo...\n`);
            await this.sleep(waitTime);
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