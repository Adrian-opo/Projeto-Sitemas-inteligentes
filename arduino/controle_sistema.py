#!/usr/bin/env python3
"""
Sistema de Controle Integrado - Garra Robótica + QR Code + Esteira
Autor: Sistema Automatizado
Data: 19/11/2025
"""

import serial
import time
import cv2
from pyzbar import pyzbar
import threading
import sys

class ControladorSistema:
    def __init__(self, porta_serial='/dev/ttyACM0', baudrate=115200):
        """
        Inicializa o controlador do sistema
        
        Args:
            porta_serial: Porta onde o Arduino está conectado
            baudrate: Taxa de comunicação serial
        """
        self.porta = porta_serial
        self.baudrate = baudrate
        self.serial_conn = None
        self.camera = None
        self.executando = True
        
        # Mapeamento de destinos QR Code -> Posições dos servos
        self.mapa_destinos = {
            'A': {'base': 0, 'antebraco': 130},
            'B': {'base': 45, 'antebraco': 130},
            'C': {'base': 90, 'antebraco': 130},
            'D': {'base': 135, 'antebraco': 130},
            'E': {'base': 180, 'antebraco': 130},
        }
        
    def conectar_serial(self):
        """Estabelece conexão serial com Arduino"""
        try:
            self.serial_conn = serial.Serial(
                self.porta,
                self.baudrate,
                timeout=1
            )
            time.sleep(2)  # Aguarda reset do Arduino
            print(f"✓ Conectado ao Arduino em {self.porta}")
            
            # Lê mensagens iniciais do Arduino
            for _ in range(10):
                if self.serial_conn.in_waiting:
                    linha = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    print(f"  Arduino: {linha}")
                time.sleep(0.1)
            return True
        except Exception as e:
            print(f"✗ Erro ao conectar: {e}")
            return False
    
    def enviar_comando(self, comando):
        """
        Envia comando para o Arduino e aguarda resposta
        
        Args:
            comando: String com o comando a enviar
        """
        if not self.serial_conn:
            print("✗ Serial não conectada!")
            return False
        
        try:
            self.serial_conn.write(f"{comando}\n".encode())
            print(f"→ Enviado: {comando}")
            
            # Aguarda resposta
            tempo_inicio = time.time()
            while (time.time() - tempo_inicio) < 30:  # Timeout de 30s
                if self.serial_conn.in_waiting:
                    linha = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    print(f"← Arduino: {linha}")
                    
                    if linha == "OK":
                        return True
                    elif "READY_FOR_QR" in linha:
                        return "QR"
                    elif "READY_FOR_CONVEYOR" in linha:
                        return "CONVEYOR"
                time.sleep(0.01)
            
            return True
        except Exception as e:
            print(f"✗ Erro ao enviar comando: {e}")
            return False
    
    def inicializar_camera(self, indice=0):
        """Inicializa câmera para leitura de QR Code"""
        try:
            self.camera = cv2.VideoCapture(indice)
            if self.camera.isOpened():
                print(f"✓ Câmera inicializada (índice {indice})")
                return True
            else:
                print(f"✗ Não foi possível abrir a câmera {indice}")
                return False
        except Exception as e:
            print(f"✗ Erro ao inicializar câmera: {e}")
            return False
    
    def ler_qr_code(self, timeout=30):
        """
        Lê QR Code da câmera
        
        Args:
            timeout: Tempo máximo de espera em segundos
        
        Returns:
            String com o conteúdo do QR Code ou None
        """
        if not self.camera:
            print("✗ Câmera não inicializada!")
            return None
        
        print("\n=== AGUARDANDO QR CODE ===")
        print("Posicione o QR Code na frente da câmera...")
        print(f"Destinos válidos: {', '.join(self.mapa_destinos.keys())}")
        
        tempo_inicio = time.time()
        
        while (time.time() - tempo_inicio) < timeout:
            ret, frame = self.camera.read()
            
            if not ret:
                print("✗ Erro ao capturar frame")
                continue
            
            # Procura por QR Codes no frame
            qr_codes = pyzbar.decode(frame)
            
            for qr in qr_codes:
                dados = qr.data.decode('utf-8').strip().upper()
                print(f"\n✓ QR Code detectado: {dados}")
                
                # Desenha retângulo ao redor do QR Code
                pontos = qr.polygon
                if len(pontos) == 4:
                    pontos = [(p.x, p.y) for p in pontos]
                    for i in range(4):
                        cv2.line(frame, pontos[i], pontos[(i+1)%4], (0, 255, 0), 3)
                
                # Mostra o frame com detecção
                cv2.putText(frame, f"Destino: {dados}", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow('QR Code Detectado', frame)
                cv2.waitKey(2000)  # Mostra por 2 segundos
                cv2.destroyAllWindows()
                
                return dados
            
            # Mostra preview da câmera
            cv2.putText(frame, "Aguardando QR Code...", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow('Camera - Posicione QR Code', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyAllWindows()
        print("✗ Timeout - QR Code não detectado")
        return None
    
    def obter_posicao_destino(self, codigo_qr):
        """
        Retorna as posições dos servos para o destino especificado
        
        Args:
            codigo_qr: Código lido do QR
        
        Returns:
            Dict com posições ou None se inválido
        """
        if codigo_qr in self.mapa_destinos:
            return self.mapa_destinos[codigo_qr]
        else:
            print(f"✗ Destino '{codigo_qr}' não reconhecido!")
            print(f"  Destinos válidos: {', '.join(self.mapa_destinos.keys())}")
            return None
    
    def ciclo_completo_automatico(self):
        """Executa ciclo completo: pegar → QR → posicionar → soltar"""
        print("\n" + "="*60)
        print("INICIANDO CICLO COMPLETO AUTOMÁTICO")
        print("="*60)
        
        # 1. Pega o objeto
        print("\n[1/5] Pegando objeto...")
        resposta = self.enviar_comando('P')
        if resposta == "QR":
            print("✓ Objeto capturado! Sistema pronto para ler QR Code")
        
        # 2. Lê QR Code
        print("\n[2/5] Lendo QR Code...")
        destino_qr = self.ler_qr_code(timeout=30)
        
        if not destino_qr:
            print("✗ Falha na leitura do QR Code. Abortando ciclo.")
            self.enviar_comando('V')  # Volta à posição inicial
            return False
        
        # 3. Obtém posição de destino
        posicao = self.obter_posicao_destino(destino_qr)
        if not posicao:
            print("✗ Destino inválido. Abortando ciclo.")
            self.enviar_comando('V')
            return False
        
        # 4. Move para posição de seleção
        print(f"\n[3/5] Movendo para posição '{destino_qr}'...")
        print(f"  Base: {posicao['base']}° | Antebraço: {posicao['antebraco']}°")
        comando_qr = f"QR{posicao['base']},{posicao['antebraco']}"
        self.enviar_comando(comando_qr)
        
        # 5. Coloca na esteira
        print("\n[4/5] Colocando objeto na esteira...")
        time.sleep(1)
        resposta = self.enviar_comando('E')
        
        if resposta == "CONVEYOR":
            print("✓ Objeto depositado! Aguardando esteira...")
            # Aqui você pode adicionar comando para ativar a esteira
            time.sleep(3)
        
        # 6. Volta à posição inicial
        print("\n[5/5] Retornando à posição inicial...")
        self.enviar_comando('V')
        
        print("\n" + "="*60)
        print("✓ CICLO COMPLETO FINALIZADO COM SUCESSO!")
        print("="*60 + "\n")
        return True
    
    def monitorar_serial(self):
        """Thread para monitorar continuamente a serial"""
        while self.executando:
            if self.serial_conn and self.serial_conn.in_waiting:
                try:
                    linha = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if linha and linha != "OK":
                        print(f"← {linha}")
                except:
                    pass
            time.sleep(0.05)
    
    def menu_interativo(self):
        """Menu interativo para controle manual"""
        print("\n" + "="*60)
        print("MENU DE CONTROLE DO SISTEMA")
        print("="*60)
        print("\n=== SEQUÊNCIAS AUTOMÁTICAS ===")
        print("  1 - Ciclo completo automático (Pegar + QR + Soltar)")
        print("  2 - Calibração inicial")
        print("\n=== CONTROLE MANUAL - SERVOS ===")
        print("  3 - Pegar objeto")
        print("  4 - Colocar na esteira")
        print("  5 - Voltar posição inicial")
        print("  6 - Controle manual de servo")
        print("\n=== MOTORES DE PASSO ===")
        print("  7 - Testar ambos motores")
        print("  8 - Motor 1 - Pequeno movimento (100 passos)")
        print("  9 - Motor 2 - Pequeno movimento (100 passos)")
        print("  0 - Zerar posições dos motores")
        print("  P - Mostrar posição atual dos motores")
        print("\n=== QR CODE ===")
        print("  Q - Ler QR Code e mover para posição")
        print("\n=== SISTEMA ===")
        print("  M - Monitorar serial continuamente")
        print("  X - Sair")
        print("="*60)
    
    def executar(self):
        """Loop principal do sistema"""
        if not self.conectar_serial():
            return
        
        # Tenta inicializar câmera
        self.inicializar_camera()
        
        # Inicia thread de monitoramento
        thread_monitor = threading.Thread(target=self.monitorar_serial, daemon=True)
        thread_monitor.start()
        
        while self.executando:
            self.menu_interativo()
            escolha = input("\nEscolha uma opção: ").strip().upper()
            
            if escolha == '1':
                self.ciclo_completo_automatico()
            
            elif escolha == '2':
                self.enviar_comando('C')
            
            elif escolha == '3':
                self.enviar_comando('P')
            
            elif escolha == '4':
                self.enviar_comando('E')
            
            elif escolha == '5':
                self.enviar_comando('V')
            
            elif escolha == '6':
                print("\nServos disponíveis: G(garra), B(base), A(antebraço), R(braço)")
                servo = input("Servo: ").strip().upper()
                angulo = input("Ângulo (0-180): ").strip()
                self.enviar_comando(f"{servo}{angulo}")
            
            elif escolha == '7':
                self.enviar_comando('M')
            
            elif escolha == '8':
                print("\nF = Frente | T = Trás")
                direcao = input("Direção: ").strip().upper()
                passos = input("Passos (padrão 100): ").strip()
                if not passos:
                    passos = "100"
                cmd = '1F' if direcao == 'F' else '1B'
                self.enviar_comando(f"{cmd}{passos}")
            
            elif escolha == '9':
                print("\nF = Frente | T = Trás")
                direcao = input("Direção: ").strip().upper()
                passos = input("Passos (padrão 100): ").strip()
                if not passos:
                    passos = "100"
                cmd = '2F' if direcao == 'F' else '2B'
                self.enviar_comando(f"{cmd}{passos}")
            
            elif escolha == '0':
                self.enviar_comando('Z')
            
            elif escolha == 'P':
                self.enviar_comando('?')
            
            elif escolha == 'Q':
                destino = self.ler_qr_code()
                if destino:
                    pos = self.obter_posicao_destino(destino)
                    if pos:
                        cmd = f"QR{pos['base']},{pos['antebraco']}"
                        self.enviar_comando(cmd)
            
            elif escolha == 'M':
                print("\nMonitorando serial... (Pressione Ctrl+C para parar)")
                try:
                    while True:
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\nMonitoramento interrompido")
            
            elif escolha == 'X':
                self.executando = False
                print("\nEncerrando sistema...")
            
            else:
                print("✗ Opção inválida!")
        
        # Cleanup
        if self.camera:
            self.camera.release()
        if self.serial_conn:
            self.serial_conn.close()
        cv2.destroyAllWindows()
        print("Sistema encerrado.")


def main():
    """Função principal"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  SISTEMA DE CONTROLE - GARRA ROBÓTICA + QR CODE         ║
    ║  Arduino Mega 2560 + Servos + Motores de Passo          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Solicita porta serial
    porta = input("Porta serial do Arduino (padrão /dev/ttyACM0): ").strip()
    if not porta:
        porta = '/dev/ttyACM0'
    
    # Cria e executa controlador
    controlador = ControladorSistema(porta_serial=porta)
    
    try:
        controlador.executar()
    except KeyboardInterrupt:
        print("\n\nPrograma interrompido pelo usuário")
    except Exception as e:
        print(f"\n✗ Erro fatal: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
