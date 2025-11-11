const zmq = require('zeromq');
const readline = require('readline');

class MessageClient {
    constructor() {
        this.socket = new zmq.Request();
        this.subSocket = new zmq.Subscriber();
        this.username = null;
        this.brokerAddress = process.env.BROKER_ADDRESS || 'tcp://broker:5555';
        this.proxyAddress = process.env.PROXY_ADDRESS || 'tcp://proxy:5558';
        this.subscribedChannels = [];
        
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
    }

    async connect() {
        await this.socket.connect(this.brokerAddress);
        console.log(`Cliente conectado ao broker em ${this.brokerAddress}`);
        
        await this.subSocket.connect(this.proxyAddress);
        console.log(`Cliente conectado ao proxy em ${this.proxyAddress}`);
    }
    
    async subscribeToUser() {
        // Inscrever-se para receber mensagens privadas (tópico = nome do usuário)
        if (this.username) {
            this.subSocket.subscribe(this.username);
            console.log(`Inscrito para receber mensagens privadas como '${this.username}'`);
        }
    }
    
    async subscribeToChannel(channel) {
        this.subSocket.subscribe(channel);
        this.subscribedChannels.push(channel);
        console.log(`\n✓ Inscrito no canal '${channel}'\n`);
    }
    
    async startListening() {
        // Listener assíncrono para mensagens publicadas
        (async () => {
            for await (const [topic, msg] of this.subSocket) {
                try {
                    const data = JSON.parse(msg.toString());
                    const topicStr = topic.toString();
                    
                    if (topicStr === this.username) {
                        // Mensagem privada
                        console.log(`\n[MENSAGEM PRIVADA de ${data.from}]: ${data.message}`);
                        console.log(`Timestamp: ${data.timestamp}\n`);
                    } else {
                        // Publicação em canal
                        console.log(`\n[CANAL: ${topicStr}] ${data.user}: ${data.message}`);
                        console.log(`Timestamp: ${data.timestamp}\n`);
                    }
                } catch (e) {
                    console.error('Erro ao processar mensagem:', e.message);
                }
            }
        })();
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
        return new Promise((resolve) => {
            this.rl.question('Digite seu nome de usuário: ', async (username) => {
                try {
                    const response = await this.sendRequest('login', {
                        user: username
                    });

                    if (response.data.status === 'sucesso') {
                        this.username = username;
                        await this.subscribeToUser();
                        await this.startListening();
                        console.log(`\n✓ Login realizado com sucesso! Bem-vindo, ${username}!\n`);
                        resolve(true);
                    } else {
                        console.log(`\n✗ Erro no login: ${response.data.description}\n`);
                        resolve(false);
                    }
                } catch (error) {
                    console.error('Erro ao fazer login:', error.message);
                    resolve(false);
                }
            });
        });
    }

    async listUsers() {
        try {
            const response = await this.sendRequest('users', {});
            console.log('\n=== Usuários Cadastrados ===');
            if (response.data.users && response.data.users.length > 0) {
                response.data.users.forEach((user, index) => {
                    console.log(`${index + 1}. ${user}`);
                });
            } else {
                console.log('Nenhum usuário cadastrado.');
            }
            console.log('===========================\n');
        } catch (error) {
            console.error('Erro ao listar usuários:', error.message);
        }
    }

    async createChannel() {
        return new Promise((resolve) => {
            this.rl.question('Digite o nome do canal: ', async (channel) => {
                try {
                    const response = await this.sendRequest('channel', {
                        channel: channel
                    });

                    if (response.data.status === 'sucesso') {
                        console.log(`\n✓ Canal '${channel}' criado com sucesso!\n`);
                    } else {
                        console.log(`\n✗ Erro: ${response.data.description}\n`);
                    }
                } catch (error) {
                    console.error('Erro ao criar canal:', error.message);
                }
                resolve();
            });
        });
    }

    async listChannels() {
        try {
            const response = await this.sendRequest('channels', {});
            console.log('\n=== Canais Disponíveis ===');
            if (response.data.channels && response.data.channels.length > 0) {
                response.data.channels.forEach((channel, index) => {
                    console.log(`${index + 1}. ${channel}`);
                });
            } else {
                console.log('Nenhum canal disponível.');
            }
            console.log('==========================\n');
        } catch (error) {
            console.error('Erro ao listar canais:', error.message);
        }
    }
    
