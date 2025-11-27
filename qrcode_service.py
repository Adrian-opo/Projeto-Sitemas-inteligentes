"""
Serviço para iniciar o script de leitura de QR code em background.
Este módulo é importado pelo Django AppConfig para auto-start.
"""
import os
import subprocess
import sys
import threading
import time


_qr_process = None
_qr_lock = threading.Lock()


def start_qr_reader_service(
    source="0",
    port=5001,
    backend_url="http://127.0.0.1:8001/api/arduino/pacote/",
    tunnel=False
):
    """
    Inicia o script-read-qrcode.py em um processo separado.
    Retorna o processo (subprocess.Popen) ou None se já estiver rodando.
    """
    global _qr_process
    
    with _qr_lock:
        if _qr_process is not None and _qr_process.poll() is None:
            print("[QR Service] Já está rodando.", flush=True)
            return _qr_process
        
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "script-read-qrcode.py"
        )
        
        if not os.path.exists(script_path):
            print(f"[QR Service] ERRO: script não encontrado em {script_path}", flush=True)
            return None
        
        # Monta os argumentos do script
        args = [
            sys.executable,
            script_path,
            "--source", str(source),
            "--port", str(port),
            "--backend-url", backend_url,
            "--host", "0.0.0.0",
        ]
        
        if tunnel:
            args.append("--tunnel")
        
        try:
            print(f"[QR Service] Iniciando: {' '.join(args)}", flush=True)
            
            # Inicia o processo em background
            _qr_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Thread para monitorar o output do processo
            def _monitor_output():
                try:
                    for line in _qr_process.stdout:
                        line = line.strip()
                        if line:
                            print(f"[QR Reader] {line}", flush=True)
                except Exception as e:
                    print(f"[QR Service] Erro ao ler output: {e}", flush=True)
            
            monitor_thread = threading.Thread(target=_monitor_output, daemon=True)
            monitor_thread.start()
            
            # Aguarda um pouco para ver se o processo inicia corretamente
            time.sleep(1)
            
            if _qr_process.poll() is not None:
                print(f"[QR Service] ERRO: processo terminou imediatamente com código {_qr_process.returncode}", flush=True)
                _qr_process = None
                return None
            
            print(f"[QR Service] Iniciado com PID {_qr_process.pid}", flush=True)
            return _qr_process
            
        except Exception as e:
            print(f"[QR Service] ERRO ao iniciar: {e}", flush=True)
            _qr_process = None
            return None


def stop_qr_reader_service():
    """
    Para o serviço de leitura de QR code se estiver rodando.
    """
    global _qr_process
    
    with _qr_lock:
        if _qr_process is None:
            return
        
        try:
            if _qr_process.poll() is None:
                print(f"[QR Service] Parando processo {_qr_process.pid}...", flush=True)
                _qr_process.terminate()
                try:
                    _qr_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("[QR Service] Timeout ao aguardar término, forçando kill...", flush=True)
                    _qr_process.kill()
                print("[QR Service] Processo parado.", flush=True)
        except Exception as e:
            print(f"[QR Service] Erro ao parar: {e}", flush=True)
        finally:
            _qr_process = None


def get_qr_reader_status():
    """
    Retorna informações sobre o status do serviço.
    """
    with _qr_lock:
        if _qr_process is None:
            return {"running": False, "pid": None}
        
        poll = _qr_process.poll()
        if poll is None:
            return {"running": True, "pid": _qr_process.pid}
        else:
            return {"running": False, "pid": None, "exit_code": poll}
