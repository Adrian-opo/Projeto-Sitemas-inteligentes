# 🚀 GUIA DE INÍCIO RÁPIDO

## Setup Inicial (Execute APENAS UMA VEZ)

### 1. Instalar Dependências Python
```bash
cd /home/renan/Documentos/PlatformIO/Projects/TESTESMOTOR
pip install -r requirements.txt
```

### 2. Compilar e Fazer Upload do Firmware
```bash
pio run --target upload
```

## 🧪 Testar Motores de Passo (RECOMENDADO COMEÇAR AQUI)

Execute o testador simplificado:
```bash
python3 teste_motores.py
```

### Comandos Rápidos de Teste:
- **Opção 1**: Teste básico (50 passos frente e volta)
- **Opção 6**: Ver posição atual dos motores
- **Opção 5**: Zerar contadores

### Teste Manual via Monitor Serial:
```bash
pio device monitor
```

Digite os comandos:
```
Z          # Zera posições
1F100      # Motor 1: 100 passos frente
?          # Mostra posição atual
1B100      # Motor 1: 100 passos trás (volta)
2F50       # Motor 2: 50 passos frente
?          # Mostra posição atual
```

## 📸 Gerar QR Codes para Testes

```bash
python3 gerar_qrcodes.py
```

Escolha **opção 1** para gerar QR Codes A-E na pasta `qr_codes/`

## 🤖 Sistema Completo (Garra + QR Code + Esteira)

```bash
python3 controle_sistema.py
```

### Primeiro Teste: Calibração
1. Execute o script
2. Escolha **opção 2** (Calibração inicial)
3. Observe os servos se movendo suavemente

### Teste Completo com QR Code:
1. Execute o script
2. Escolha **opção 1** (Ciclo completo automático)
3. Quando aparecer "AGUARDANDO QR CODE", mostre um QR Code (A-E)
4. Sistema irá:
   - Pegar objeto
   - Ler QR Code
   - Mover para posição
   - Soltar na esteira
   - Voltar ao início

## 📊 Entendendo a Saída dos Motores

Quando você move um motor, verá algo assim:
```
POS:100,0|GRAUS:17.6,0.0
```

- **POS**: Posição em passos (Motor1, Motor2)
- **GRAUS**: Posição em graus (Motor1, Motor2)
- Para 28BYJ-48: 2048 passos = 360°

## 🔍 Verificação de Problemas

### Motores não giram?
1. Verifique alimentação 5V
2. Confirme pinos: 30, 31, 32, 33 (Motor 1)
3. Teste com: `1F10` (apenas 10 passos)

### Câmera não funciona?
```bash
ls /dev/video*
```
Se aparecer `video0`, use índice 0. Se aparecer `video1`, edite o código.

### Porta serial errada?
```bash
ls /dev/tty* | grep -E "(ACM|USB)"
```

## 📁 Arquivos Criados

```
TESTESMOTOR/
├── src/main.cpp              ← Firmware Arduino
├── controle_sistema.py       ← Sistema completo
├── teste_motores.py          ← Testador simplificado
├── gerar_qrcodes.py          ← Gerador de QR Codes
├── requirements.txt          ← Dependências Python
├── README.md                 ← Documentação completa
└── INICIO_RAPIDO.md          ← Este arquivo
```

## 🎯 Ordem Recomendada de Testes

1. ✅ Upload do firmware
2. ✅ `teste_motores.py` - Opção 1 (teste básico)
3. ✅ `gerar_qrcodes.py` - Opção 1 (gerar QR Codes)
4. ✅ `controle_sistema.py` - Opção 2 (calibração)
5. ✅ `controle_sistema.py` - Opção 1 (ciclo completo)

## 💡 Dicas

- **Movimento suave**: Use 50-200 passos por vez
- **Velocidade**: Configurada em `RPM_TARGET = 15.0` no firmware
- **QR Codes**: Imprima ou mostre em tela de celular
- **Câmera**: Boa iluminação é essencial

## 🆘 Ajuda

Veja `README.md` para documentação completa e troubleshooting detalhado.
