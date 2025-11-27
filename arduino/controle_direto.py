#!/usr/bin/env python3
"""
Controle Direto - Envie comandos para o Arduino
"""
import serial
import time
import threading

class ControleDireto:
    def __init__(self, porta='/dev/ttyUSB0'):
        self.porta = porta
        self.serial = None
        self.rodando = True
        
    def conectar(self):
        try:
            self.serial = serial.Serial(self.porta, 115200, timeout=0.1)
            time.sleep(2)
            print(f"✓ Conectado a {self.porta}\n")
            
            # Limpa buffer inicial
            while self.serial.in_waiting:
                self.serial.readline()
            
            return True
        except Exception as e:
            print(f"✗ Erro: {e}")
            return False
    
    def monitor_serial(self):
        """Thread para ler respostas do Arduino"""
        while self.rodando:
            try:
                if self.serial and self.serial.in_waiting:
                    linha = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if linha and linha != "OK":
                        print(f"← {linha}")
            except:
                pass
            time.sleep(0.01)
    
    def enviar(self, cmd):
        """Envia comando para Arduino"""
        if self.serial:
            self.serial.write(f"{cmd}\n".encode())
            print(f"→ {cmd}")
    
    def executar(self):
        if not self.conectar():
            return
        
        # Inicia thread de monitoramento
        thread = threading.Thread(target=self.monitor_serial, daemon=True)
        thread.start()
        
        print("="*60)
        print("CONTROLE DIRETO - DIGITE COMANDOS")
        print("="*60)
        print("\nComandos rápidos:")
        print("  1F<n>  - Motor1 frente (ex: 1F50)")
        print("  1B<n>  - Motor1 trás")
        print("  2F<n>  - Motor2 frente")
        print("  2B<n>  - Motor2 trás")
        print("  ?      - Ver posição")
        print("  Z      - Zerar")
        print("  M      - Teste ambos")
        print("  T      - Teste pinos")
        print("  C      - Calibrar servos")
        print("  P      - Pegar objeto")
        print("  quit   - Sair")
        print("="*60)
        print()
        
        try:
            while self.rodando:
                cmd = input("Comando: ").strip()
                
                if cmd.lower() == 'quit':
                    break
                
                if cmd:
                    self.enviar(cmd)
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n\nInterrompido")
        finally:
            self.rodando = False
            if self.serial:
                self.serial.close()
            print("\nDesconectado")

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════╗
    ║     CONTROLE DIRETO - ARDUINO MEGA         ║
    ╚════════════════════════════════════════════╝
    """)
    
    porta = input("Porta serial (Enter=/dev/ttyUSB0): ").strip()
    if not porta:
        porta = '/dev/ttyUSB0'
    
    controle = ControleDireto(porta)
    controle.executar()
