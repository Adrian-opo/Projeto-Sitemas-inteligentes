#!/usr/bin/env python3
"""
Script central para iniciar o DashLog.
Inicia o Django e o QR Reader juntos.
Ctrl+C para parar tudo.

Uso:
    python start.py
    python start.py --qr-source=0 --qr-port=5001
    python start.py --django-port=8001 --tunnel
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from threading import Thread

# Cores para o terminal
class Colors:
    DJANGO = '\033[94m'    # Azul
    QR = '\033[92m'        # Verde
    ERROR = '\033[91m'     # Vermelho
    WARN = '\033[93m'      # Amarelo
    RESET = '\033[0m'
    BOLD = '\033[1m'

def colored(text, color):
    return f"{color}{text}{Colors.RESET}"

# Processos globais para cleanup
django_proc = None
qr_proc = None
stopping = False


def stream_output(proc, prefix, color):
    """Lê stdout/stderr do processo e imprime com prefixo colorido."""
    try:
        for line in iter(proc.stdout.readline, ''):
            if stopping:
                break
            line = line.rstrip()
            if line:
                print(f"{colored(f'[{prefix}]', color)} {line}", flush=True)
    except Exception:
        pass


def cleanup(*args):
    """Para todos os processos graciosamente."""
    global stopping, django_proc, qr_proc
    
    if stopping:
        return
    stopping = True
    
    print(f"\n{colored('[DASHLOG]', Colors.WARN)} Parando serviços...", flush=True)
    
    for name, proc in [("QR Reader", qr_proc), ("Django", django_proc)]:
        if proc and proc.poll() is None:
            try:
                print(f"{colored('[DASHLOG]', Colors.WARN)} Parando {name}...", flush=True)
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
            except Exception as e:
                print(f"{colored('[ERRO]', Colors.ERROR)} Erro ao parar {name}: {e}", flush=True)
    
    print(f"{colored('[DASHLOG]', Colors.BOLD)} Todos os serviços parados.", flush=True)
    sys.exit(0)


def main():
    global django_proc, qr_proc
    
    parser = argparse.ArgumentParser(
        description="Inicia o DashLog (Django + QR Reader) em primeiro plano."
    )
    parser.add_argument('--django-port', type=int, default=8001, help='Porta do Django (padrão: 8001)')
    parser.add_argument('--django-host', default='0.0.0.0', help='Host do Django (padrão: 0.0.0.0)')
    parser.add_argument('--qr-source', default='0', help='Fonte da câmera (0=webcam ou URL do IP Webcam)')
    parser.add_argument('--qr-port', type=int, default=5001, help='Porta do QR Reader Flask (padrão: 5001)')
    parser.add_argument('--tunnel', action='store_true', help='Ativar Cloudflare tunnel')
    parser.add_argument('--no-qr', action='store_true', help='Não iniciar o QR Reader')
    parser.add_argument('--migrate', action='store_true', help='Executar migrações antes de iniciar')
    
    args = parser.parse_args()
    
    # Registra handlers para SIGINT (Ctrl+C) e SIGTERM
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Diretório base do projeto
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    # Detecta o Python do venv se existir
    venv_python = os.path.join(base_dir, '.venv', 'bin', 'python')
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    
    print(f"{colored('[DASHLOG]', Colors.BOLD)} Iniciando DashLog...", flush=True)
    print(f"{colored('[DASHLOG]', Colors.BOLD)} Python: {python_exe}", flush=True)
    print(f"{colored('[DASHLOG]', Colors.BOLD)} Django: http://{args.django_host}:{args.django_port}", flush=True)
    if not args.no_qr:
        print(f"{colored('[DASHLOG]', Colors.BOLD)} QR Reader: http://0.0.0.0:{args.qr_port}", flush=True)
    print(f"{colored('[DASHLOG]', Colors.BOLD)} Pressione Ctrl+C para parar tudo.\n", flush=True)
    
    # Executa migrações se solicitado
    if args.migrate:
        print(f"{colored('[DJANGO]', Colors.DJANGO)} Executando migrações...", flush=True)
        result = subprocess.run([python_exe, 'manage.py', 'migrate', '--noinput'], cwd=base_dir)
        if result.returncode != 0:
            print(f"{colored('[ERRO]', Colors.ERROR)} Falha nas migrações!", flush=True)
            sys.exit(1)
        print(f"{colored('[DJANGO]', Colors.DJANGO)} Migrações concluídas.\n", flush=True)
    
    # Configura variável de ambiente para desativar auto-start do QR Reader no apps.py
    # (já que vamos iniciar manualmente aqui)
    env = os.environ.copy()
    env['DASHLOG_DISABLE_QR_AUTOSTART'] = '1'
    
    # Inicia o QR Reader primeiro (se não desativado)
    if not args.no_qr:
        qr_script = os.path.join(base_dir, 'script-read-qrcode.py')
        if os.path.exists(qr_script):
            qr_args = [
                python_exe, qr_script,
                '--source', str(args.qr_source),
                '--port', str(args.qr_port),
                '--backend-url', f'http://127.0.0.1:{args.django_port}/api/arduino/pacote/',
                '--host', '0.0.0.0'
            ]
            if args.tunnel:
                qr_args.append('--tunnel')
            
            qr_proc = subprocess.Popen(
                qr_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=base_dir
            )
            
            # Thread para ler output do QR Reader
            qr_thread = Thread(target=stream_output, args=(qr_proc, 'QR', Colors.QR), daemon=True)
            qr_thread.start()
            
            # Aguarda um pouco para o QR Reader iniciar
            time.sleep(1)
            if qr_proc.poll() is not None:
                print(f"{colored('[ERRO]', Colors.ERROR)} QR Reader falhou ao iniciar!", flush=True)
        else:
            print(f"{colored('[WARN]', Colors.WARN)} script-read-qrcode.py não encontrado, pulando QR Reader.", flush=True)
    
    # Inicia o Django
    django_args = [
        python_exe, 'manage.py', 'runserver',
        f'{args.django_host}:{args.django_port}',
        '--noreload'  # Desativa reload para evitar duplicação de processos
    ]
    
    django_proc = subprocess.Popen(
        django_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=base_dir,
        env=env
    )
    
    # Thread para ler output do Django
    django_thread = Thread(target=stream_output, args=(django_proc, 'DJANGO', Colors.DJANGO), daemon=True)
    django_thread.start()
    
    # Loop principal - espera os processos terminarem
    try:
        while True:
            # Verifica se algum processo morreu
            if django_proc and django_proc.poll() is not None:
                print(f"{colored('[ERRO]', Colors.ERROR)} Django parou inesperadamente!", flush=True)
                cleanup()
                break
            
            if qr_proc and qr_proc.poll() is not None and not args.no_qr:
                print(f"{colored('[WARN]', Colors.WARN)} QR Reader parou.", flush=True)
                qr_proc = None  # Não tentar parar de novo
            
            time.sleep(0.5)
    except KeyboardInterrupt:
        cleanup()


if __name__ == '__main__':
    main()
