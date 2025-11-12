#!/usr/bin/env python3
import zmq
import msgpack
import time
from datetime import datetime
from threading import Thread, Lock

class ReferenceServer:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.pub_socket = self.context.socket(zmq.PUB)
        
        # Relógio lógico
        self.logical_clock = 0
        self.clock_lock = Lock()
        
        # Registro de servidores
        self.servers = {}  # {name: {"rank": int, "last_heartbeat": timestamp}}
        self.servers_lock = Lock()
        self.next_rank = 1
        
        print("Servidor de Referência iniciado")
    
    def increment_clock(self):
        """Incrementa o relógio lógico"""
        with self.clock_lock:
            self.logical_clock += 1
            return self.logical_clock
    
    def update_clock(self, received_clock):
        """Atualiza relógio lógico baseado no recebido"""
        with self.clock_lock:
            self.logical_clock = max(self.logical_clock, received_clock) + 1
            return self.logical_clock
    
    def handle_rank(self, data):
        """Atribui rank a um servidor"""
        user = data.get("user")
        received_clock = data.get("clock", 0)
        
        # Atualizar relógio lógico
        current_clock = self.update_clock(received_clock)
        
        with self.servers_lock:
            if user not in self.servers:
                # Novo servidor - atribuir rank
                rank = self.next_rank
                self.next_rank += 1
                self.servers[user] = {
                    "rank": rank,
                    "last_heartbeat": time.time()
                }
                print(f"Servidor '{user}' registrado com rank {rank}")
            else:
                # Servidor já existe - retornar rank existente
                rank = self.servers[user]["rank"]
                self.servers[user]["last_heartbeat"] = time.time()
        
        return {
            "service": "rank",
            "data": {
                "rank": rank,
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }
    
    def handle_list(self, data):
        """Retorna lista de servidores"""
        received_clock = data.get("clock", 0)
        current_clock = self.update_clock(received_clock)
        
        with self.servers_lock:
            # Limpar servidores inativos (sem heartbeat há mais de 30s)
            current_time = time.time()
            active_servers = {
                name: info for name, info in self.servers.items()
                if current_time - info["last_heartbeat"] < 30
            }
            
            # Atualizar lista
            self.servers = active_servers
            
            # Criar lista de servidores
            server_list = [
                {"name": name, "rank": info["rank"]}
                for name, info in self.servers.items()
            ]
        
        print(f"Lista de servidores: {len(server_list)} ativos")
        
        return {
            "service": "list",
            "data": {
                "list": server_list,
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }
    
    def handle_heartbeat(self, data):
        """Processa heartbeat de servidor"""
        user = data.get("user")
        received_clock = data.get("clock", 0)
        
        current_clock = self.update_clock(received_clock)
        
        with self.servers_lock:
            if user in self.servers:
                self.servers[user]["last_heartbeat"] = time.time()
                # print(f"Heartbeat recebido de '{user}'")
            else:
                print(f"Heartbeat de servidor não registrado: '{user}'")
        
        return {
            "service": "heartbeat",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "clock": current_clock
            }
        }
    
    def process_request(self, message):
        """Processa requisição recebida"""
        try:
            request = msgpack.unpackb(message, raw=False)
            service = request.get("service")
            data = request.get("data", {})
            
            # print(f"Requisição: {service}")
            
            handlers = {
                "rank": self.handle_rank,
                "list": self.handle_list,
                "heartbeat": self.handle_heartbeat
            }
            
            handler = handlers.get(service)
            if handler:
                return handler(data)
            else:
                current_clock = self.increment_clock()
                return {
                    "service": service,
                    "data": {
                        "status": "erro",
                        "timestamp": datetime.now().isoformat(),
                        "description": f"Serviço '{service}' não reconhecido",
                        "clock": current_clock
                    }
                }
        
        except Exception as e:
            print(f"Erro ao processar requisição: {e}")
            current_clock = self.increment_clock()
            return {
                "service": "error",
                "data": {
                    "status": "erro",
                    "timestamp": datetime.now().isoformat(),
                    "description": str(e),
                    "clock": current_clock
                }
            }
    
    def cleanup_servers(self):
        """Thread para limpar servidores inativos periodicamente"""
        while True:
            time.sleep(10)  # Verificar a cada 10 segundos
            
            with self.servers_lock:
                current_time = time.time()
                inactive = []
                
                for name, info in self.servers.items():
                    if current_time - info["last_heartbeat"] > 30:
                        inactive.append(name)
                
                for name in inactive:
                    print(f"Servidor '{name}' removido por inatividade")
                    del self.servers[name]
    
    def start(self):
        """Inicia o servidor de referência"""
        
        self.socket.bind("tcp://*:5559")
        print("Socket REP escutando na porta 5559")
        
        
        self.pub_socket.bind("tcp://*:5560")
        print("Socket PUB na porta 5560")
        
        
        cleanup_thread = Thread(target=self.cleanup_servers, daemon=True)
        cleanup_thread.start()
        
        print("Servidor de Referência pronto!\n")
        
        try:
            while True:
                # Receber requisição
                message = self.socket.recv()
                
                # Processar
                response = self.process_request(message)
                
                # Enviar resposta
                self.socket.send(msgpack.packb(response))
        
        except KeyboardInterrupt:
            print("\nServidor de Referência encerrado")
        finally:
            self.socket.close()
            self.pub_socket.close()
            self.context.term()

if __name__ == "__main__":
    server = ReferenceServer()
    server.start()