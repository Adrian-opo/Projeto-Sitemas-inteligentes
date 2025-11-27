from django.urls import path
from django.contrib import admin
from . import views

urlpatterns= [
  path('admin/', admin.site.urls),
  path('', views.index, name='index'), 
  path("api/arduino/pacote/", views.receber_pacote_arduino, name="receber_pacote_arduino"), 
  path("api/pacote/", views.listar_pacotes, name="listar_pacotes"),
  path("camera/", views.camera_view, name="camera_view"),
  
  # Rotas de controle do Arduino
  path("api/arduino/conectar/", views.arduino_conectar, name="arduino_conectar"),
  path("api/arduino/comando/", views.arduino_comando, name="arduino_comando"),
  path("api/arduino/iniciar/", views.arduino_iniciar_ciclo, name="arduino_iniciar"),
  path("api/arduino/regiao/", views.arduino_enviar_regiao, name="arduino_regiao"),
  path("api/arduino/status/", views.arduino_status, name="arduino_status"),
  path("api/arduino/reset/", views.arduino_reset, name="arduino_reset"),
]