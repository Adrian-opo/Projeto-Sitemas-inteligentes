# 🚀 INÍCIO RÁPIDO

## Executar o Sistema

```bash
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8001
```

## Acessos

- **Dashboard**: http://localhost:8001
- **Câmera/QR**: http://localhost:5001/video.mjpg

---

## ⚙️ Configurações

### Alterar Porta Serial do Arduino
📁 `dashboard/views.py` - linha 32:
```python
self.porta = '/dev/ttyACM0'  
```

### Alterar Força dos Motores (Passos)
📁 `arduino/src/main.cpp` - linha 12:
```cpp
const long PASSOS_REGIAO = 1500;  
```

---

## 📦 Após alterar o Arduino

```bash
cd arduino
pio run --target upload
```
