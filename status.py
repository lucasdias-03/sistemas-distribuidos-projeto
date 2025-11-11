#!/usr/bin/env python3
"""
Script para monitorar o status do sistema de mensagens distribuído
"""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def print_banner():
    """Exibe banner"""
    print("=" * 70)
    print("   Sistema de Mensagens Distribuído - Status")
    print("=" * 70)
    print()

def check_containers_status():
    """Verifica status dos containers"""
    print("→ Status dos Containers:")
    print("-" * 70)

    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            check=False
        )

        if not result.stdout.strip():
            print("✗ Nenhum container em execução")
            print("\nInicie o sistema com: python on.py")
            return False

        # Parse JSON output (cada linha é um JSON)
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    containers.append(json.loads(line))
                except:
                    pass

        if not containers:
            # Fallback para formato tradicional
            subprocess.run(["docker-compose", "ps"], check=False)
            return True

        # Organizar por tipo
        services = {
            'broker': [],
            'proxy': [],
            'referencia': [],
            'servidores': [],
            'bots': [],
            'cliente': []
        }

        for container in containers:
            name = container.get('Name', '').lower()
            if 'broker' in name:
                services['broker'].append(container)
            elif 'proxy' in name:
                services['proxy'].append(container)
            elif 'referencia' in name:
                services['referencia'].append(container)
            elif 'servidor' in name:
                services['servidores'].append(container)
            elif 'bot' in name:
                services['bots'].append(container)
            elif 'cliente' in name:
                services['cliente'].append(container)

        # Exibir organizadamente
        for service_type, items in services.items():
            if items:
                print(f"\n{service_type.upper()}:")
                for item in items:
                    name = item.get('Name', 'N/A')
                    state = item.get('State', 'N/A')
                    status = item.get('Status', 'N/A')

                    status_icon = "✓" if state == "running" else "✗"
                    print(f"  {status_icon} {name}: {state} ({status})")

        return True

    except Exception as e:
        print(f"✗ Erro ao verificar containers: {e}")
        return False

def check_replication_status():
    """Verifica status de replicação"""
    print("\n→ Status de Replicação:")
    print("-" * 70)

    data_dir = Path("data")

    if not data_dir.exists():
        print("✗ Diretório de dados não encontrado")
        return

    servers = ["servidor_1", "servidor_2", "servidor_3"]
    data_files = ["users.json", "channels.json", "logins.json", "messages.json", "publications.json"]

    stats = {}

    for server in servers:
        server_dir = data_dir / server
        if not server_dir.exists():
            continue

        stats[server] = {}

        for data_file in data_files:
            file_path = server_dir / data_file
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        content = json.load(f)
                        if isinstance(content, dict) and 'data' in content:
                            data_content = content['data']
                            # Contar itens
                            if 'users' in data_content:
                                stats[server][data_file] = len(data_content['users'])
                            elif 'logins' in data_content:
                                stats[server][data_file] = len(data_content['logins'])
                            elif 'messages' in data_content:
                                stats[server][data_file] = len(data_content['messages'])
                            elif 'publications' in data_content:
                                stats[server][data_file] = len(data_content['publications'])
                            else:
                                stats[server][data_file] = 0
                        else:
                            stats[server][data_file] = 0
                except Exception as e:
                    stats[server][data_file] = f"Erro: {e}"
            else:
                stats[server][data_file] = 0

    # Verificar consistência
    print("\nDados por servidor:")
    print(f"{'Arquivo':<20} {'Servidor 1':>12} {'Servidor 2':>12} {'Servidor 3':>12} {'Status'}")
    print("-" * 70)

    for data_file in data_files:
        counts = [stats.get(server, {}).get(data_file, 0) for server in servers]

        # Verificar se todos têm o mesmo número
        if len(set(counts)) == 1 and counts[0] != 0:
            status = "✓ OK"
        elif all(c == 0 for c in counts):
            status = "- Vazio"
        else:
            status = "⚠ INCONSISTENTE"

        print(f"{data_file:<20} {str(counts[0]):>12} {str(counts[1]):>12} {str(counts[2]):>12} {status}")

