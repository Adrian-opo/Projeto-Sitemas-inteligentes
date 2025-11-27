#!/usr/bin/env python3
"""
Script de Teste Simplificado - Motores de Passo
Testa movimentos pequenos e mostra posições em tempo real
"""

import serial
import time
import sys

class TestadorMotores:
    def __init__(self, porta='/dev/ttyACM0', baudrate=115200):
        self.porta = porta
        self.baudrate = baudrate
        self.serial_conn = None
    
    def conectar(self):
        """Conecta ao Arduino"""
        try:
            print(f"Conectando a {self.porta}...")
            self.serial_conn = serial.Serial(self.porta, self.baudrate, timeout=1)
            time.sleep(2)
            
            # Limpa buffer inicial
            while self.serial_conn.in_waiting:
                linha = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                print(f"  {linha}")
            
            print("✓ Conectado!\n")
            return True
        except Exception as e:
            print(f"✗ Erro: {e}")
            return False
    
    def enviar_comando(self, cmd):
        """Envia comando e mostra todas as respostas"""
        if not self.serial_conn:
            return
        
        print(f"\n→ Comando: {cmd}")
        self.serial_conn.write(f"{cmd}\n".encode())
        
        time.sleep(0.5)
        while self.serial_conn.in_waiting:
            linha = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
            if linha:
                print(f"  {linha}")
        
        time.sleep(0.1)
    
    def teste_basico(self):
        """Teste básico de movimentos"""
        print("\n" + "="*60)
        print("TESTE BÁSICO - MOTORES DE PASSO")
        print("="*60)
        
        # Zera posições
        print("\n1. Zerando posições...")
        self.enviar_comando('Z')
        time.sleep(0.5)
        
        # Mostra posição inicial
        print("\n2. Posição inicial:")
        self.enviar_comando('?')
        time.sleep(0.5)
        
        # Teste Motor 1 - Pequenos movimentos
        print("\n3. Motor 1 - 50 passos frente:")
        self.enviar_comando('1F50')
        time.sleep(2)
        
        print("\n4. Motor 1 - 50 passos trás (volta ao zero):")
        self.enviar_comando('1B50')
        time.sleep(2)
        
        # Teste Motor 2
        print("\n5. Motor 2 - 50 passos frente:")
        self.enviar_comando('2F50')
        time.sleep(2)
        
        print("\n6. Motor 2 - 50 passos trás (volta ao zero):")
        self.enviar_comando('2B50')
        time.sleep(2)
        
        # Posição final
        print("\n7. Posição final (deve ser próxima a zero):")
        self.enviar_comando('?')
        
        print("\n" + "="*60)
        print("TESTE CONCLUÍDO!")
        print("="*60)
    
    def teste_incremental(self):
        """Teste com incrementos graduais"""
        print("\n" + "="*60)
        print("TESTE INCREMENTAL - 10 MOVIMENTOS DE 20 PASSOS")
        print("="*60)
        
        self.enviar_comando('Z')
        time.sleep(0.5)
        
        for i in range(1, 11):
            print(f"\n--- Movimento {i}/10 ---")
            self.enviar_comando('1F20')
            time.sleep(1.5)
        
        print("\n=== Posição após 200 passos totais ===")
        self.enviar_comando('?')
        
        print("\nVoltando ao zero...")
        self.enviar_comando('1B200')
        time.sleep(3)
        
        print("\n=== Posição final ===")
        self.enviar_comando('?')
    
    def teste_ambos_motores(self):
        """Teste com ambos motores simultaneamente"""
        print("\n" + "="*60)
        print("TESTE AMBOS MOTORES - COMANDO M")
        print("="*60)
        
        self.enviar_comando('Z')
        time.sleep(0.5)
        
        print("\nMovendo ambos motores (200 passos cada)...")
        self.enviar_comando('M')
        time.sleep(5)
        
        print("\nPosição final:")
        self.enviar_comando('?')
    
    def menu_interativo(self):
        """Menu de testes"""
        while True:
            print("\n" + "="*60)
            print("TESTADOR DE MOTORES DE PASSO")
            print("="*60)
            print("\n1 - Teste básico (movimentos pequenos)")
            print("2 - Teste incremental (10x20 passos)")
            print("3 - Teste ambos motores")
            print("4 - Comando manual")
            print("5 - Zerar posições")
            print("6 - Mostrar posição atual")
            print("7 - Monitorar continuamente")
            print("0 - Sair")
            print("="*60)
            
            escolha = input("\nEscolha: ").strip()
            
            if escolha == '1':
                self.teste_basico()
            elif escolha == '2':
                self.teste_incremental()
            elif escolha == '3':
                self.teste_ambos_motores()
            elif escolha == '4':
                cmd = input("Digite o comando: ").strip()
                self.enviar_comando(cmd)
                time.sleep(2)
            elif escolha == '5':
                self.enviar_comando('Z')
                time.sleep(0.5)
            elif escolha == '6':
                self.enviar_comando('?')
                time.sleep(0.5)
            elif escolha == '7':
                print("\nMonitorando... (Ctrl+C para parar)")
                try:
                    while True:
                        if self.serial_conn.in_waiting:
                            linha = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                            if linha:
                                print(f"  {linha}")
                        time.sleep(0.05)
                except KeyboardInterrupt:
                    print("\nMonitoramento interrompido")
            elif escolha == '0':
                break
            else:
                print("✗ Opção inválida!")
    
    def executar(self):
        """Executa testador"""
        if self.conectar():
            try:
                self.menu_interativo()
            except KeyboardInterrupt:
                print("\n\nInterrompido pelo usuário")
            finally:
                if self.serial_conn:
                    self.serial_conn.close()
                print("\nConexão encerrada.")

def main():
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║       TESTADOR DE MOTORES DE PASSO - TEMPO REAL      ║
    ║              Arduino Mega 2560 - Pinos 30-33         ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    porta = input("Porta serial (padrão /dev/ttyACM0): ").strip()
    if not porta:
        porta = '/dev/ttyACM0'
    
    testador = TestadorMotores(porta)
    testador.executar()

if __name__ == "__main__":
    main()
