## Envio de Pacotes pelo Arduino## Envio de Pacotes pelo Arduino

    

### URL de envio (POST)### URL de envio (POST)

[http://dominio/api/arduino/pacote/](URL)[http://dominio/api/arduino/pacote/](URL)

[]

[Build](https://chatgpt.com/share/68e8501f-69f4-8013-a1f5-a64da7b2f5ac)

[Build](https://chatgpt.com/share/68e8501f-69f4-8013-a1f5-a64da7b2f5ac)

### Exemplo de payload JSON

```json### Exemplo de payload JSON

{```json

  "codigo": "1234",{

  "nome": "PacoteTeste",  "codigo": "1234",

  "regiao": "Norte"  "nome": "PacoteTeste",

}  "regiao": "Norte"

```}



# DashLog# DashLog



Sistema de monitoramento de pacotes com leitura automática de QR codes.## Rodar com Docker



## 🚀 FuncionalidadesInstruções rápidas para rodar o projeto localmente usando Docker Compose.



- **Leitura automática de QR codes** via webcam ou IP Webcam- Build e subir em background:

- **Auto-start do QR Reader** quando o Django inicia

- **API REST** para receber e listar pacotes  docker compose up --build -d

- **Dashboard web** em tempo real

- Suporte para Docker e ambiente local- Ver logs do serviço web:



## 📋 Requisitos  docker compose logs -f web



- Python 3.11+- Parar e remover containers:

- Docker e Docker Compose (opcional)

- Webcam ou smartphone com IP Webcam app  docker compose down



## 🐳 Rodar com DockerObservações:

- Este projeto usa o Django com SQLite por padrão. Se o seu projeto precisar de dependências extras, adicione-as em `requirements.txt` antes de buildar a imagem.

### Build e iniciar os serviços- O `entrypoint.sh` executa `manage.py migrate` automaticamente antes de iniciar o servidor de desenvolvimento.



```bash
docker compose up --build -d
```

### Ver logs

```bash
docker compose logs -f web
```

### Parar containers

```bash
docker compose down
```

### Variáveis de ambiente (Docker)

Você pode configurar o QR Reader editando o `docker-compose.yml` ou criando um arquivo `.env`:

```env
QR_SOURCE=0                                              # 0 = webcam, ou URL do IP Webcam
QR_PORT=5001                                             # Porta do servidor Flask (use 5001 no macOS)
QR_BACKEND_URL=http://127.0.0.1:8000/api/arduino/pacote/  # URL do Django
QR_TUNNEL=false                                          # true para ativar Cloudflare tunnel
```

## 💻 Rodar localmente (sem Docker)

### 1. Criar e ativar virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
```

### 2. Instalar dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Executar migrações

```bash
python manage.py migrate
```

### 4. Iniciar o servidor Django (QR Reader inicia automaticamente)

**Opção 1: Script central (recomendado)** - Tudo em primeiro plano, Ctrl+C para parar:

```bash
python start.py
```

Com opções:

```bash
python start.py --migrate                           # Executa migrações antes
python start.py --qr-source="192.168.1.100:8080"   # IP Webcam
python start.py --tunnel                            # Ativa Cloudflare tunnel
python start.py --no-qr                             # Só Django, sem QR Reader
python start.py --help                              # Ver todas as opções
```

**Opção 2: Apenas Django** (QR Reader inicia em background):

```bash
python manage.py runserver 0.0.0.0:8001
```

O QR Reader será iniciado automaticamente em background na porta 5001.

> **Nota para macOS**: A porta 5000 é usada pelo AirPlay Receiver por padrão. Por isso, usamos a porta 5001.

### 5. Configurar variáveis de ambiente (opcional)

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Edite o `.env` conforme necessário e exporte as variáveis:

```bash
export $(cat .env | xargs)
```

### 6. Acessar a aplicação

- **Dashboard Django**: http://localhost:8001
- **Stream de vídeo do QR Reader**: http://localhost:5001/video.mjpg
- **Último QR lido**: http://localhost:5001/last_code

## 🎮 Gerenciar o QR Reader manualmente

Você pode controlar o serviço de QR code usando o management command:

### Iniciar manualmente

```bash
python manage.py qrcode start --source=0 --port=5001
```

### Parar

```bash
python manage.py qrcode stop
```

### Verificar status

```bash
python manage.py qrcode status
```

### Reiniciar

```bash
python manage.py qrcode restart --source=0 --tunnel
```

### Opções disponíveis

- `--source`: Fonte da câmera (0 para webcam padrão ou URL do IP Webcam)
- `--port`: Porta do servidor Flask (padrão: 5001, use 5001 no macOS para evitar conflito com AirPlay)
- `--backend-url`: URL do Django para enviar pacotes
- `--tunnel`: Ativar Cloudflare tunnel para acesso público

## 📱 Usar com IP Webcam (Android)

1. Instale o app "IP Webcam" no seu smartphone
2. Inicie o servidor no app (anote o endereço IP)
3. Configure o QR Reader:

```bash
# Exemplo: seu smartphone está em 192.168.1.100
export QR_SOURCE="192.168.1.100:8080"
python manage.py runserver
```

Ou com o comando manual:

```bash
python manage.py qrcode start --source="192.168.1.100:8080"
```

## 🌐 Expor via Cloudflare Tunnel

Para acessar o stream de QR code de qualquer lugar:

```bash
export QR_TUNNEL=true
python manage.py runserver
```

A URL pública será exibida nos logs como `[PUBLIC_VIDEO_URL]`.

## 📖 Formato do QR Code

O sistema espera QR codes no formato:

```
regiao:nome
```

Exemplos:
- `sul:paraiba`
- `norte:amazonas`
- `centro-oeste:brasilia`

Formato legado (ainda suportado):
```
regiao-nome
```

## 🔧 Troubleshooting

### Porta 8000/8001 já está em uso

Pare outros processos ou use outra porta:

```bash
python manage.py runserver 0.0.0.0:8002
```

### QR Reader não inicia automaticamente

Verifique os logs do Django:

```bash
python manage.py runserver
# Procure por "[Django] Iniciando QR Reader service..."
```

Ou inicie manualmente:

```bash
python manage.py qrcode start
```

### Câmera não detectada

Teste o script diretamente:

```bash
python script-read-qrcode.py --source=0
```

Tente outras fontes:
- `--source=1` (segunda câmera)
- `--source="<IP>:8080"` (IP Webcam)

## 📝 Notas

- O QR Reader inicia automaticamente quando o Django é iniciado via `runserver`
- As dependências incluem Django, Flask, OpenCV, requests
- O sistema usa SQLite por padrão (para produção, configure PostgreSQL/MySQL)
- O script `entrypoint.sh` executa `migrate` automaticamente antes de iniciar o servidor
