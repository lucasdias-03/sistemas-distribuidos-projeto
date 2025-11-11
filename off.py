#!/usr/bin/env python3
"""
Script para parar o sistema de mensagens distribuído
"""
import subprocess
import sys
import time

def print_banner():
    """Exibe banner"""
    print("=" * 70)
    print("   Sistema de Mensagens Distribuído - Desligando")
    print("=" * 70)
    print()

def show_running_containers():
    """Mostra containers em execução"""
    print("→ Containers em execução:")
    print("-" * 70)
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--services", "--filter", "status=running"],
            capture_output=True,
            text=True,
            check=False
        )

        services = result.stdout.strip().split('\n')
        services = [s for s in services if s]  # Remove linhas vazias

        if services:
            for service in services:
                print(f"  • {service}")
            print(f"\nTotal: {len(services)} serviço(s)")
            return True
        else:
            print("  Nenhum container em execução")
            return False

    except Exception as e:
        print(f"⚠ Erro ao listar containers: {e}")
        return False

def ask_confirmation():
    """Pede confirmação do usuário"""
    print("\n" + "=" * 70)
    print("ATENÇÃO: Esta ação irá:")
    print("  • Parar todos os containers")
    print("  • Remover redes Docker criadas")
    print("  • Os dados em 'data/' serão PRESERVADOS")
    print("=" * 70)
    print()

    response = input("Deseja continuar? (s/N): ").strip().lower()
    return response in ['s', 'sim', 'y', 'yes']

def stop_containers():
    """Para os containers"""
    print("\n→ Parando containers...")

    try:
        process = subprocess.Popen(
            ["docker-compose", "down"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            print(f"  {line}", end='')

        process.wait()

        if process.returncode == 0:
            print("\n✓ Containers parados com sucesso")
            return True
        else:
            print("\n✗ ERRO ao parar containers")
            return False

    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        return False

def show_data_preservation():
    """Mostra informações sobre dados preservados"""
    print("\n→ Dados preservados em disco:")
    print("-" * 70)

    import os
    from pathlib import Path

    data_dir = Path("data")

    if data_dir.exists():
        total_size = 0
        file_count = 0

        for root, dirs, files in os.walk(data_dir):
            for file in files:
                file_path = Path(root) / file
                try:
                    size = file_path.stat().st_size
                    total_size += size
                    file_count += 1
                    rel_path = file_path.relative_to(data_dir)
                    print(f"  {rel_path} ({size} bytes)")
                except Exception:
                    pass

        print(f"\nTotal: {file_count} arquivo(s), {total_size} bytes")
        print("\n⚠ Para limpar dados, execute:")
        print("  rm -rf data/  (Linux/Mac)")
        print("  rmdir /s data  (Windows)")
    else:
        print("  Nenhum dado encontrado")

def show_cleanup_options():
    """Mostra opções de limpeza"""
    print("\n" + "=" * 70)
    print("Opções de Limpeza Adicional:")
    print("=" * 70)
    print()
    print("Remover imagens Docker (liberar espaço):")
    print("  docker-compose down --rmi all")
    print()
    print("Remover volumes (APAGA TODOS OS DADOS):")
    print("  docker-compose down -v")
    print()
    print("Limpeza completa (imagens + volumes + dados):")
    print("  docker-compose down --rmi all -v && rm -rf data/")
    print()

def verify_stopped():
    """Verifica se tudo foi parado"""
    print("\n→ Verificando status final...")

    try:
        result = subprocess.run(
            ["docker-compose", "ps", "-q"],
            capture_output=True,
            text=True,
            check=False
        )

        if result.stdout.strip():
            print("⚠ Alguns containers ainda estão em execução")
            subprocess.run(["docker-compose", "ps"], check=False)
            return False
        else:
            print("✓ Todos os containers foram parados")
            return True

    except Exception as e:
        print(f"⚠ Erro ao verificar status: {e}")
        return False

def main():
    """Função principal"""
    print_banner()

    # Mostra containers em execução
    has_running = show_running_containers()

    if not has_running:
        print("\n✓ Sistema já está desligado")
        show_data_preservation()
        return

    # Pede confirmação
    if not ask_confirmation():
        print("\n✓ Operação cancelada")
        print("  Containers continuam em execução")
        return

    # Para containers
    if not stop_containers():
        print("\n⚠ Houve erros ao parar containers")
        print("  Tente manualmente: docker-compose down")
        sys.exit(1)

    # Verifica se parou
    verify_stopped()

    # Mostra dados preservados
    show_data_preservation()

    # Mostra opções de limpeza
    show_cleanup_options()

    print("\n" + "=" * 70)
    print("✓ Sistema desligado com sucesso!")
    print("=" * 70)
    print("\nPara reiniciar o sistema:")
    print("  python on.py")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Operação cancelada pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ ERRO FATAL: {e}")
        sys.exit(1)
