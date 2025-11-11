const zmq = require('zeromq');
const readline = require('readline');

class MessageClient {
    constructor() {
        this.socket = new zmq.Request();
        this.username = null;
        this.brokerAddress = process.env.BROKER_ADDRESS || 'tcp://broker:5555';
        
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
    }

    async connect() {
        await this.socket.connect(this.brokerAddress);
        console.log(`Cliente conectado ao broker em ${this.brokerAddress}`);
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
            if (response.data.users && response.data.users.length > 0) {
                response.data.users.forEach((channel, index) => {
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

    showMenu() {
        console.log('=== Menu ===');
        console.log('1. Listar usuários');
        console.log('2. Criar canal');
        console.log('3. Listar canais');
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