    async subscribeChannel() {
        return new Promise((resolve) => {
            this.rl.question('Digite o nome do canal para se inscrever: ', async (channel) => {
                try {
                    await this.subscribeToChannel(channel);
                } catch (error) {
                    console.error('Erro ao se inscrever:', error.message);
                }
                resolve();
            });
        });
    }
    
    async publishToChannel() {
        return new Promise((resolve) => {
            this.rl.question('Digite o nome do canal: ', async (channel) => {
                this.rl.question('Digite a mensagem: ', async (message) => {
                    try {
                        const response = await this.sendRequest('publish', {
                            user: this.username,
                            channel: channel,
                            message: message
                        });

                        if (response.data.status === 'OK') {
                            console.log(`\n✓ Mensagem publicada no canal '${channel}'\n`);
                        } else {
                            console.log(`\n✗ Erro: ${response.data.message}\n`);
                        }
                    } catch (error) {
                        console.error('Erro ao publicar:', error.message);
                    }
                    resolve();
                });
            });
        });
    }
    
    async sendPrivateMessage() {
        return new Promise((resolve) => {
            this.rl.question('Digite o nome do destinatário: ', async (dst) => {
                this.rl.question('Digite a mensagem: ', async (message) => {
                    try {
                        const response = await this.sendRequest('message', {
                            src: this.username,
                            dst: dst,
                            message: message
                        });

                        if (response.data.status === 'OK') {
                            console.log(`\n✓ Mensagem enviada para '${dst}'\n`);
                        } else {
                            console.log(`\n✗ Erro: ${response.data.message}\n`);
                        }
                    } catch (error) {
                        console.error('Erro ao enviar mensagem:', error.message);
                    }
                    resolve();
                });
            });
        });
    }

    showMenu() {
        console.log('=== Menu ===');
        console.log('1. Listar usuários');
        console.log('2. Criar canal');
        console.log('3. Listar canais');
        console.log('4. Inscrever em canal');
        console.log('5. Publicar em canal');
        console.log('6. Enviar mensagem privada');
        console.log('0. Sair');
        console.log('============\n');
    }

    async menu() {
        return new Promise((resolve) => {
            this.rl.question('Escolha uma opção: ', async (option) => {
                switch (option) {
                    case '1':
                        await this.listUsers();
                        break;
                    case '2':
                        await this.createChannel();
                        break;
                    case '3':
                        await this.listChannels();
                        break;
                    case '4':
                        await this.subscribeChannel();
                        break;
                    case '5':
                        await this.publishToChannel();
                        break;
                    case '6':
                        await this.sendPrivateMessage();
                        break;
                    case '0':
                        console.log('Saindo...');
                        resolve(false);
                        return;
                    default:
                        console.log('Opção inválida!\n');
                }
                resolve(true);
            });
        });
    }

    async start() {
        console.log('=================================');
        console.log('Sistema de Mensagens Instantâneas');
        console.log('=================================\n');

        await this.connect();

        // Loop de login até conseguir
        let loggedIn = false;
        while (!loggedIn) {
            loggedIn = await this.login();
            if (!loggedIn) {
                const retry = await new Promise((resolve) => {
                    this.rl.question('Tentar novamente? (s/n): ', (answer) => {
                        resolve(answer.toLowerCase() === 's');
                    });
                });
                if (!retry) {
                    console.log('Encerrando...');
                    this.rl.close();
                    this.socket.close();
                    process.exit(0);
                }
            }
        }

        // Menu principal
        let running = true;
        while (running) {
            this.showMenu();
            running = await this.menu();
        }

        this.rl.close();
        this.socket.close();
        this.subSocket.close();
        console.log('Cliente encerrado.');
    }
}

// Iniciar cliente
const client = new MessageClient();
client.start().catch((error) => {
    console.error('Erro fatal:', error);
    process.exit(1);
});

// Tratamento de encerramento
process.on('SIGINT', () => {
    console.log('\nEncerrando cliente...');
    process.exit(0);
});