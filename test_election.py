#!/usr/bin/env python3
"""
Script de teste para demonstrar a eleição usando o algoritmo Bully.

Este script:
1. Verifica os servidores registrados no servidor de referência
2. Simula a queda do coordenador atual (desligando-o)
3. Aguarda a eleição acontecer
4. Mostra o novo coordenador eleito

Para usar:
1. Certifique-se que o servidor de referência está rodando
2. Certifique-se que os servidores estão rodando (docker-compose up)
3. Execute: python test_election.py
"""

import zmq
import msgpack
import time
import sys
import subprocess
from datetime import datetime

class ElectionTester:
    def __init__(self):
        self.context = zmq.Context()
        self.logical_clock = 0

    def increment_clock(self):
        """Incrementa relógio lógico"""
        self.logical_clock += 1
        return self.logical_clock

    def update_clock(self, received_clock):
        """Atualiza relógio lógico"""
        self.logical_clock = max(self.logical_clock, received_clock) + 1
        return self.logical_clock

    def get_servers_list(self):
        """Obtém lista de servidores do servidor de referência"""
        try:
            ref_socket = self.context.socket(zmq.REQ)
            ref_socket.connect("tcp://localhost:5559")
            ref_socket.setsockopt(zmq.RCVTIMEO, 5000)

            clock = self.increment_clock()
            request = {
                "service": "list",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "clock": clock
                }
            }

            ref_socket.send(msgpack.packb(request))
            response = msgpack.unpackb(ref_socket.recv(), raw=False)

            self.update_clock(response["data"]["clock"])
            servers = response["data"]["list"]

            ref_socket.close()
            return servers

        except Exception as e:
            print(f"❌ Erro ao obter lista de servidores: {e}")
            print("   Certifique-se que o servidor de referência está rodando!")
            return []

    def get_coordinator(self, server_name):
        """Pergunta ao servidor quem é o coordenador atual"""
        try:
            # Conectar diretamente ao servidor (porta 5561 - servidor-servidor)
            server_socket = self.context.socket(zmq.REQ)
            server_socket.connect(f"tcp://{server_name}:5561")
            server_socket.setsockopt(zmq.RCVTIMEO, 3000)

            clock = self.increment_clock()
            request = {
                "service": "who_coordinator",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "clock": clock
                }
            }

            server_socket.send(msgpack.packb(request))
            response = msgpack.unpackb(server_socket.recv(), raw=False)

            coordinator = response["data"].get("coordinator")

            server_socket.close()
            return coordinator

        except Exception as e:
            print(f"   ⚠️  Servidor {server_name} não está respondendo")
            return None

    def stop_server(self, server_name):
        """Para um servidor usando docker-compose"""
        try:
            print(f"\n🔴 Parando servidor {server_name}...")
            result = subprocess.run(
                ["docker-compose", "stop", server_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(f"✅ Servidor {server_name} parado com sucesso!")
                return True
            else:
                print(f"❌ Erro ao parar servidor: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Erro ao parar servidor {server_name}: {e}")
            return False

    def start_server(self, server_name):
        """Inicia um servidor usando docker-compose"""
        try:
            print(f"\n🟢 Iniciando servidor {server_name}...")
            result = subprocess.run(
                ["docker-compose", "start", server_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(f"✅ Servidor {server_name} iniciado com sucesso!")
                return True
            else:
                print(f"❌ Erro ao iniciar servidor: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Erro ao iniciar servidor {server_name}: {e}")
            return False

    def monitor_election(self):
        """Monitora o processo de eleição"""
        print("\n" + "="*70)
        print("🗳️  TESTE DE ELEIÇÃO - ALGORITMO BULLY")
        print("="*70)

        # Passo 1: Verificar servidores registrados
        print("\n📋 Passo 1: Verificando servidores registrados...")
        servers = self.get_servers_list()

        if not servers:
            print("❌ Nenhum servidor encontrado!")
            print("   Execute 'docker-compose up -d' primeiro.")
            return

        # Ordenar por rank
        servers.sort(key=lambda s: s["rank"])

        print(f"\n✅ Encontrados {len(servers)} servidores:")
        for server in servers:
            print(f"   • {server['name']:<20} (Rank: {server['rank']})")

        # Identificar coordenador atual (maior rank)
        current_coordinator = servers[-1]["name"]  # Servidor com maior rank
        print(f"\n👑 Coordenador esperado (maior rank): {current_coordinator}")

        # Aguardar um pouco para a eleição inicial terminar
        print("\n⏳ Aguardando eleição inicial (5 segundos)...")
        time.sleep(5)

        # Passo 2: Confirmar quem é o coordenador antes de parar
        print("\n📋 Passo 2: Confirmando coordenador atual...")
        for server in servers:
            coord = self.get_coordinator(server["name"])
            if coord:
                print(f"   • {server['name']} diz que o coordenador é: {coord}")

        # Passo 3: Simular falha do coordenador
        print("\n" + "="*70)
        print("💥 Passo 3: Simulando falha do coordenador...")
        print("="*70)

        if not self.stop_server(current_coordinator):
            print("❌ Não foi possível parar o coordenador. Abortando teste.")
            return

        # Passo 4: Aguardar eleição
        print("\n⏳ Aguardando processo de eleição (15 segundos)...")
        print("   Durante este tempo, o servidor com segundo maior rank deve:")
        print("   1. Detectar que o coordenador falhou")
        print("   2. Iniciar uma eleição")
        print("   3. Assumir como novo coordenador")

        for i in range(15, 0, -1):
            print(f"   ⏰ {i} segundos restantes...", end='\r')
            time.sleep(1)
        print("\n")

        # Passo 5: Verificar novo coordenador
        print("="*70)
        print("🔍 Passo 5: Verificando novo coordenador...")
        print("="*70)

        # Obter lista atualizada (sem o servidor parado)
        active_servers = self.get_servers_list()

        if active_servers:
            active_servers.sort(key=lambda s: s["rank"])
            expected_new_coordinator = active_servers[-1]["name"]

            print(f"\n✅ Servidores ativos após eleição:")
            for server in active_servers:
                print(f"   • {server['name']:<20} (Rank: {server['rank']})")

            print(f"\n👑 Novo coordenador esperado: {expected_new_coordinator}")

            # Perguntar a cada servidor quem é o coordenador
            print("\n📊 Consultando servidores sobre o coordenador atual:")
            coordinators = {}
            for server in active_servers:
                coord = self.get_coordinator(server["name"])
                if coord:
                    print(f"   • {server['name']} → Coordenador: {coord}")
                    coordinators[coord] = coordinators.get(coord, 0) + 1

            # Verificar consenso
            if coordinators:
                most_voted = max(coordinators, key=coordinators.get)
                votes = coordinators[most_voted]
                total = len(active_servers)

                print(f"\n📊 Resultado da eleição:")
                print(f"   • Coordenador eleito: {most_voted}")
                print(f"   • Consenso: {votes}/{total} servidores")

                if most_voted == expected_new_coordinator:
                    print(f"\n✅ SUCESSO! Eleição funcionou corretamente!")
                    print(f"   O servidor com maior rank ({expected_new_coordinator}) assumiu como coordenador.")
                else:
                    print(f"\n⚠️  AVISO: Coordenador eleito ({most_voted}) não é o esperado ({expected_new_coordinator})")

        # Passo 6: Opção de reiniciar o servidor parado
        print("\n" + "="*70)
        print("🔄 Passo 6: Reiniciando servidor original...")
        print("="*70)

        if self.start_server(current_coordinator):
            print("\n⏳ Aguardando servidor reiniciar e se registrar (10 segundos)...")
            time.sleep(10)

            # Verificar se uma nova eleição ocorreu
            print("\n🔍 Verificando se nova eleição ocorreu...")
            servers = self.get_servers_list()
            servers.sort(key=lambda s: s["rank"])

            print(f"\n✅ Servidores ativos:")
            for server in servers:
                coord = self.get_coordinator(server["name"])
                status = f"→ Coordenador: {coord}" if coord else "→ Não respondeu"
                print(f"   • {server['name']:<20} (Rank: {server['rank']}) {status}")

            expected_final_coordinator = servers[-1]["name"]
            print(f"\n👑 Coordenador esperado agora: {expected_final_coordinator}")

            if expected_final_coordinator == current_coordinator:
                print("\n✅ O servidor original deve iniciar uma nova eleição e reassumir como coordenador")
                print("   (pode levar alguns momentos para a eleição acontecer)")

        print("\n" + "="*70)
        print("✅ Teste de eleição concluído!")
        print("="*70)
        print("\n💡 Dicas para observar a eleição:")
        print("   • Use 'docker-compose logs -f servidor_1 servidor_2 servidor_3'")
        print("   • Procure por mensagens [ELEIÇÃO] nos logs")
        print("   • Observe o fluxo de mensagens OK e anúncio do coordenador")
        print("\n")

def main():
    tester = ElectionTester()

    try:
        tester.monitor_election()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.context.term()

if __name__ == "__main__":
    main()
