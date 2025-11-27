#!/usr/bin/env python3
"""
Controlador Integrado - Sistema de Separação por Regiões
Integra o Dashboard Django com o Arduino para automação completa.

Fluxo de operação:
1. Arduino pega objeto e posiciona na frente da câmera
2. Câmera lê QR code e envia região para o backend Django
3. Este controlador recebe a região e envia comando ao Arduino
4. Arduino move defletor, solta objeto e retorna à posição inicial

Autor: Sistema Automatizado
Data: 27/11/2025
"""

import serial
import time
import threading
import requests
import sys
import os

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ControladorIntegrado:
    """
    Controlador que integra o Arduino com o backend Django.
    Monitora o backend para novos pacotes e envia comandos ao Arduino.
    """
    
    # Mapeamento de regiões válidas
    REGIOES_VALIDAS = ['norte', 'nordeste', 'centro-oeste', 'sudeste', 'sul']
    
    def __init__(self, porta_serial='/dev/ttyACM0', baudrate=115200, backend_url='http://127.0.0.1:8001'):
        """
        Inicializa o controlador integrado.
        
        Args:
            porta_serial: Porta serial do Arduino
            baudrate: Taxa de comunicação
            backend_url: URL base do backend Django
        """
        self.porta = porta_serial
        self.baudrate = baudrate
        self.backend_url = backend_url.rstrip('/')
        self.serial_conn = None
        self.executando = True
        self.aguardando_qr = False
        self.ultimo_codigo_processado = None
        
        # Thread para monitorar serial
        self._monitor_thread = None
        
    def conectar_serial(self):
        """Estabelece conexão serial com Arduino."""
        try:
            self.serial_conn = serial.Serial(
                self.porta,
                self.baudrate,
                timeout=0.1
            )
            time.sleep(2)  # Aguarda reset do Arduino
            print(f"✓ Conectado ao Arduino em {self.porta}")
            
            # Lê mensagens iniciais
            for _ in range(20):
                if self.serial_conn.in_waiting:
                    linha = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if linha:
                        print(f"  Arduino: {linha}")
                time.sleep(0.1)
            
            return True
        except Exception as e:
            print(f"✗ Erro ao conectar Arduino: {e}")
            return False
    
    def enviar_comando(self, comando):
        """
        Envia comando para o Arduino.
        
        Args:
            comando: String com o comando
            
        Returns:
            True se enviado com sucesso
        """
        if not self.serial_conn:
            print("✗ Serial não conectada!")
            return False
        
        try:
            self.serial_conn.write(f"{comando}\n".encode())
            print(f"→ Arduino: {comando}")
            return True
        except Exception as e:
            print(f"✗ Erro ao enviar: {e}")
            return False
    
    def ler_resposta_arduino(self, timeout=30):
        """
        Lê resposta do Arduino até receber OK ou timeout.
        
        Args:
            timeout: Tempo máximo de espera em segundos
            
        Returns:
            Lista de linhas recebidas
        """
        respostas = []
        tempo_inicio = time.time()
        
        while (time.time() - tempo_inicio) < timeout:
            if self.serial_conn and self.serial_conn.in_waiting:
                try:
                    linha = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if linha:
                        respostas.append(linha)
                        print(f"← Arduino: {linha}")
                        
                        # Verifica sinais especiais
                        if linha == "READY_FOR_QR":
                            self.aguardando_qr = True
                            return respostas
                        elif linha == "OK" or linha == "PRONTO":
                            self.aguardando_qr = False
                            return respostas
                        elif linha.startswith("ERRO:"):
                            return respostas
                except Exception as e:
                    print(f"  Erro leitura: {e}")
            
            time.sleep(0.01)
        
        return respostas
    
    def buscar_ultimo_pacote(self):
        """
        Busca o último pacote registrado no backend Django.
        
        Returns:
            Dict com dados do pacote ou None
        """
        try:
            url = f"{self.backend_url}/api/pacote/"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('pacotes') and len(data['pacotes']) > 0:
                return data['pacotes'][0]  # Mais recente
            return None
            
        except Exception as e:
            print(f"  Erro ao buscar pacote: {e}")
            return None
    
    def normalizar_regiao(self, regiao):
        """
        Normaliza o nome da região para o formato esperado pelo Arduino.
        
        Args:
            regiao: Nome da região
            
        Returns:
            Região normalizada ou None se inválida
        """
        if not regiao:
            return None
        
        regiao = regiao.lower().strip()
        
        # Tratamentos especiais
        if regiao in ['centro-oeste', 'centro oeste', 'centrooeste', 'centro_oeste']:
            return 'centro-oeste'
        
        if regiao in self.REGIOES_VALIDAS:
            return regiao
        
        return None
    
    def iniciar_ciclo(self):
        """
        Inicia um ciclo completo: pegar objeto e aguardar QR code.
        """
        print("\n" + "="*60)
        print("INICIANDO NOVO CICLO")
        print("="*60)
        
        # Envia comando para pegar objeto
        self.enviar_comando("INICIAR")
        respostas = self.ler_resposta_arduino(timeout=30)
        
        if self.aguardando_qr:
            print("\n✓ Objeto capturado! Aguardando leitura do QR code...")
            return True
        else:
            print("\n✗ Falha ao iniciar ciclo")
            return False
    
    def processar_regiao(self, regiao):
        """
        Processa a região lida do QR code.
        
        Args:
            regiao: Nome da região
            
        Returns:
            True se processado com sucesso
        """
        regiao_normalizada = self.normalizar_regiao(regiao)
        
        if not regiao_normalizada:
            print(f"✗ Região inválida: {regiao}")
            print(f"  Regiões válidas: {', '.join(self.REGIOES_VALIDAS)}")
            return False
        
        print(f"\n✓ Região detectada: {regiao_normalizada.upper()}")
        
        # Envia comando de região para o Arduino
        comando = f"REGIAO:{regiao_normalizada}"
        self.enviar_comando(comando)
        
        # Aguarda conclusão do ciclo
        respostas = self.ler_resposta_arduino(timeout=60)
        
        if "PRONTO" in respostas or "OK" in respostas:
            print("\n✓ Ciclo concluído com sucesso!")
            return True
        else:
            print("\n⚠ Ciclo pode não ter sido concluído corretamente")
            return False
    
    def monitorar_backend(self):
        """
        Thread que monitora o backend para novos pacotes.
        Quando um novo pacote é detectado e o Arduino está aguardando QR,
        envia automaticamente a região para o Arduino.
        """
        print("\n[Monitor] Iniciando monitoramento do backend...")
        
        while self.executando:
            try:
                # Só verifica se Arduino está aguardando QR
                if self.aguardando_qr:
                    pacote = self.buscar_ultimo_pacote()
                    
                    if pacote and pacote.get('codigo') != self.ultimo_codigo_processado:
                        regiao = pacote.get('regiao')
                        codigo = pacote.get('codigo')
                        nome = pacote.get('nome', 'Desconhecido')
                        
                        print(f"\n[Monitor] Novo pacote detectado!")
                        print(f"  Código: {codigo}")
                        print(f"  Nome: {nome}")
                        print(f"  Região: {regiao}")
                        
                        # Processa a região
                        if self.processar_regiao(regiao):
                            self.ultimo_codigo_processado = codigo
                
            except Exception as e:
                print(f"[Monitor] Erro: {e}")
            
            time.sleep(0.5)  # Polling a cada 500ms
    
    def modo_automatico(self):
        """
        Executa o sistema em modo completamente automático.
        Inicia ciclos continuamente e processa regiões do backend.
        """
        print("\n" + "="*60)
        print("MODO AUTOMÁTICO - OPERAÇÃO CONTÍNUA")
        print("="*60)
        print("Pressione Ctrl+C para parar")
        print("="*60)
        
        # Inicia thread de monitoramento do backend
        self._monitor_thread = threading.Thread(
            target=self.monitorar_backend,
            daemon=True
        )
        self._monitor_thread.start()
        
        try:
            while self.executando:
                # Se não está aguardando QR, inicia novo ciclo
                if not self.aguardando_qr:
                    print("\n[Auto] Pronto para novo ciclo")
                    input("  Pressione ENTER para iniciar ou Ctrl+C para sair...")
                    self.iniciar_ciclo()
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n[Auto] Parando sistema...")
            self.executando = False
    
    def modo_manual(self):
        """
        Executa o sistema em modo manual com menu interativo.
        """
        while self.executando:
            print("\n" + "="*60)
            print("MENU - CONTROLE MANUAL")
            print("="*60)
            print("1 - Iniciar ciclo (pegar objeto)")
            print("2 - Enviar região manualmente")
            print("3 - Calibrar sistema")
            print("4 - Status do Arduino")
            print("5 - Reset de emergência")
            print("A - Modo automático")
            print("X - Sair")
            print("="*60)
            
            escolha = input("\nEscolha: ").strip().upper()
            
            if escolha == '1':
                self.iniciar_ciclo()
                
            elif escolha == '2':
                print(f"\nRegiões válidas: {', '.join(self.REGIOES_VALIDAS)}")
                regiao = input("Digite a região: ").strip()
                self.processar_regiao(regiao)
                
            elif escolha == '3':
                self.enviar_comando("C")
                self.ler_resposta_arduino(timeout=10)
                
            elif escolha == '4':
                self.enviar_comando("STATUS")
                self.ler_resposta_arduino(timeout=5)
                
            elif escolha == '5':
                self.enviar_comando("RESET")
                self.ler_resposta_arduino(timeout=10)
                self.aguardando_qr = False
                
            elif escolha == 'A':
                self.modo_automatico()
                
            elif escolha == 'X':
                self.executando = False
                print("Encerrando...")
                
            else:
                print("Opção inválida!")
    
    def executar(self, modo='manual'):
        """
        Executa o controlador.
        
        Args:
            modo: 'manual' ou 'automatico'
        """
        if not self.conectar_serial():
            print("\n✗ Não foi possível conectar ao Arduino")
            print("  Verifique se o Arduino está conectado e a porta está correta")
            return
        
        try:
            if modo == 'automatico':
                self.modo_automatico()
            else:
                self.modo_manual()
                
        except KeyboardInterrupt:
            print("\n\nInterrompido pelo usuário")
        finally:
            self.executando = False
            if self.serial_conn:
                self.serial_conn.close()
            print("Conexão fechada.")


def main():
    """Função principal."""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  CONTROLADOR INTEGRADO - SISTEMA DE SEPARAÇÃO           ║
    ║  Arduino + Django + QR Code                              ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Configurações
    porta = input("Porta serial (Enter=/dev/ttyACM0): ").strip()
    if not porta:
        porta = '/dev/ttyACM0'
    
    backend = input("URL do backend (Enter=http://127.0.0.1:8001): ").strip()
    if not backend:
        backend = 'http://127.0.0.1:8001'
    
    modo = input("Modo [M]anual ou [A]utomático (Enter=M): ").strip().upper()
    modo = 'automatico' if modo == 'A' else 'manual'
    
    # Cria e executa controlador
    controlador = ControladorIntegrado(
        porta_serial=porta,
        backend_url=backend
    )
    
    controlador.executar(modo=modo)


if __name__ == "__main__":
    main()
