import json
import serial
import serial.tools.list_ports
import threading
import time

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Pacote


# ===== CONTROLADOR ARDUINO GLOBAL =====
# Gerencia conexão serial com Arduino
class ArduinoController:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.serial_conn = None
        self.porta = '/dev/ttyACM0'
        self.baudrate = 115200
        self.aguardando_qr = False
        self._initialized = True
    
    def conectar(self, porta=None):
        """Conecta ao Arduino."""
        if porta:
            self.porta = porta
        try:
            if self.serial_conn and self.serial_conn.is_open:
                return True
            self.serial_conn = serial.Serial(self.porta, self.baudrate, timeout=0.1)
            time.sleep(2)
            print(f"[Arduino] Conectado em {self.porta}")
            return True
        except Exception as e:
            print(f"[Arduino] Erro conexão: {e}")
            return False
    
    def desconectar(self):
        """Desconecta do Arduino."""
        if self.serial_conn:
            self.serial_conn.close()
            self.serial_conn = None
    
    def enviar_comando(self, comando):
        """Envia comando para Arduino."""
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.conectar():
                return False, "Não conectado"
        try:
            self.serial_conn.write(f"{comando}\n".encode())
            print(f"[Arduino] → {comando}")
            
            # Lê resposta
            respostas = []
            tempo_inicio = time.time()
            while (time.time() - tempo_inicio) < 10:
                if self.serial_conn.in_waiting:
                    linha = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if linha:
                        respostas.append(linha)
                        print(f"[Arduino] ← {linha}")
                        if linha == "READY_FOR_QR":
                            self.aguardando_qr = True
                            break
                        elif linha in ["OK", "PRONTO", "RESET_OK", "CALIBRADO"]:
                            self.aguardando_qr = False
                            break
                time.sleep(0.01)
            
            return True, respostas
        except Exception as e:
            print(f"[Arduino] Erro: {e}")
            return False, str(e)
    
    def enviar_regiao(self, regiao):
        """Envia região para o Arduino processar."""
        # Envia mesmo se não estiver no estado correto - o Arduino vai responder com erro se necessário
        print(f"[Arduino] Enviando região: {regiao} (aguardando_qr={self.aguardando_qr})")
        sucesso, resposta = self.enviar_comando(f"REGIAO:{regiao}")
        if sucesso:
            self.aguardando_qr = False  # Reseta flag após enviar
        return sucesso, resposta
    
    def is_connected(self):
        """Verifica se está conectado."""
        return self.serial_conn is not None and self.serial_conn.is_open
    
    def get_status(self):
        """Retorna status da conexão."""
        return {
            "conectado": self.is_connected(),
            "porta": self.porta,
            "aguardando_qr": self.aguardando_qr
        }


# Instância global do controlador
arduino = ArduinoController()


# Página inicial
def index(request):
    return render(request, 'index.html')

# Rota para o Arduino enviar pacotes
@csrf_exempt
def receber_pacote_arduino(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body.decode('utf-8'))

            codigo = dados.get("codigo")
            nome = dados.get("nome")
            regiao = dados.get("regiao")
            
            if not codigo or not nome or not regiao:
                return JsonResponse({"erro": "Campos obrigatórios ausentes."}, status=400)

            regiao = regiao.lower().strip()

            pacote, created = Pacote.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nome": nome,
                    "regiao": regiao,
                    "criado_em": timezone.now()
                }
            )

            return JsonResponse({
                "mensagem": "Pacote recebido com sucesso.",
                "codigo": pacote.codigo,
                "nome": pacote.nome,
                "regiao": pacote.regiao,
                "criado_em": pacote.criado_em.strftime("%d/%m/%Y %H:%M:%S"),
                "novo": created
            })

        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido."}, status=400)
        except Exception as e:
            print("Erro ao processar POST do Arduino:", e)
            return JsonResponse({"erro": "Erro interno no servidor."}, status=500)
    else:
        return JsonResponse({"erro": "Método não permitido. Use POST."}, status=405)


# Rota para o frontend buscar pacotes
def listar_pacotes(request):
    if request.method == 'GET':
        try:
            pacotes = Pacote.objects.order_by('-criado_em')[:10]
            dados = [
                {
                    "codigo": p.codigo,
                    "nome": p.nome,
                    "regiao": p.regiao,
                    "criado_em": p.criado_em.strftime("%d/%m/%Y %H:%M:%S"),
                }
                for p in pacotes
            ]
            return JsonResponse({"pacotes": dados})
        except Exception as e:
            print("Erro ao buscar pacotes:", e)
            return JsonResponse({"erro": "Erro ao buscar dados."}, status=500)
    else:
        return JsonResponse({"erro": "Método não permitido. Use GET."}, status=405)
    
def camera_view(request):
    url_camera = request.GET.get('url_camera', '')
    if not url_camera:
        print("URL da câmera não fornecida.")
    return render(request, 'index.html', {'url_camera': url_camera})


# ===== ROTAS DE CONTROLE DO ARDUINO =====

@csrf_exempt
def arduino_conectar(request):
    """Conecta ao Arduino."""
    if request.method == 'POST':
        try:
            dados = json.loads(request.body.decode('utf-8'))
            porta = dados.get('porta', '/dev/ttyACM0')
        except:
            porta = '/dev/ttyACM0'
        
        sucesso = arduino.conectar(porta)
        return JsonResponse({
            "sucesso": sucesso,
            "mensagem": "Conectado" if sucesso else "Falha na conexão",
            "status": arduino.get_status()
        })
    return JsonResponse({"erro": "Use POST"}, status=405)


