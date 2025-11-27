import os
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    
    def ready(self):
        """
        Chamado quando o app Django está pronto.
        Inicia o serviço de leitura de QR code automaticamente.
        """
        # Evita executar duas vezes no runserver (autoreload)
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        # Não inicia se o start.py está gerenciando
        if os.environ.get('DASHLOG_DISABLE_QR_AUTOSTART') == '1':
            print("[Django] QR Reader gerenciado pelo start.py, pulando auto-start.", flush=True)
            return
        
        try:
            from qrcode_service import start_qr_reader_service
            
            # Configura os parâmetros (pode ajustar conforme necessário)
            source = os.environ.get('QR_SOURCE', '0')  # câmera padrão ou IP Webcam URL
            port = int(os.environ.get('QR_PORT', '5001'))
            backend_url = os.environ.get('QR_BACKEND_URL', 'http://127.0.0.1:8001/api/arduino/pacote/')
            tunnel = os.environ.get('QR_TUNNEL', '').lower() in ('true', '1', 'yes')
            
            print(f"[Django] Iniciando QR Reader service (source={source}, port={port})...", flush=True)
            start_qr_reader_service(
                source=source,
                port=port,
                backend_url=backend_url,
                tunnel=tunnel
            )
        except Exception as e:
            print(f"[Django] ERRO ao iniciar QR Reader service: {e}", flush=True)
