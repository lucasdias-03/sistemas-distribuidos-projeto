#!/usr/bin/env python3
import zmq
import json
import os
from datetime import datetime
from pathlib import Path

class MessageServer:
    def __init__(self, data_dir="/data"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        # Socket PUB para publicações
        self.pub_socket = self.context.socket(zmq.PUB)
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivos de persistência
        self.users_file = self.data_dir / "users.json"
        self.channels_file = self.data_dir / "channels.json"
        self.logins_file = self.data_dir / "logins.json"
        self.messages_file = self.data_dir / "messages.json"
        self.publications_file = self.data_dir / "publications.json"
        
        # Carregar dados existentes
        self.users = self.load_data(self.users_file, [], 'users')
        self.channels = self.load_data(self.channels_file, [], 'channels')
        self.logins = self.load_data(self.logins_file, [], 'logins')
        self.messages = self.load_data(self.messages_file, [], 'messages')
        self.publications = self.load_data(self.publications_file, [], 'publications')
        
        print(f"Servidor iniciado. Usuários: {len(self.users)}, Canais: {len(self.channels)}")
    
    def load_data(self, file_path, default, data_key=None):
        """Carrega dados do arquivo JSON"""
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    content = json.load(f)
                    # Se o arquivo tem formato estruturado, extrair os dados
                    if isinstance(content, dict) and 'data' in content and data_key:
                        return content['data'].get(data_key, default)
                    return content if not data_key else default
            except Exception as e:
                print(f"Erro ao carregar {file_path}: {e}")
                return default
        return default
    
    def save_data(self, file_path, data):
        """Salva dados no arquivo JSON"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar {file_path}: {e}")
    
    def handle_login(self, data):
        """Processa login de usuário"""
        user = data.get("user")
        timestamp = data.get("timestamp")
        
        if not user:
            return {
                "service": "login",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": "Nome de usuário não fornecido"
                }
            }
        
        # Verificar se usuário já existe
        if user in self.users:
            return {
                "service": "login",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": "Usuário já cadastrado"
                }
            }
        
        # Adicionar usuário
        self.users.append(user)
        users_data = {
            "service": "users",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "users": self.users
            }
        }
        self.save_data(self.users_file, users_data)

        # Registrar login
        self.logins.append({
            "user": user,
            "timestamp": timestamp
        })
        logins_data = {
            "service": "login",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "logins": self.logins
            }
        }
        self.save_data(self.logins_file, logins_data)
        
        print(f"Login: {user} ({timestamp})")
        
        return {
            "service": "login",
            "data": {
                "status": "sucesso",
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def handle_users(self, data):
        """Retorna lista de usuários"""
        return {
            "service": "users",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "users": self.users
            }
        }
    
    def handle_channel(self, data):
        """Cria novo canal"""
        channel = data.get("channel")
        timestamp = data.get("timestamp")
        
        if not channel:
            return {
                "service": "channel",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": "Nome do canal não fornecido"
                }
            }
        
        # Verificar se canal já existe
        if channel in self.channels:
            return {
                "service": "channel",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": "Canal já existe"
                }
            }
        
        # Adicionar canal
        self.channels.append(channel)
        channels_data = {
            "service": "channels",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "channels": self.channels
            }
        }
        self.save_data(self.channels_file, channels_data)

        print(f"Canal criado: {channel} ({timestamp})")
        
        return {
            "service": "channel",
            "data": {
                "status": "sucesso",
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def handle_channels(self, data):
        """Retorna lista de canais"""
        return {
            "service": "channels",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "channels": self.channels
            }
        }
    
    def handle_publish(self, data):
        """Publica mensagem em canal"""
        user = data.get("user")
        channel = data.get("channel")
        message = data.get("message")
        timestamp = data.get("timestamp")
        
        if not channel or not message:
            return {
                "service": "publish",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Canal ou mensagem não fornecidos"
                }
            }
        
        # Verificar se canal existe
        if channel not in self.channels:
            return {
                "service": "publish",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Canal não existe"
                }
            }
        
        # Publicar no canal (tópico = nome do canal)
        publication = {
            "user": user,
            "message": message,
            "timestamp": timestamp
        }
        
        # Enviar para o proxy Pub/Sub
        topic = channel
        self.pub_socket.send_string(topic, zmq.SNDMORE)
        self.pub_socket.send_json(publication)
        
        # Persistir publicação
        self.publications.append({
            "channel": channel,
            "user": user,
            "message": message,
            "timestamp": timestamp
        })
        publications_data = {
            "service": "publish",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "publications": self.publications
            }
        }
        self.save_data(self.publications_file, publications_data)
        
        print(f"Publicação no canal '{channel}' por {user}: {message}")
        
        return {
            "service": "publish",
            "data": {
                "status": "OK",
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def handle_message(self, data):
        """Envia mensagem privada para usuário"""
        src = data.get("src")
        dst = data.get("dst")
        message = data.get("message")
        timestamp = data.get("timestamp")
        
        if not dst or not message:
            return {
                "service": "message",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Destinatário ou mensagem não fornecidos"
                }
            }
        
        # Verificar se usuário existe
        if dst not in self.users:
            return {
                "service": "message",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Usuário não existe"
                }
            }
        
        # Publicar para o usuário (tópico = nome do usuário)
        private_message = {
            "from": src,
            "message": message,
            "timestamp": timestamp
        }
        
        # Enviar para o proxy Pub/Sub
        topic = dst
        self.pub_socket.send_string(topic, zmq.SNDMORE)
        self.pub_socket.send_json(private_message)
        
        # Persistir mensagem
        self.messages.append({
            "src": src,
            "dst": dst,
            "message": message,
            "timestamp": timestamp
        })
        messages_data = {
            "service": "message",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "messages": self.messages
            }
        }
        self.save_data(self.messages_file, messages_data)
        
        print(f"Mensagem de {src} para {dst}: {message}")
        
        return {
            "service": "message",
            "data": {
                "status": "OK",
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def process_request(self, message):
        """Processa requisição recebida"""
        try:
            request = json.loads(message)
            service = request.get("service")
            data = request.get("data", {})
            
            print(f"Requisição recebida: {service}")
            
            # Roteamento de serviços
            handlers = {
                "login": self.handle_login,
                "users": self.handle_users,
                "channel": self.handle_channel,
                "channels": self.handle_channels,
                "publish": self.handle_publish,
                "message": self.handle_message
            }
            
            handler = handlers.get(service)
            if handler:
                return handler(data)
            else:
                return {
                    "service": service,
                    "data": {
                        "status": "erro",
                        "timestamp": datetime.now().isoformat(),
                        "description": f"Serviço '{service}' não reconhecido"
                    }
                }
        
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e}")
            return {
                "service": "error",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": "Formato de mensagem inválido"
                }
            }
        except Exception as e:
            print(f"Erro ao processar requisição: {e}")
            return {
                "service": "error",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": str(e)
                }
            }
    
    def start(self):
        """Inicia o servidor"""
        # Conectar ao broker
        broker_address = os.getenv("BROKER_ADDRESS", "tcp://broker:5556")
        self.socket.connect(broker_address)
        print(f"Servidor conectado ao broker em {broker_address}")
        
        # Conectar ao proxy Pub/Sub
        proxy_address = os.getenv("PROXY_ADDRESS", "tcp://proxy:5557")
        self.pub_socket.connect(proxy_address)
        print(f"Servidor conectado ao proxy em {proxy_address}")
        
        print("Aguardando requisições...")
        
        try:
            while True:
                # Receber requisição
                message = self.socket.recv_string()
                
                # Processar requisição
                response = self.process_request(message)
                
                # Enviar resposta
                self.socket.send_json(response)
        
        except KeyboardInterrupt:
            print("\nServidor encerrado")
        finally:
            self.socket.close()
            self.pub_socket.close()
            self.context.term()

if __name__ == "__main__":
    server = MessageServer()
    server.start()