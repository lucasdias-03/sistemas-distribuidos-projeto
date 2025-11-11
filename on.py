#!/usr/bin/env python3
"""
Script para iniciar o sistema de mensagens distribuído
"""
import subprocess
import sys
import time
import os

def print_banner():
    """Exibe banner do sistema"""
    print("=" * 70)
    print("   Sistema de Mensagens Distribuído - Inicializando")
    print("=" * 70)
    print()

def check_docker():
    """Verifica se Docker está instalado e rodando"""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Docker encontrado: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ ERRO: Docker não encontrado ou não está rodando")
        print("  Instale o Docker: https://docs.docker.com/get-docker/")
        return False

def check_docker_compose():
    """Verifica se Docker Compose está instalado"""
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Docker Compose encontrado: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ ERRO: Docker Compose não encontrado")
        print("  Instale o Docker Compose: https://docs.docker.com/compose/install/")
        return False

def stop_existing_containers():
    """Para containers existentes"""
    print("\n→ Parando containers existentes (se houver)...")
    try:
        subprocess.run(
            ["docker-compose", "down"],
            capture_output=True,
            check=False
        )
        print("✓ Containers anteriores parados")
    except Exception as e:
        print(f"⚠ Aviso ao parar containers: {e}")

def build_images():
    """Constrói as imagens Docker"""
    print("\n→ Construindo imagens Docker...")
    print("  (Isso pode levar alguns minutos na primeira vez)\n")
    try:
        process = subprocess.Popen(
            ["docker-compose", "build"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            print(f"  {line}", end='')

        process.wait()

        if process.returncode == 0:
            print("\n✓ Imagens construídas com sucesso")
            return True
        else:
            print("\n✗ ERRO ao construir imagens")
            return False
    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        return False

def start_services():
    """Inicia os serviços"""
    print("\n→ Iniciando serviços em background...")
    print("  - 1 Broker (balanceador de carga)")
    print("  - 1 Proxy (Pub/Sub)")
    print("  - 1 Referência (coordenação)")
    print("  - 3 Servidores (processamento)")
    print("  - 2 Bots (clientes automatizados)")
    print("  - 1 Cliente (interface interativa)")
    print()

    try:
        # Iniciar serviços em background
        subprocess.run(
            ["docker-compose", "up", "-d",
             "broker", "proxy", "referencia",
             "servidor_1", "servidor_2", "servidor_3",
             "bot_1", "bot_2"],
            check=True
        )
        print("✓ Serviços iniciados")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ ERRO ao iniciar serviços: {e}")
        return False

def wait_for_services():
    """Aguarda serviços ficarem prontos"""
    print("\n→ Aguardando serviços ficarem prontos...")
    print("  (Eleição de coordenador, sincronização, etc.)")

    for i in range(15, 0, -1):
        print(f"  {i}s...", end='\r')
        time.sleep(1)

    print("✓ Serviços prontos" + " " * 20)

def show_logs():
    """Mostra logs dos serviços"""
    print("\n→ Logs dos serviços:")
    print("-" * 70)

    services = ["servidor_1", "servidor_2", "servidor_3"]

    for service in services:
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", "5", service],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(f"\n[{service}]")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        except Exception as e:
            print(f"⚠ Não foi possível obter logs de {service}: {e}")

def show_status():
    """Mostra status dos containers"""
    print("\n→ Status dos containers:")
    print("-" * 70)
    try:
        subprocess.run(["docker-compose", "ps"], check=True)
    except Exception as e:
        print(f"⚠ Erro ao obter status: {e}")

def start_client_interactive():
    """Pergunta se deseja iniciar cliente interativo"""
    print("\n" + "=" * 70)
    print("Sistema iniciado com sucesso!")
    print("=" * 70)
    print("\nOpções:")
    print("  1. Iniciar cliente interativo (conectar ao sistema)")
    print("  2. Ver logs em tempo real")
    print("  3. Sair (serviços continuarão rodando em background)")
    print()

    choice = input("Escolha uma opção (1-3): ").strip()

    if choice == "1":
        print("\n→ Iniciando cliente interativo...")
        print("  (Use Ctrl+P, Ctrl+Q para desconectar sem parar)")
        print("  (Digite 0 no menu para sair completamente)")
        print()
        time.sleep(2)
        try:
            # Inicia cliente e anexa ao terminal
            subprocess.run(
                ["docker-compose", "up", "cliente"],
                check=False
            )
        except KeyboardInterrupt:
            print("\n✓ Cliente desconectado")

    elif choice == "2":
        print("\n→ Mostrando logs em tempo real...")
        print("  (Pressione Ctrl+C para parar)")
        print()
        try:
            subprocess.run(
                ["docker-compose", "logs", "-f"],
                check=False
            )
        except KeyboardInterrupt:
            print("\n✓ Logs interrompidos")

    else:
        print("\n✓ Serviços rodando em background")

def show_helpful_commands():
    """Mostra comandos úteis"""
    print("\n" + "=" * 70)
    print("Comandos Úteis:")
    print("=" * 70)
    print()
    print("Ver logs de um serviço específico:")
    print("  docker logs -f servidor_1")
    print("  docker logs -f servidor_2")
    print("  docker logs -f servidor_3")
    print()
    print("Conectar ao cliente interativo:")
    print("  docker-compose up cliente")
    print()
    print("Ver status dos containers:")
    print("  docker-compose ps")
    print()
    print("Parar todos os serviços:")
    print("  python off.py")
    print("  ou: docker-compose down")
    print()
    print("Verificar dados replicados:")
    print("  cat data/servidor_1/users.json")
    print("  cat data/servidor_2/users.json")
    print("  cat data/servidor_3/users.json")
    print()
    print("Testar falha de servidor:")
    print("  docker stop servidor_3")
    print("  docker start servidor_3")
    print()

def main():
    """Função principal"""
    print_banner()

    # Verificações
    if not check_docker():
        sys.exit(1)

    if not check_docker_compose():
        sys.exit(1)

    # Parar containers existentes
    stop_existing_containers()

    # Construir imagens
    if not build_images():
        sys.exit(1)

    # Iniciar serviços
    if not start_services():
        sys.exit(1)

    # Aguardar serviços
    wait_for_services()

    # Mostrar status
    show_status()

    # Mostrar logs
    show_logs()

    # Opções interativas
    start_client_interactive()

    # Comandos úteis
    show_helpful_commands()

    print("=" * 70)
    print("✓ Sistema pronto para uso!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Inicialização cancelada pelo usuário")
        print("  Use 'python off.py' para parar serviços se necessário")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ ERRO FATAL: {e}")
        sys.exit(1)
