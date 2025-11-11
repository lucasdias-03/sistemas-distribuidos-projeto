#!/usr/bin/env python3
import zmq
import json  # Mantido apenas para persistência em disco
import msgpack
import os
import time
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock

class MessageServer:
    def __init__(self, data_dir="/data"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        # Socket PUB para publicações
        self.pub_socket = self.context.socket(zmq.PUB)
        
        # Socket REQ para comunicação com referência e outros servidores
        self.req_socket = self.context.socket(zmq.REQ)
        
        # Relógio lógico
        self.logical_clock = 0
        self.clock_lock = Lock()
        
        # Informações do servidor
        self.server_name = os.getenv("SERVER_NAME", f"servidor_{os.getpid()}")
        self.rank = None
        self.coordinator = None
        self.message_count = 0  # Contador para sincronização a cada 10 mensagens
        
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
        self.channels = self.load_data(self.channels_file, [], 'users')  # Note: usa 'users' conforme especificação
        self.logins = self.load_data(self.logins_file, [], 'logins')
        self.messages = self.load_data(self.messages_file, [], 'messages')
        self.publications = self.load_data(self.publications_file, [], 'publications')
        
        print(f"Servidor iniciado. Usuários: {len(self.users)}, Canais: {len(self.channels)}")
    
    def increment_clock(self):
        """Incrementa relógio lógico antes de enviar mensagem"""
        with self.clock_lock:
            self.logical_clock += 1
            return self.logical_clock
    
    def update_clock(self, received_clock):
        """Atualiza relógio lógico ao receber mensagem"""
        with self.clock_lock:
            self.logical_clock = max(self.logical_clock, received_clock) + 1
            return self.logical_clock
    
    def register_with_reference(self):
        """Registra servidor com o servidor de referência e obtém rank"""
        try:
            ref_address = os.getenv("REFERENCE_ADDRESS", "tcp://referencia:5559")
            ref_socket = self.context.socket(zmq.REQ)
            ref_socket.connect(ref_address)
            
            clock = self.increment_clock()
            request = {
                "service": "rank",
                "data": {
                    "user": self.server_name,
                    "timestamp": datetime.now().isoformat(),
                    "clock": clock
                }
            }
            
            ref_socket.send(msgpack.packb(request))
            response = msgpack.unpackb(ref_socket.recv(), raw=False)
            
            self.rank = response["data"]["rank"]
            self.update_clock(response["data"]["clock"])
            
            print(f"Servidor '{self.server_name}' registrado com rank {self.rank}")
            
            ref_socket.close()
            return True
            
        except Exception as e:
            print(f"Erro ao registrar com referência: {e}")
            return False
    
    def send_heartbeat(self):
        """Thread para enviar heartbeat periódico"""
        ref_address = os.getenv("REFERENCE_ADDRESS", "tcp://referencia:5559")
        heartbeat_socket = self.context.socket(zmq.REQ)
        heartbeat_socket.connect(ref_address)
        
        while True:
            try:
                time.sleep(5)  # Heartbeat a cada 5 segundos
                
                clock = self.increment_clock()
                request = {
                    "service": "heartbeat",
                    "data": {
                        "user": self.server_name,
                        "timestamp": datetime.now().isoformat(),
                        "clock": clock
                    }
                }
                
                heartbeat_socket.send(msgpack.packb(request))
                response = msgpack.unpackb(heartbeat_socket.recv(), raw=False)
                self.update_clock(response["data"]["clock"])
                
            except Exception as e:
                print(f"Erro no heartbeat: {e}")
                break
    
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
        received_clock = data.get("clock", 0)
        
        # Atualizar relógio lógico
        current_clock = self.update_clock(received_clock)
        
        if not user:
            return {
                "service": "login",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": "Nome de usuário não fornecido",
                    "clock": current_clock
                }
            }
        
        # Verificar se usuário já existe
        if user in self.users:
            return {
                "service": "login",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": "Usuário já cadastrado",
                    "clock": current_clock
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
        
        print(f"Login: {user} ({timestamp}) - Clock: {current_clock}")
        
        return {
            "service": "login",
            "data": {
                "status": "sucesso",
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }
    
    def handle_users(self, data):
        """Retorna lista de usuários"""
        received_clock = data.get("clock", 0)
        current_clock = self.update_clock(received_clock)
        
        return {
            "service": "users",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "users": self.users,
                "clock": current_clock
            }
        }
    
    def handle_channel(self, data):
        """Cria novo canal"""
        channel = data.get("channel")
        timestamp = data.get("timestamp")
        received_clock = data.get("clock", 0)
        
        current_clock = self.update_clock(received_clock)
        
        if not channel:
            return {
                "service": "channel",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": "Nome do canal não fornecido",
                    "clock": current_clock
                }
            }
        
        # Verificar se canal já existe
        if channel in self.channels:
            return {
                "service": "channel",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": "Canal já existe",
                    "clock": current_clock
                }
            }
        
        # Adicionar canal
        self.channels.append(channel)
        channels_data = {
            "service": "channels",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "users": self.channels
            }
        }
        self.save_data(self.channels_file, channels_data)

        print(f"Canal criado: {channel} ({timestamp}) - Clock: {current_clock}")
        
        return {
            "service": "channel",
            "data": {
                "status": "sucesso",
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }
    
    def handle_channels(self, data):
        """Retorna lista de canais"""
        received_clock = data.get("clock", 0)
        current_clock = self.update_clock(received_clock)
        
        return {
            "service": "channels",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "users": self.channels,
                "clock": current_clock
            }
        }
    
    def handle_publish(self, data):
        """Publica mensagem em canal"""
        user = data.get("user")
        channel = data.get("channel")
        message = data.get("message")
        timestamp = data.get("timestamp")
        received_clock = data.get("clock", 0)
        
        current_clock = self.update_clock(received_clock)
        
        if not channel or not message:
            return {
                "service": "publish",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Canal ou mensagem não fornecidos",
                    "clock": current_clock
                }
            }
        
        # Verificar se canal existe
        if channel not in self.channels:
            return {
                "service": "publish",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Canal não existe",
                    "clock": current_clock
                }
            }
        
        # Publicar no canal (tópico = nome do canal)
        pub_clock = self.increment_clock()
        publication = {
            "user": user,
            "message": message,
            "timestamp": timestamp,
            "clock": pub_clock
        }
        
        # Enviar para o proxy Pub/Sub (MessagePack)
        topic = channel
        self.pub_socket.send_string(topic, zmq.SNDMORE)
        self.pub_socket.send(msgpack.packb(publication))
        
        # Persistir publicação
        self.publications.append({
            "channel": channel,
            "user": user,
            "message": message,
            "timestamp": timestamp,
            "clock": pub_clock
        })
        publications_data = {
            "service": "publish",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "publications": self.publications
            }
        }
        self.save_data(self.publications_file, publications_data)
        
        print(f"Publicação no canal '{channel}' por {user}: {message} - Clock: {pub_clock}")
        
        return {
            "service": "publish",
            "data": {
                "status": "OK",
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }
    
    def handle_message(self, data):
        """Envia mensagem privada para usuário"""
        src = data.get("src")
        dst = data.get("dst")
        message = data.get("message")
        timestamp = data.get("timestamp")
        received_clock = data.get("clock", 0)
        
        current_clock = self.update_clock(received_clock)
        
        if not dst or not message:
            return {
                "service": "message",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Destinatário ou mensagem não fornecidos",
                    "clock": current_clock
                }
            }
        
        # Verificar se usuário existe
        if dst not in self.users:
            return {
                "service": "message",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Usuário não existe",
                    "clock": current_clock
                }
            }
        
        # Publicar para o usuário (tópico = nome do usuário)
        msg_clock = self.increment_clock()
        private_message = {
            "from": src,
            "message": message,
            "timestamp": timestamp,
            "clock": msg_clock
        }
        
        # Enviar para o proxy Pub/Sub (MessagePack)
        topic = dst
        self.pub_socket.send_string(topic, zmq.SNDMORE)
        self.pub_socket.send(msgpack.packb(private_message))
        
        # Persistir mensagem
        self.messages.append({
            "src": src,
            "dst": dst,
            "message": message,
            "timestamp": timestamp,
            "clock": msg_clock
        })
        messages_data = {
            "service": "message",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "messages": self.messages
            }
        }
        self.save_data(self.messages_file, messages_data)
        
        print(f"Mensagem de {src} para {dst}: {message} - Clock: {msg_clock}")
        
        return {
            "service": "message",
            "data": {
                "status": "OK",
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }
    
    def process_request(self, message):
        """Processa requisição recebida"""
        try:
            # Decodificar MessagePack
            request = msgpack.unpackb(message, raw=False)
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
        
        # Registrar com servidor de referência
        print("Registrando com servidor de referência...")
        if self.register_with_reference():
            # Iniciar thread de heartbeat
            heartbeat_thread = Thread(target=self.send_heartbeat, daemon=True)
            heartbeat_thread.start()
            print("Heartbeat iniciado")
        else:
            print("AVISO: Falha ao registrar com servidor de referência")
        
        print("Aguardando requisições... (usando MessagePack + Relógio Lógico)\n")
        
        try:
            while True:
                # Receber requisição (MessagePack binário)
                message = self.socket.recv()
                
                # Processar requisição
                response = self.process_request(message)
                
                # Incrementar contador de mensagens
                self.message_count += 1
                
                # Sincronizar relógio a cada 10 mensagens
                if self.message_count >= 10:
                    self.message_count = 0
                    # TODO: Implementar sincronização com coordenador (Parte 4)
                
                # Enviar resposta (MessagePack binário)
                self.socket.send(msgpack.packb(response))
        
        except KeyboardInterrupt:
            print("\nServidor encerrado")
        finally:
            self.socket.close()
            self.pub_socket.close()
            self.context.term()

if __name__ == "__main__":
    server = MessageServer()
    server.start()