def check_coordinator():
    """Verifica quem é o coordenador atual"""
    print("\n→ Coordenador Atual:")
    print("-" * 70)

    try:
        # Verificar logs dos servidores para encontrar coordenador
        servers = ["servidor_1", "servidor_2", "servidor_3"]

        for server in servers:
            result = subprocess.run(
                ["docker", "logs", "--tail", "50", server],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Procurar por anúncio de coordenador
            for line in result.stdout.split('\n'):
                if "é o novo COORDENADOR" in line:
                    print(f"✓ {line.strip()}")
                    return

        print("⚠ Coordenador não identificado nos logs recentes")

    except Exception as e:
        print(f"⚠ Erro ao verificar coordenador: {e}")

def check_clock_sync():
    """Verifica última sincronização de relógio"""
    print("\n→ Sincronização de Relógio:")
    print("-" * 70)

    try:
        servers = ["servidor_1", "servidor_2", "servidor_3"]

        for server in servers:
            result = subprocess.run(
                ["docker", "logs", "--tail", "100", server],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Procurar por logs de Berkeley
            berkeley_found = False
            for line in result.stdout.split('\n'):
                if "[BERKELEY]" in line or "[SYNC]" in line:
                    print(f"{server}: {line.strip()}")
                    berkeley_found = True
                    break

            if not berkeley_found:
                print(f"{server}: Nenhuma sincronização recente")

    except Exception as e:
        print(f"⚠ Erro ao verificar sincronização: {e}")

def show_recent_logs():
    """Mostra logs recentes de atividades"""
    print("\n→ Atividades Recentes:")
    print("-" * 70)

    try:
        result = subprocess.run(
            ["docker-compose", "logs", "--tail", "20", "--no-color"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Filtrar linhas relevantes
        relevant_keywords = ["ELEIÇÃO", "REPLICAÇÃO", "BERKELEY", "SYNC", "Login", "Canal criado"]

        lines = result.stdout.split('\n')
        relevant_lines = [
            line for line in lines
            if any(keyword in line for keyword in relevant_keywords)
        ]

        if relevant_lines:
            for line in relevant_lines[-10:]:  # Últimas 10 linhas relevantes
                print(line)
        else:
            print("Nenhuma atividade recente relevante")

    except Exception as e:
        print(f"⚠ Erro ao obter logs: {e}")

def show_helpful_commands():
    """Mostra comandos úteis"""
    print("\n" + "=" * 70)
    print("Comandos Úteis:")
    print("=" * 70)
    print()
    print("Ver logs completos de um servidor:")
    print("  docker logs -f servidor_1")
    print()
    print("Ver apenas logs de replicação:")
    print("  docker logs servidor_1 | grep REPLICAÇÃO")
    print()
    print("Ver apenas logs de eleição:")
    print("  docker logs servidor_3 | grep ELEIÇÃO")
    print()
    print("Ver apenas logs de Berkeley:")
    print("  docker logs servidor_3 | grep BERKELEY")
    print()
    print("Comparar dados entre servidores:")
    print("  diff data/servidor_1/users.json data/servidor_2/users.json")
    print()
    print("Conectar ao cliente:")
    print("  docker-compose up cliente")
    print()

def main():
    """Função principal"""
    print_banner()

    # Timestamp
    print(f"Verificação realizada em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Status dos containers
    if not check_containers_status():
        return

    # Status de replicação
    check_replication_status()

    # Coordenador
    check_coordinator()

    # Sincronização de relógio
    check_clock_sync()

    # Logs recentes
    show_recent_logs()

    # Comandos úteis
    show_helpful_commands()

    print("=" * 70)
    print("✓ Verificação concluída")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Verificação cancelada")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        sys.exit(1)
