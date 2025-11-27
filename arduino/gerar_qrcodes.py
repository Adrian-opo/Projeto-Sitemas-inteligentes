#!/usr/bin/env python3
"""
Gerador de QR Codes para Sistema de Seleção
Cria QR Codes A-E para testes
"""

import qrcode
import os

def gerar_qr_codes():
    """Gera QR Codes para todos os destinos"""
    
    destinos = {
        'A': 'Posição A - Base 0°',
        'B': 'Posição B - Base 45°',
        'C': 'Posição C - Base 90°',
        'D': 'Posição D - Base 135°',
        'E': 'Posição E - Base 180°'
    }
    
    # Cria diretório para os QR Codes
    pasta = 'qr_codes'
    if not os.path.exists(pasta):
        os.makedirs(pasta)
    
    print("Gerando QR Codes...")
    print("-" * 50)
    
    for codigo, descricao in destinos.items():
        # Configura QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        # Adiciona dados
        qr.add_data(codigo)
        qr.make(fit=True)
        
        # Cria imagem
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Salva arquivo
        nome_arquivo = f"{pasta}/destino_{codigo}.png"
        img.save(nome_arquivo)
        
        print(f"✓ {codigo}: {descricao}")
        print(f"  Arquivo: {nome_arquivo}")
    
    print("-" * 50)
    print(f"\n✓ {len(destinos)} QR Codes gerados na pasta '{pasta}/'")
    print("\nPara testar:")
    print("1. Abra as imagens em uma tela/celular")
    print("2. Execute o sistema: python3 controle_sistema.py")
    print("3. Escolha opção 'Q' ou faça o ciclo completo")
    print("4. Aponte a câmera para o QR Code")

def gerar_qr_personalizado():
    """Permite gerar QR Code personalizado"""
    print("\n" + "="*50)
    print("GERADOR DE QR CODE PERSONALIZADO")
    print("="*50)
    
    codigo = input("\nDigite o código para o QR Code: ").strip().upper()
    
    if not codigo:
        print("✗ Código vazio!")
        return
    
    # Configura QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    qr.add_data(codigo)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    pasta = 'qr_codes'
    if not os.path.exists(pasta):
        os.makedirs(pasta)
    
    nome_arquivo = f"{pasta}/custom_{codigo}.png"
    img.save(nome_arquivo)
    
    print(f"\n✓ QR Code '{codigo}' gerado!")
    print(f"  Arquivo: {nome_arquivo}")

def visualizar_qr_codes():
    """Mostra todos os QR Codes gerados"""
    import cv2
    import glob
    
    pasta = 'qr_codes'
    arquivos = glob.glob(f"{pasta}/*.png")
    
    if not arquivos:
        print("✗ Nenhum QR Code encontrado!")
        print("  Execute a opção 1 para gerar QR Codes primeiro.")
        return
    
    print(f"\nEncontrados {len(arquivos)} QR Codes")
    print("Pressione qualquer tecla para ver o próximo, ESC para sair\n")
    
    for arquivo in sorted(arquivos):
        img = cv2.imread(arquivo)
        nome = os.path.basename(arquivo)
        
        # Redimensiona para visualização melhor
        altura, largura = img.shape[:2]
        nova_largura = 400
        nova_altura = int(altura * nova_largura / largura)
        img_resized = cv2.resize(img, (nova_largura, nova_altura))
        
        cv2.putText(img_resized, nome, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        cv2.imshow('QR Codes - Pressione ESC para sair', img_resized)
        
        tecla = cv2.waitKey(0)
        if tecla == 27:  # ESC
            break
    
    cv2.destroyAllWindows()

def menu():
    """Menu principal"""
    while True:
        print("\n" + "="*50)
        print("GERADOR DE QR CODES - SISTEMA DE SELEÇÃO")
        print("="*50)
        print("\n1 - Gerar QR Codes padrão (A-E)")
        print("2 - Gerar QR Code personalizado")
        print("3 - Visualizar QR Codes gerados")
        print("4 - Sair")
        print("="*50)
        
        escolha = input("\nEscolha uma opção: ").strip()
        
        if escolha == '1':
            gerar_qr_codes()
        elif escolha == '2':
            gerar_qr_personalizado()
        elif escolha == '3':
            visualizar_qr_codes()
        elif escolha == '4':
            print("\nEncerrando...")
            break
        else:
            print("\n✗ Opção inválida!")

if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\n\nPrograma interrompido pelo usuário")
    except ImportError as e:
        print(f"\n✗ Erro: Biblioteca não encontrada - {e}")
        print("\nInstale as dependências:")
        print("  pip install qrcode[pil] opencv-python")
