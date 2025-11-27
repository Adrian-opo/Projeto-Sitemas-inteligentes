"""
Management command para controlar o serviço de leitura de QR code.

Uso:
    python manage.py qrcode start [--source=0] [--port=5000] [--tunnel]
    python manage.py qrcode stop
    python manage.py qrcode status
"""
from django.core.management.base import BaseCommand
from qrcode_service import start_qr_reader_service, stop_qr_reader_service, get_qr_reader_status


class Command(BaseCommand):
    help = 'Controla o serviço de leitura de QR code'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['start', 'stop', 'status', 'restart'],
            help='Ação a executar: start, stop, status ou restart'
        )
        parser.add_argument(
            '--source',
            type=str,
            default='0',
            help='Fonte da câmera (0 para webcam padrão ou URL do IP Webcam)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=5001,
            help='Porta para o servidor Flask do QR reader (padrão: 5001)'
        )
        parser.add_argument(
            '--backend-url',
            type=str,
            default='http://127.0.0.1:8001/api/arduino/pacote/',
            help='URL do backend Django para enviar os pacotes'
        )
        parser.add_argument(
            '--tunnel',
            action='store_true',
            help='Ativar cloudflare tunnel para acesso público'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'start':
            self.stdout.write(self.style.SUCCESS('Iniciando serviço de QR code...'))
            process = start_qr_reader_service(
                source=options['source'],
                port=options['port'],
                backend_url=options['backend_url'],
                tunnel=options['tunnel']
            )
            if process:
                self.stdout.write(self.style.SUCCESS(f'Serviço iniciado com PID {process.pid}'))
            else:
                self.stdout.write(self.style.ERROR('Falha ao iniciar o serviço'))

        elif action == 'stop':
            self.stdout.write(self.style.WARNING('Parando serviço de QR code...'))
            stop_qr_reader_service()
            self.stdout.write(self.style.SUCCESS('Serviço parado'))

        elif action == 'status':
            status = get_qr_reader_status()
            if status['running']:
                self.stdout.write(self.style.SUCCESS(f'Serviço rodando (PID: {status["pid"]})'))
            else:
                self.stdout.write(self.style.WARNING('Serviço não está rodando'))
                if 'exit_code' in status:
                    self.stdout.write(f'Último exit code: {status["exit_code"]}')

        elif action == 'restart':
            self.stdout.write(self.style.WARNING('Reiniciando serviço...'))
            stop_qr_reader_service()
            import time
            time.sleep(1)
            process = start_qr_reader_service(
                source=options['source'],
                port=options['port'],
                backend_url=options['backend_url'],
                tunnel=options['tunnel']
            )
            if process:
                self.stdout.write(self.style.SUCCESS(f'Serviço reiniciado com PID {process.pid}'))
            else:
                self.stdout.write(self.style.ERROR('Falha ao reiniciar o serviço'))
