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

        # Socket SUB para receber notificações de eleição
        self.sub_socket = self.context.socket(zmq.SUB)

        # Socket REQ para comunicação com referência e outros servidores
        self.req_socket = self.context.socket(zmq.REQ)

        # Relógio lógico
        self.logical_clock = 0
        self.clock_lock = Lock()

        # Relógio físico sincronizado
        self.physical_clock_offset = 0.0  # Offset em relação ao relógio do sistema
        self.physical_clock_lock = Lock()

        # Informações do servidor
        self.server_name = os.getenv("SERVER_NAME", f"servidor_{os.getpid()}")
        self.rank = None
        self.coordinator = None
        self.coordinator_lock = Lock()
        self.servers_list = []  # Lista de outros servidores
        self.servers_lock = Lock()
        self.message_count = 0  # Contador para sincronização a cada 10 mensagens
        self.in_election = False  # Flag para evitar eleições simultâneas
        
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

    def get_physical_time(self):
        """Retorna o relógio físico sincronizado"""
        with self.physical_clock_lock:
            return time.time() + self.physical_clock_offset

    def set_physical_clock_offset(self, offset):
        """Ajusta o offset do relógio físico"""
        with self.physical_clock_lock:
            self.physical_clock_offset = offset
            print(f"Relógio físico ajustado. Offset: {offset:.6f}s")
    
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

    def get_servers_list(self):
        """Obtém lista de servidores do servidor de referência"""
        try:
            ref_address = os.getenv("REFERENCE_ADDRESS", "tcp://referencia:5559")
            list_socket = self.context.socket(zmq.REQ)
            list_socket.connect(ref_address)

            clock = self.increment_clock()
            request = {
                "service": "list",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "clock": clock
                }
            }

            list_socket.send(msgpack.packb(request))
            response = msgpack.unpackb(list_socket.recv(), raw=False)

            self.update_clock(response["data"]["clock"])

            with self.servers_lock:
                self.servers_list = response["data"]["list"]

            list_socket.close()
            return self.servers_list

        except Exception as e:
            print(f"Erro ao obter lista de servidores: {e}")
            return []

    def start_election(self):
        """Inicia processo de eleição (Algoritmo Bully)"""
        if self.in_election:
            return  # Já está em processo de eleição

        self.in_election = True
        print(f"\n[ELEIÇÃO] Iniciando eleição... (Rank: {self.rank})")

        try:
            # Obter lista de servidores
            servers = self.get_servers_list()

            # Encontrar servidores com rank maior
            higher_rank_servers = [s for s in servers if s["rank"] > self.rank]

            if not higher_rank_servers:
                # Este servidor tem o maior rank - torna-se coordenador
                self.become_coordinator()
                return

            # Enviar mensagem de eleição para servidores com rank maior
            received_ok = False
            for server in higher_rank_servers:
                try:
                    # Conectar ao servidor
                    server_address = f"tcp://{server['name']}:5561"
                    election_socket = self.context.socket(zmq.REQ)
                    election_socket.setsockopt(zmq.RCVTIMEO, 2000)  # Timeout de 2s
                    election_socket.connect(server_address)

                    clock = self.increment_clock()
                    request = {
                        "service": "election",
                        "data": {
                            "timestamp": datetime.now().isoformat(),
                            "clock": clock
                        }
                    }

                    election_socket.send(msgpack.packb(request))
                    response = msgpack.unpackb(election_socket.recv(), raw=False)

                    if response["data"].get("election") == "OK":
                        received_ok = True
                        self.update_clock(response["data"]["clock"])

                    election_socket.close()

                except Exception as e:
                    print(f"[ELEIÇÃO] Servidor {server['name']} não respondeu: {e}")
                    continue

            if not received_ok:
                # Nenhum servidor com rank maior respondeu - torna-se coordenador
                self.become_coordinator()
            else:
                print(f"[ELEIÇÃO] Aguardando coordenador ser anunciado...")

        finally:
            self.in_election = False

    def become_coordinator(self):
        """Torna este servidor o coordenador"""
        with self.coordinator_lock:
            self.coordinator = self.server_name

        print(f"\n[ELEIÇÃO] '{self.server_name}' é o novo COORDENADOR!\n")

        # Anunciar para todos os servidores via tópico 'servers'
        clock = self.increment_clock()
        announcement = {
            "service": "election",
            "data": {
                "coordinator": self.server_name,
                "timestamp": datetime.now().isoformat(),
                "clock": clock
            }
        }

        # Publicar no tópico 'servers'
        self.pub_socket.send_string("servers", zmq.SNDMORE)
        self.pub_socket.send(msgpack.packb(announcement))

        print(f"[ELEIÇÃO] Coordenador anunciado no tópico 'servers'")

    def handle_election_request(self, data):
        """Responde a requisição de eleição de outro servidor"""
        received_clock = data.get("clock", 0)
        current_clock = self.update_clock(received_clock)

        print(f"[ELEIÇÃO] Recebida requisição de eleição")

        # Responder OK
        response = {
            "service": "election",
            "data": {
                "election": "OK",
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }

        # Iniciar própria eleição em thread separada
        Thread(target=self.start_election, daemon=True).start()

        return response

    def handle_clock_request(self, data):
        """Responde a requisição de sincronização de relógio"""
        received_clock = data.get("clock", 0)
        current_clock = self.update_clock(received_clock)

        # Retornar o relógio físico atual
        current_time = self.get_physical_time()

        return {
            "service": "clock",
            "data": {
                "time": current_time,
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }

    def synchronize_clocks_berkeley(self):
        """Sincroniza relógios usando algoritmo de Berkeley (apenas coordenador)"""
        with self.coordinator_lock:
            if self.coordinator != self.server_name:
                return  # Apenas coordenador sincroniza

        print(f"\n[BERKELEY] Iniciando sincronização de relógios...")

        try:
            servers = self.get_servers_list()
            times = []
            my_time = self.get_physical_time()
            times.append(my_time)

            # Coletar tempo de todos os servidores
            for server in servers:
                if server["name"] == self.server_name:
                    continue

                try:
                    server_address = f"tcp://{server['name']}:5561"
                    clock_socket = self.context.socket(zmq.REQ)
                    clock_socket.setsockopt(zmq.RCVTIMEO, 2000)
                    clock_socket.connect(server_address)

                    clock = self.increment_clock()
                    request = {
                        "service": "clock",
                        "data": {
                            "timestamp": datetime.now().isoformat(),
                            "clock": clock
                        }
                    }

                    clock_socket.send(msgpack.packb(request))
                    response = msgpack.unpackb(clock_socket.recv(), raw=False)

                    server_time = response["data"]["time"]
                    times.append(server_time)
                    self.update_clock(response["data"]["clock"])

                    print(f"[BERKELEY] Tempo de {server['name']}: {server_time:.6f}")

                    clock_socket.close()

                except Exception as e:
                    print(f"[BERKELEY] Erro ao coletar tempo de {server['name']}: {e}")
                    continue

            # Calcular média
            if len(times) > 0:
                avg_time = sum(times) / len(times)
                print(f"[BERKELEY] Tempo médio: {avg_time:.6f}")

                # Calcular offset para este servidor
                my_offset = avg_time - time.time()
                self.set_physical_clock_offset(my_offset)

                # Enviar ajustes para outros servidores
                for server in servers:
                    if server["name"] == self.server_name:
                        continue

                    # TODO: Enviar ajuste para cada servidor
                    # Por simplicidade, cada servidor ajusta ao receber tempo médio

        except Exception as e:
            print(f"[BERKELEY] Erro na sincronização: {e}")

    def request_clock_sync(self):
        """Solicita sincronização de relógio ao coordenador"""
        with self.coordinator_lock:
            if not self.coordinator or self.coordinator == self.server_name:
                return  # Sem coordenador ou este é o coordenador

            coordinator_name = self.coordinator

        try:
            coordinator_address = f"tcp://{coordinator_name}:5561"
            clock_socket = self.context.socket(zmq.REQ)
            clock_socket.setsockopt(zmq.RCVTIMEO, 2000)
            clock_socket.connect(coordinator_address)

            clock = self.increment_clock()
            request = {
                "service": "clock",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "clock": clock
                }
            }

            t1 = time.time()
            clock_socket.send(msgpack.packb(request))
            response = msgpack.unpackb(clock_socket.recv(), raw=False)
            t2 = time.time()

            coordinator_time = response["data"]["time"]
            rtt = t2 - t1

            # Ajustar relógio considerando RTT
            adjusted_time = coordinator_time + (rtt / 2)
            offset = adjusted_time - time.time()
            self.set_physical_clock_offset(offset)

            self.update_clock(response["data"]["clock"])
            clock_socket.close()

        except Exception as e:
            print(f"[SYNC] Erro ao sincronizar com coordenador: {e}")
            # Coordenador pode estar offline - iniciar eleição
            Thread(target=self.start_election, daemon=True).start()

    def listen_to_servers_topic(self):
        """Thread para escutar anúncios de eleição no tópico 'servers'"""
        print(f"[SERVIDOR] Thread listen_to_servers_topic iniciada para {self.server_name}")
        while True:
            try:
                print(f"[SERVIDOR] {self.server_name} aguardando mensagens no tópico 'servers'...")
                topic, msg = self.sub_socket.recv_multipart()
                topic_str = topic.decode('utf-8')

                print(f"[SERVIDOR] {self.server_name} recebeu mensagem no tópico '{topic_str}'")

                if topic_str == "servers":
                    data = msgpack.unpackb(msg, raw=False)
                    service_type = data.get("service")

                    print(f"[SERVIDOR] {self.server_name} processando service_type: {service_type}")

                    if service_type == "election":
                        new_coordinator = data["data"].get("coordinator")

                        if new_coordinator:
                            with self.coordinator_lock:
                                self.coordinator = new_coordinator

                            self.update_clock(data["data"].get("clock", 0))
                            print(f"\n[ELEIÇÃO] Novo coordenador anunciado: {new_coordinator}\n")
                            self.in_election = False

                    elif service_type == "replication":
                        print(f"[SERVIDOR] {self.server_name} chamando handle_replication")
                        # Receber operação de replicação
                        self.handle_replication(data["data"])

            except Exception as e:
                print(f"[ERRO] {self.server_name} - Erro ao escutar tópico 'servers': {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)

    def replicate_operation(self, operation_type, operation_data):
        """Propaga operação para outros servidores via tópico 'servers'"""
        try:
            clock = self.increment_clock()
            replication_msg = {
                "service": "replication",
                "data": {
                    "server": self.server_name,
                    "operation": operation_type,
                    "operation_data": operation_data,
                    "timestamp": datetime.now().isoformat(),
                    "clock": clock
                }
            }

            # Publicar no tópico 'servers'
            self.pub_socket.send_string("servers", zmq.SNDMORE)
            self.pub_socket.send(msgpack.packb(replication_msg))

        except Exception as e:
            print(f"[REPLICAÇÃO] ERRO ao propagar {operation_type}: {e}")
            import traceback
            traceback.print_exc()

    def handle_replication(self, data):
        """Processa operação de replicação recebida de outro servidor"""
        try:
            server = data.get("server")
            operation = data.get("operation")
            operation_data = data.get("operation_data")
            received_clock = data.get("clock", 0)

            # Ignorar próprias operações
            if server == self.server_name:
                return

            print(f"[REPLICAÇÃO] {operation} de {server}: {operation_data}")

            # Atualizar relógio lógico
            self.update_clock(received_clock)

            # Aplicar operação baseada no tipo
            if operation == "login":
                self._apply_login_replication(operation_data)
            elif operation == "channel":
                self._apply_channel_replication(operation_data)
            elif operation == "publish":
                self._apply_publish_replication(operation_data)
            elif operation == "message":
                self._apply_message_replication(operation_data)

        except Exception as e:
            print(f"[REPLICAÇÃO] ERRO ao processar {operation}: {e}")
            import traceback
            traceback.print_exc()

    def _apply_login_replication(self, data):
        """Aplica replicação de login"""
        user = data.get("user")
        timestamp = data.get("timestamp")

        if user and user not in self.users:
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

    def _apply_channel_replication(self, data):
        """Aplica replicação de criação de canal"""
        channel = data.get("channel")

        if channel and channel not in self.channels:
            self.channels.append(channel)
            channels_data = {
                "service": "channels",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "users": self.channels
                }
            }
            self.save_data(self.channels_file, channels_data)

    def _apply_publish_replication(self, data):
        """Aplica replicação de publicação"""
        channel = data.get("channel")
        user = data.get("user")
        message = data.get("message")
        timestamp = data.get("timestamp")
        clock = data.get("clock")

        # Verificar se já existe (evitar duplicação)
        exists = any(
            p.get("channel") == channel and
            p.get("user") == user and
            p.get("message") == message and
            p.get("timestamp") == timestamp
            for p in self.publications
        )

        if not exists:
            self.publications.append({
                "channel": channel,
                "user": user,
                "message": message,
                "timestamp": timestamp,
                "clock": clock
            })
            publications_data = {
                "service": "publish",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "publications": self.publications
                }
            }
            self.save_data(self.publications_file, publications_data)

    def _apply_message_replication(self, data):
        """Aplica replicação de mensagem privada"""
        src = data.get("src")
        dst = data.get("dst")
        message = data.get("message")
        timestamp = data.get("timestamp")
        clock = data.get("clock")

        # Verificar se já existe (evitar duplicação)
        exists = any(
            m.get("src") == src and
            m.get("dst") == dst and
            m.get("message") == message and
            m.get("timestamp") == timestamp
            for m in self.messages
        )

        if not exists:
            self.messages.append({
                "src": src,
                "dst": dst,
                "message": message,
                "timestamp": timestamp,
                "clock": clock
            })
            messages_data = {
                "service": "message",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "messages": self.messages
                }
            }
            self.save_data(self.messages_file, messages_data)

    def request_full_sync(self):
        """Solicita sincronização completa de dados de outro servidor"""
        try:
            servers = self.get_servers_list()

            # Tentar sincronizar com cada servidor
            for server in servers:
                if server["name"] == self.server_name:
                    continue

                try:
                    server_address = f"tcp://{server['name']}:5561"
                    sync_socket = self.context.socket(zmq.REQ)
                    sync_socket.setsockopt(zmq.RCVTIMEO, 5000)
                    sync_socket.connect(server_address)

                    clock = self.increment_clock()
                    request = {
                        "service": "sync",
                        "data": {
                            "timestamp": datetime.now().isoformat(),
                            "clock": clock
                        }
                    }

                    sync_socket.send(msgpack.packb(request))
                    response = msgpack.unpackb(sync_socket.recv(), raw=False)

                    # Aplicar dados recebidos
                    self._apply_full_sync(response["data"])
                    self.update_clock(response["data"]["clock"])

                    sync_socket.close()
                    print(f"[SYNC] Sincronização completa realizada com {server['name']}")
                    return True

                except Exception as e:
                    print(f"[SYNC] Erro ao sincronizar com {server['name']}: {e}")
                    continue

            return False

        except Exception as e:
            print(f"[SYNC] Erro na sincronização completa: {e}")
            return False

    def _apply_full_sync(self, data):
        """Aplica dados recebidos de sincronização completa"""
        # Mesclar usuários
        remote_users = data.get("users", [])
        for user in remote_users:
            if user not in self.users:
                self.users.append(user)

        # Mesclar canais
        remote_channels = data.get("channels", [])
        for channel in remote_channels:
            if channel not in self.channels:
                self.channels.append(channel)

        # Mesclar logins (ordenar por timestamp)
        remote_logins = data.get("logins", [])
        all_logins = self.logins + remote_logins
        # Remover duplicatas mantendo o mais antigo
        seen = {}
        for login in all_logins:
            key = (login["user"], login["timestamp"])
            if key not in seen:
                seen[key] = login
        self.logins = list(seen.values())

        # Mesclar mensagens (ordenar por clock)
        remote_messages = data.get("messages", [])
        all_messages = self.messages + remote_messages
        seen_messages = {}
        for msg in all_messages:
            key = (msg["src"], msg["dst"], msg["message"], msg["timestamp"])
            if key not in seen_messages:
                seen_messages[key] = msg
        self.messages = list(seen_messages.values())
        self.messages.sort(key=lambda x: x.get("clock", 0))

        # Mesclar publicações (ordenar por clock)
        remote_publications = data.get("publications", [])
        all_publications = self.publications + remote_publications
        seen_pubs = {}
        for pub in all_publications:
            key = (pub["channel"], pub["user"], pub["message"], pub["timestamp"])
            if key not in seen_pubs:
                seen_pubs[key] = pub
        self.publications = list(seen_pubs.values())
        self.publications.sort(key=lambda x: x.get("clock", 0))

        # Salvar tudo
        self.save_data(self.users_file, {
            "service": "users",
            "data": {"timestamp": datetime.now().isoformat(), "users": self.users}
        })
        self.save_data(self.channels_file, {
            "service": "channels",
            "data": {"timestamp": datetime.now().isoformat(), "users": self.channels}
        })
        self.save_data(self.logins_file, {
            "service": "login",
            "data": {"timestamp": datetime.now().isoformat(), "logins": self.logins}
        })
        self.save_data(self.messages_file, {
            "service": "message",
            "data": {"timestamp": datetime.now().isoformat(), "messages": self.messages}
        })
        self.save_data(self.publications_file, {
            "service": "publish",
            "data": {"timestamp": datetime.now().isoformat(), "publications": self.publications}
        })

    def handle_sync_request(self, data):
        """Responde a requisição de sincronização completa"""
        received_clock = data.get("clock", 0)
        current_clock = self.update_clock(received_clock)

        return {
            "service": "sync",
            "data": {
                "users": self.users,
                "channels": self.channels,
                "logins": self.logins,
                "messages": self.messages,
                "publications": self.publications,
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }

    def handle_who_coordinator(self, data):
        """Responde quem é o coordenador atual"""
        received_clock = data.get("clock", 0)
        current_clock = self.update_clock(received_clock)

        with self.coordinator_lock:
            coordinator = self.coordinator

        return {
            "service": "who_coordinator",
            "data": {
                "coordinator": coordinator,
                "my_rank": self.rank,
                "my_name": self.server_name,
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }

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

        # Replicar operação para outros servidores (síncrono)
        self.replicate_operation("login", {"user": user, "timestamp": timestamp})

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

        # Replicar operação para outros servidores (síncrono)
        self.replicate_operation("channel", {"channel": channel})

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

        # Replicar operação para outros servidores (síncrono)
        self.replicate_operation("publish", {
            "channel": channel,
            "user": user,
            "message": message,
            "timestamp": timestamp,
            "clock": pub_clock
        })

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

        # Replicar operação para outros servidores (síncrono)
        self.replicate_operation("message", {
            "src": src,
            "dst": dst,
            "message": message,
            "timestamp": timestamp,
            "clock": msg_clock
        })

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
                "message": self.handle_message,
                "election": self.handle_election_request,
                "clock": self.handle_clock_request,
                "sync": self.handle_sync_request,
                "who_coordinator": self.handle_who_coordinator
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
    
    def server_to_server_handler(self):
        """Thread para processar requisições de outros servidores (eleição e clock)"""
        # Criar socket REP para comunicação entre servidores
        s2s_socket = self.context.socket(zmq.REP)
        s2s_socket.bind("tcp://*:5561")
        print(f"Socket servidor-servidor escutando na porta 5561")

        while True:
            try:
                # Receber requisição
                message = s2s_socket.recv()

                # Processar
                response = self.process_request(message)

                # Enviar resposta
                s2s_socket.send(msgpack.packb(response))

            except Exception as e:
                print(f"Erro no handler servidor-servidor: {e}")

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

        # Conectar ao proxy SUB para escutar tópico 'servers'
        # Nota: PROXY_ADDRESS é para PUB (5557), mas SUB precisa conectar em 5558
        proxy_sub_address = os.getenv("PROXY_SUB_ADDRESS", "tcp://proxy:5558")
        self.sub_socket.connect(proxy_sub_address)
        self.sub_socket.subscribe("servers")
        print(f"Inscrito no tópico 'servers' em {proxy_sub_address}")

        # Registrar com servidor de referência
        print("Registrando com servidor de referência...")
        if self.register_with_reference():
            # Iniciar thread de heartbeat
            heartbeat_thread = Thread(target=self.send_heartbeat, daemon=True)
            heartbeat_thread.start()
            print("Heartbeat iniciado")
        else:
            print("AVISO: Falha ao registrar com servidor de referência")

        # Iniciar thread para escutar tópico 'servers'
        servers_thread = Thread(target=self.listen_to_servers_topic, daemon=True)
        servers_thread.start()
        print("Escutando tópico 'servers'")

        # Iniciar thread para comunicação servidor-servidor
        s2s_thread = Thread(target=self.server_to_server_handler, daemon=True)
        s2s_thread.start()
        print("Handler servidor-servidor iniciado")

        # Aguardar um pouco para outros servidores iniciarem
        print("Aguardando outros servidores... (5s)")
        time.sleep(5)

        # Sincronização inicial de dados
        print("Solicitando sincronização completa de dados...")
        if self.request_full_sync():
            print("Sincronização inicial concluída com sucesso")
        else:
            print("Nenhum servidor disponível para sincronização (servidor pode ser o primeiro)")

        # Iniciar eleição
        print("Iniciando processo de eleição...")
        Thread(target=self.start_election, daemon=True).start()

        print("Aguardando requisições... (MessagePack + Relógio Lógico + Berkeley + Replicação)\n")

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

                    # Se for coordenador, sincronizar todos usando Berkeley
                    with self.coordinator_lock:
                        if self.coordinator == self.server_name:
                            Thread(target=self.synchronize_clocks_berkeley, daemon=True).start()
                        elif self.coordinator:
                            # Se não for coordenador, sincronizar com o coordenador
                            Thread(target=self.request_clock_sync, daemon=True).start()

                # Enviar resposta (MessagePack binário)
                self.socket.send(msgpack.packb(response))

        except KeyboardInterrupt:
            print("\nServidor encerrado")
        finally:
            self.socket.close()
            self.pub_socket.close()
            self.sub_socket.close()
            self.context.term()

if __name__ == "__main__":
    server = MessageServer()
    server.start()