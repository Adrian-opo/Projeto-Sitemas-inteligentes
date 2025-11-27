# Sistema de Controle - Garra Robótica com Separação por Regiões

Sistema automatizado de separação de objetos por regiões do Brasil usando garra robótica, leitura de QR Code e motores de passo.

## 📋 Visão Geral

O sistema funciona em um ciclo automatizado:
1. **Garra pega objeto** e posiciona na frente da câmera
2. **Câmera lê QR Code** com formato `regiao:nome` (ex: `sul:parana`)
3. **Sistema identifica região** e move o defletor correspondente
4. **Garra solta objeto** na esteira
5. **Defletor direciona** objeto para a região correta
6. **Sistema retorna** à posição inicial para próximo ciclo

## 🗺️ Mapeamento das 5 Regiões

| Região | Motor | Direção | Passos |
|--------|-------|---------|--------|
| **Norte** | M1 | Horário (CW) | 1500 |
| **Nordeste** | M3 | Horário (CW) | 1500 |
| **Centro-Oeste** | - | Sem movimento | 0 |
| **Sudeste** | M1 | Anti-horário (CCW) | 1500 |
| **Sul** | M3 | Anti-horário (CCW) | 1500 |

## 📦 Componentes

### Hardware
- **Arduino Mega 2560**
- **Servos** (4x):
  - Pino 3: Garra
  - Pino 5: Base
  - Pino 8: Antebraço
  - Pino 10: Braço
- **Motores de Passo** (2x - 28BYJ-48):
  - Motor 1 (M1): Pinos 30, 31, 32, 33 - Defletor A
  - Motor 3 (M3): Pinos 26, 27, 28, 29 - Defletor B (lado oposto)
- **Câmera** (webcam USB)

### Software
- PlatformIO / Arduino IDE
- Python 3.x
- Django (backend)
- Flask (streaming de vídeo)
- OpenCV + Pyzbar (leitura QR)

## 🚀 Instalação

### 1. Compilar e fazer upload do firmware

```bash
cd arduino
pio run --target upload
```

### 2. Iniciar o sistema Django

```bash
# Na raiz do projeto
python manage.py runserver 0.0.0.0:8001
```

### 3. Executar o controlador integrado (opcional)

```bash
cd arduino
python controle_integrado.py
```

## 🎮 Comandos do Arduino

### Via Serial (115200 baud)

| Comando | Descrição |
|---------|-----------|
| `INICIAR` | Inicia ciclo - pega objeto e aguarda QR |
| `REGIAO:<nome>` | Processa região (ex: `REGIAO:norte`) |
| `C` ou `CALIBRAR` | Calibração inicial dos servos |
| `STATUS` | Mostra estado atual do sistema |
| `RESET` | Reset de emergência |

### Estados do Sistema

- `AGUARDANDO` - Pronto para novo ciclo
- `PEGANDO_OBJETO` - Garra pegando objeto
- `AGUARDANDO_QR` - Objeto na câmera, aguardando leitura
- `MOVENDO_DEFLETOR` - Motor movendo defletor
- `SOLTANDO_OBJETO` - Garra soltando na esteira
- `RETORNANDO_DEFLETOR` - Defletor voltando à posição
- `VOLTANDO_POSICAO` - Garra voltando à posição inicial

## 🔌 API REST (Django)

### Endpoints de Controle

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/arduino/conectar/` | Conecta ao Arduino |
| POST | `/api/arduino/iniciar/` | Inicia ciclo de pegar objeto |
| POST | `/api/arduino/regiao/` | Envia região para o Arduino |
| GET | `/api/arduino/status/` | Status da conexão |
| POST | `/api/arduino/reset/` | Reset de emergência |
| POST | `/api/arduino/comando/` | Envia comando direto |

### Exemplos

```bash
# Conectar ao Arduino
curl -X POST http://localhost:8001/api/arduino/conectar/ \
  -H "Content-Type: application/json" \
  -d '{"porta": "/dev/ttyACM0"}'

# Iniciar ciclo
curl -X POST http://localhost:8001/api/arduino/iniciar/

# Enviar região
curl -X POST http://localhost:8001/api/arduino/regiao/ \
  -H "Content-Type: application/json" \
  -d '{"regiao": "sul"}'

# Status
curl http://localhost:8001/api/arduino/status/
```

## 📊 Fluxo do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     CICLO AUTOMÁTICO                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   1. INICIAR CICLO    │
               │   (Comando INICIAR)   │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   2. PEGAR OBJETO     │
               │   - Mover garra       │
               │   - Fechar garra      │
               │   - Posicionar câmera │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   3. AGUARDAR QR      │◄──── Câmera lê QR Code
               │   (READY_FOR_QR)      │      e envia região
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   4. MOVER DEFLETOR   │
               │   - Norte: M1 CW      │
               │   - Nordeste: M3 CW   │
               │   - Centro-Oeste: -   │
               │   - Sudeste: M1 CCW   │
               │   - Sul: M3 CCW       │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   5. SOLTAR OBJETO    │
               │   - Abrir garra       │
               │   - Objeto na esteira │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   6. AGUARDAR ESTEIRA │
               │   (5 segundos)        │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   7. RETORNAR         │
               │   - Defletor volta    │
               │   - Garra volta       │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   8. PRONTO           │
               │   (Novo ciclo)        │
               └───────────────────────┘
```

## 📝 Formato do QR Code

O QR Code deve conter informação no formato:

```
regiao:nome
```

### Exemplos:
- `norte:amazonas`
- `nordeste:bahia`
- `centro-oeste:brasilia`
- `sudeste:saopaulo`
- `sul:parana`

## 🔧 Configuração

### Ajustar quantidade de passos

No arquivo `main.cpp`, altere a constante:

```cpp
const long PASSOS_REGIAO = 1500;  // Ajuste conforme necessário
```

### Ajustar tempo de espera da esteira

```cpp
const unsigned long TEMPO_ESTEIRA = 5000;  // 5 segundos
```

### Velocidade dos motores

```cpp
const float RPM_TARGET = 15.0f;  // RPM dos motores de passo
```

## 🐛 Troubleshooting

### Arduino não responde
1. Verifique conexão USB
2. Confirme a porta serial: `ls /dev/tty*`
3. Tente reset manual (botão no Arduino)

### Motor não move
1. Verifique alimentação (5V para 28BYJ-48)
2. Confirme conexões dos pinos
3. Teste com comando: `REGIAO:norte`

### QR Code não é lido
1. Verifique iluminação
2. Ajuste distância da câmera
3. Verifique formato do QR: `regiao:nome`

### Garra não abre/fecha
1. Verifique alimentação dos servos
2. Teste calibração: `C`

## 📁 Arquivos

```
arduino/
├── src/
│   └── main.cpp           # Firmware do Arduino (automatizado)
├── controle_integrado.py  # Controlador Python integrado
├── controle_sistema.py    # Controlador com menu (legado)
├── controle_direto.py     # Comandos diretos (debug)
├── platformio.ini         # Configuração PlatformIO
└── README.md              # Esta documentação
```

## 📜 Licença

Projeto acadêmico - Sistemas Inteligentes