@csrf_exempt
def arduino_comando(request):
    """Envia comando para o Arduino."""
    if request.method == 'POST':
        try:
            dados = json.loads(request.body.decode('utf-8'))
            comando = dados.get('comando', '')
            
            if not comando:
                return JsonResponse({"erro": "Comando não fornecido"}, status=400)
            
            sucesso, resposta = arduino.enviar_comando(comando)
            return JsonResponse({
                "sucesso": sucesso,
                "resposta": resposta,
                "status": arduino.get_status()
            })
        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=500)
    return JsonResponse({"erro": "Use POST"}, status=405)


@csrf_exempt  
def arduino_iniciar_ciclo(request):
    """Inicia ciclo de pegar objeto."""
    if request.method == 'POST':
        sucesso, resposta = arduino.enviar_comando("INICIAR")
        return JsonResponse({
            "sucesso": sucesso,
            "resposta": resposta,
            "aguardando_qr": arduino.aguardando_qr,
            "status": arduino.get_status()
        })
    return JsonResponse({"erro": "Use POST"}, status=405)


@csrf_exempt
def arduino_enviar_regiao(request):
    """Envia região detectada para o Arduino."""
    if request.method == 'POST':
        try:
            dados = json.loads(request.body.decode('utf-8'))
            regiao = dados.get('regiao', '')
            
            if not regiao:
                return JsonResponse({"erro": "Região não fornecida"}, status=400)
            
            # Normaliza região
            regiao = regiao.lower().strip()
            if regiao in ['centro-oeste', 'centro oeste', 'centrooeste', 'centro_oeste']:
                regiao = 'centro-oeste'
            
            regioes_validas = ['norte', 'nordeste', 'centro-oeste', 'sudeste', 'sul']
            if regiao not in regioes_validas:
                return JsonResponse({
                    "erro": f"Região inválida: {regiao}",
                    "regioes_validas": regioes_validas
                }, status=400)
            
            sucesso, resposta = arduino.enviar_regiao(regiao)
            return JsonResponse({
                "sucesso": sucesso,
                "regiao": regiao,
                "resposta": resposta,
                "status": arduino.get_status()
            })
        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=500)
    return JsonResponse({"erro": "Use POST"}, status=405)


def arduino_status(request):
    """Retorna status do Arduino."""
    return JsonResponse(arduino.get_status())


def arduino_listar_portas(request):
    """Lista todas as portas seriais disponíveis no sistema."""
    portas = []
    for porta in serial.tools.list_ports.comports():
        portas.append({
            "dispositivo": porta.device,
            "descricao": porta.description,
            "fabricante": porta.manufacturer or "Desconhecido"
        })
    return JsonResponse({
        "portas": portas,
        "status": arduino.get_status()
    })


@csrf_exempt
def arduino_reset(request):
    """Reseta o Arduino."""
    if request.method == 'POST':
        sucesso, resposta = arduino.enviar_comando("RESET")
        return JsonResponse({
            "sucesso": sucesso,
            "resposta": resposta,
            "status": arduino.get_status()
        })
    return JsonResponse({"erro": "Use POST"}, status=405)


@csrf_exempt
def arduino_interromper(request):
    """Interrompe o ciclo atual do Arduino."""
    if request.method == 'POST':
        sucesso, resposta = arduino.enviar_comando("PARAR")
        arduino.aguardando_qr = False
        return JsonResponse({
            "sucesso": sucesso,
            "resposta": resposta,
            "mensagem": "Ciclo interrompido" if sucesso else "Falha ao interromper",
            "status": arduino.get_status()
        })
    return JsonResponse({"erro": "Use POST"}, status=405)


@csrf_exempt
def arduino_upload(request):
    """Faz upload do código para o Arduino via PlatformIO."""
    if request.method == 'POST':
        import subprocess
        import os
        
        # Caminho do projeto Arduino
        arduino_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'arduino')
        
        try:
            # Desconecta para liberar a porta serial
            arduino.desconectar()
            
            # Executa o upload via PlatformIO
            resultado = subprocess.run(
                ['platformio', 'run', '--target', 'upload'],
                cwd=arduino_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            sucesso = resultado.returncode == 0
            
            return JsonResponse({
                "sucesso": sucesso,
                "mensagem": "Upload concluído!" if sucesso else "Erro no upload",
                "stdout": resultado.stdout[-2000:] if resultado.stdout else "",
                "stderr": resultado.stderr[-500:] if resultado.stderr else "",
                "status": arduino.get_status()
            })
        except subprocess.TimeoutExpired:
            return JsonResponse({
                "sucesso": False,
                "erro": "Timeout: Upload demorou mais de 2 minutos",
                "status": arduino.get_status()
            })
        except FileNotFoundError:
            return JsonResponse({
                "sucesso": False,
                "erro": "PlatformIO não encontrado. Instale com: pip install platformio",
                "status": arduino.get_status()
            })
        except Exception as e:
            return JsonResponse({
                "sucesso": False,
                "erro": str(e),
                "status": arduino.get_status()
            })
    return JsonResponse({"erro": "Use POST"}, status=405)
