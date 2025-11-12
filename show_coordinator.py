#!/usr/bin/env python3
"""
Script simples para mostrar o coordenador atual do sistema.

Uso: python show_coordinator.py
"""

import zmq
import msgpack
from datetime import datetime

def get_servers_list():
    """Obtém lista de servidores do servidor de referência"""
    try:
        context = zmq.Context()
        ref_socket = context.socket(zmq.REQ)
        ref_socket.connect("tcp://localhost:5559")
        ref_socket.setsockopt(zmq.RCVTIMEO, 5000)

        request = {
            "service": "list",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "clock": 0
            }
        }

        ref_socket.send(msgpack.packb(request))
        response = msgpack.unpackb(ref_socket.recv(), raw=False)

        servers = response["data"]["list"]
        ref_socket.close()
        context.term()

        return sorted(servers, key=lambda s: s["rank"])

    except Exception as e:
        print(f"❌ Erro ao conectar com servidor de referência: {e}")
        return []

def get_coordinator_from_server(server_name):
    """Pergunta ao servidor quem é o coordenador"""
    try:
        context = zmq.Context()
        server_socket = context.socket(zmq.REQ)
        server_socket.connect(f"tcp://{server_name}:5561")
        server_socket.setsockopt(zmq.RCVTIMEO, 3000)

        request = {
            "service": "who_coordinator",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "clock": 0
            }
        }

        server_socket.send(msgpack.packb(request))
        response = msgpack.unpackb(server_socket.recv(), raw=False)

        coordinator = response["data"].get("coordinator")
        my_rank = response["data"].get("my_rank")

        server_socket.close()
        context.term()

        return coordinator, my_rank

    except Exception as e:
        return None, None

def main():
    print("\n" + "="*60)
    print("👑 ESTADO ATUAL DA ELEIÇÃO")
    print("="*60)

    # Obter lista de servidores
    servers = get_servers_list()

    if not servers:
        print("\n❌ Nenhum servidor ativo encontrado!")
        print("   Execute 'docker-compose up -d' primeiro.\n")
        return

    print(f"\n📋 Servidores registrados: {len(servers)}")
    print()

    # Consultar cada servidor
    coordinators = {}
    for server in servers:
        name = server["name"]
        rank = server["rank"]

        coord, _ = get_coordinator_from_server(name)

        if coord:
            coordinators[coord] = coordinators.get(coord, 0) + 1
            is_coord = "👑" if coord == name else "  "
            print(f"  {is_coord} {name:<20} (Rank {rank}) → Coordenador: {coord}")
        else:
            print(f"     {name:<20} (Rank {rank}) → Não respondeu")

    # Determinar coordenador eleito
    if coordinators:
        print("\n" + "-"*60)
        elected = max(coordinators, key=coordinators.get)
        votes = coordinators[elected]
        total = len(servers)

        print(f"👑 Coordenador Eleito: {elected}")
        print(f"📊 Consenso: {votes}/{total} servidores")

        # Verificar se é o esperado (maior rank)
        expected = servers[-1]["name"]
        if elected == expected:
            print(f"✅ Status: OK (coordenador é o servidor com maior rank)")
        else:
            print(f"⚠️  Status: Coordenador eleito ({elected}) não tem o maior rank")
            print(f"   Esperado: {expected} (Rank {servers[-1]['rank']})")

            # Verificar se esperado está online
            expected_online = any(s["name"] == expected for s in servers)
            if not expected_online:
                print(f"   Motivo: {expected} está offline")
            else:
                print(f"   Motivo: Eleição pode estar em andamento")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido\n")
    except Exception as e:
        print(f"\n❌ Erro: {e}\n")
