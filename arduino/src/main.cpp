#include <Arduino.h>
#include <Servo.h>

// =====================================================================
// SISTEMA AUTOMATIZADO - GARRA ROBÓTICA COM SEPARAÇÃO POR REGIÕES
// Integrado com Dashboard Django e leitura de QR Code
// =====================================================================

// ===== CONFIGURAÇÃO DAS 5 REGIÕES DO BRASIL =====
// Movimento de 1500 passos para posicionar cada defletor
const long PASSOS_REGIAO = 1500;

// ===== MOTORES DE PASSO =====
// Motor 1: pinos 30, 31, 32, 33 (Controle do defletor A)
const int IN1_M1 = 30, IN2_M1 = 31, IN3_M1 = 32, IN4_M1 = 33;

// Motor 3: pinos 26, 27, 28, 29 (Controle do defletor B - lado oposto)
const int IN1_M3 = 26, IN2_M3 = 27, IN3_M3 = 28, IN4_M3 = 29;

const long STEPS_PER_REV = 2048;
const float RPM_TARGET = 15.0f;

// Sequência Half-Step para motores 28BYJ-48
const uint8_t HALFSTEP[8][4] = {
  {1,0,0,0}, {1,1,0,0}, {0,1,0,0}, {0,1,1,0},
  {0,0,1,0}, {0,0,1,1}, {0,0,0,1}, {1,0,0,1}
};

volatile int sidx_M1 = 0;
volatile int sidx_M3 = 0;

// ===== SERVOS =====
const int SERVO_GARRA = 3;
const int SERVO_BASE = 5;
const int SERVO_ANTEBRACO = 8;
const int SERVO_BRACO = 10;

Servo servoGarra;
Servo servoBase;
Servo servoAntebraco;
Servo servoBraco;

struct PosicaoServos {
  int garra = 120;
  int base = 90;
  int antebraco = 60;
  int braco = 120;
} posicoes;

// ===== ESTADO DO SISTEMA =====
enum EstadoSistema {
  AGUARDANDO,           // Esperando comando para iniciar
  PEGANDO_OBJETO,       // Garra pegando objeto
  AGUARDANDO_QR,        // Objeto na frente da câmera, aguardando leitura
  MOVENDO_DEFLETOR,     // Motor de passo movendo defletor
  SOLTANDO_OBJETO,      // Garra soltando objeto na esteira
  RETORNANDO_DEFLETOR,  // Defletor voltando à posição inicial
  VOLTANDO_POSICAO      // Garra voltando à posição inicial
};

EstadoSistema estadoAtual = AGUARDANDO;
String regiaoAtual = "";

// Controle de movimento para retorno automático
bool motor1_moveu = false;
bool motor3_moveu = false;
bool direcao_m1_cw = false;
bool direcao_m3_cw = false;

// ===== FUNÇÕES MOTORES DE PASSO =====
inline unsigned long usPerHalfStep(float rpm) {
  if (rpm < 0.1f) rpm = 0.1f;
  return (unsigned long)(60000000.0f / (STEPS_PER_REV * rpm));
}

inline void writeStep_M1(int i) {
  digitalWrite(IN1_M1, HALFSTEP[i][0]);
  digitalWrite(IN2_M1, HALFSTEP[i][1]);
  digitalWrite(IN3_M1, HALFSTEP[i][2]);
  digitalWrite(IN4_M1, HALFSTEP[i][3]);
}

inline void writeStep_M3(int i) {
  digitalWrite(IN1_M3, HALFSTEP[i][0]);
  digitalWrite(IN2_M3, HALFSTEP[i][1]);
  digitalWrite(IN3_M3, HALFSTEP[i][2]);
  digitalWrite(IN4_M3, HALFSTEP[i][3]);
}

inline void stepOnce_M1(bool cw, unsigned long dwell_us) {
  writeStep_M1(sidx_M1);
  sidx_M1 = cw ? ((sidx_M1 + 1) % 8) : ((sidx_M1 + 7) % 8);
  delayMicroseconds(dwell_us);
}

inline void stepOnce_M3(bool cw, unsigned long dwell_us) {
  writeStep_M3(sidx_M3);
  sidx_M3 = cw ? ((sidx_M3 + 1) % 8) : ((sidx_M3 + 7) % 8);
  delayMicroseconds(dwell_us);
}

void motorOff_M1() {
  digitalWrite(IN1_M1, LOW);
  digitalWrite(IN2_M1, LOW);
  digitalWrite(IN3_M1, LOW);
  digitalWrite(IN4_M1, LOW);
}

void motorOff_M3() {
  digitalWrite(IN1_M3, LOW);
  digitalWrite(IN2_M3, LOW);
  digitalWrite(IN3_M3, LOW);
  digitalWrite(IN4_M3, LOW);
}

void moverMotor1(long steps, bool cw, float rpm) {
  rpm = max(1.0f, rpm);
  const unsigned long usDelay = usPerHalfStep(rpm);
  
  for (long i = 0; i < steps; i++) {
    stepOnce_M1(cw, usDelay);
  }
  motorOff_M1();
  
  motor1_moveu = true;
  direcao_m1_cw = cw;
}

void moverMotor3(long steps, bool cw, float rpm) {
  rpm = max(1.0f, rpm);
  const unsigned long usDelay = usPerHalfStep(rpm);
  
  for (long i = 0; i < steps; i++) {
    stepOnce_M3(cw, usDelay);
  }
  motorOff_M3();
  
  motor3_moveu = true;
  direcao_m3_cw = cw;
}

// ===== FUNÇÕES DOS SERVOS =====
void move_servo_gradual(Servo &servo, int start, int end, int step_delay = 20) {
  int passo = (end > start) ? 1 : -1;
  for (int ang = start; ang != end; ang += passo) {
    servo.write(ang);
    delay(step_delay);
  }
  servo.write(end);
}

void calibracao_inicial() {
  Serial.println("CALIBRANDO...");
  
  for (int pos = 0; pos <= 90; pos += 2) {
    servoBase.write(pos);
    delay(50);
  }
  delay(300);
  
  for (int pos = 90; pos <= 120; pos += 2) {
    servoBraco.write(pos);
    delay(50);
  }
  delay(300);
  
  for (int pos = 90; pos >= 60; pos -= 2) {
    servoAntebraco.write(pos);
    delay(50);
  }
  delay(300);
  
  for (int pos = 100; pos <= 120; pos += 2) {
    servoGarra.write(pos);
    delay(50);
  }
  delay(500);
  
  posicoes.garra = 120;
  posicoes.base = 90;
  posicoes.antebraco = 60;
  posicoes.braco = 120;
  
  Serial.println("CALIBRADO");
}

void pegar_objeto() {
  Serial.println("PEGANDO...");
  estadoAtual = PEGANDO_OBJETO;
  
  // Abrir garra
  move_servo_gradual(servoGarra, posicoes.garra, 120, 20);
  posicoes.garra = 120;
  delay(200);
  
  // Mover base para posição do objeto
  move_servo_gradual(servoBase, posicoes.base, 180, 20);
  posicoes.base = 180;
  delay(300);
  
  // Descer para pegar
  move_servo_gradual(servoBraco, posicoes.braco, 15, 20);
  posicoes.braco = 15;
  delay(300);
  
  // Fechar garra (pegar objeto)
  move_servo_gradual(servoGarra, posicoes.garra, 140, 20);
  posicoes.garra = 140;
  delay(500);
  
  // Subir com objeto
  move_servo_gradual(servoBraco, posicoes.braco, 90, 20);
  posicoes.braco = 90;
  delay(300);
  
  move_servo_gradual(servoBraco, posicoes.braco, 120, 20);
  posicoes.braco = 120;
  
  // Mover para frente da câmera (posição central)
  move_servo_gradual(servoBase, posicoes.base, 90, 20);
  posicoes.base = 90;
  delay(300);
  
  estadoAtual = AGUARDANDO_QR;
  Serial.println("READY_FOR_QR");
}

// =====================================================================
// PROCESSAMENTO DAS 5 REGIÕES DO BRASIL
// =====================================================================
// Mapeamento de regiões para movimentos dos motores de passo:
//
// | REGIÃO        | MOTOR  | DIREÇÃO      | PASSOS |
// |---------------|--------|--------------|--------|
// | NORTE         | M1     | Horário (CW) | 1500   |
// | NORDESTE      | M3     | Horário (CW) | 1500   |
// | CENTRO-OESTE  | -      | Sem movimento| 0      |
// | SUDESTE       | M1     | Anti-hor(CCW)| 1500   |
// | SUL           | M3     | Anti-hor(CCW)| 1500   |
// =====================================================================

void moverDefletorParaRegiao(String regiao) {
  Serial.print("MOVENDO_DEFLETOR:");
  Serial.println(regiao);
  estadoAtual = MOVENDO_DEFLETOR;
  
  // Reset flags de movimento
  motor1_moveu = false;
  motor3_moveu = false;
  
  regiao.toLowerCase();
  regiao.trim();
  
  if (regiao == "norte") {
    // Motor 1 sentido horário
    Serial.println("REGIAO:NORTE - Motor1 CW 1500");
    moverMotor1(PASSOS_REGIAO, true, RPM_TARGET);
  }
  else if (regiao == "nordeste") {
    // Motor 3 sentido horário
    Serial.println("REGIAO:NORDESTE - Motor3 CW 1500");
    moverMotor3(PASSOS_REGIAO, true, RPM_TARGET);
  }
  else if (regiao == "centro-oeste" || regiao == "centro oeste" || regiao == "centrooeste") {
    // Nenhum movimento - objeto passa reto
    Serial.println("REGIAO:CENTRO-OESTE - Passagem direta");
  }
  else if (regiao == "sudeste") {
    // Motor 1 sentido anti-horário
    Serial.println("REGIAO:SUDESTE - Motor1 CCW 1500");
    moverMotor1(PASSOS_REGIAO, false, RPM_TARGET);
  }
  else if (regiao == "sul") {
    // Motor 3 sentido anti-horário
    Serial.println("REGIAO:SUL - Motor3 CCW 1500");
    moverMotor3(PASSOS_REGIAO, false, RPM_TARGET);
  }
  else {
    Serial.print("REGIAO_INVALIDA:");
    Serial.println(regiao);
  }
  
  Serial.println("DEFLETOR_POSICIONADO");
}

void soltar_objeto() {
  Serial.println("SOLTANDO...");
  estadoAtual = SOLTANDO_OBJETO;
  
  // Descer para soltar
  move_servo_gradual(servoBraco, posicoes.braco, 37, 20);
  posicoes.braco = 37;
  delay(300);
  
  // Abrir garra (soltar objeto)
  move_servo_gradual(servoGarra, posicoes.garra, 120, 20);
  posicoes.garra = 120;
  delay(300);
  
  // Subir
  move_servo_gradual(servoBraco, posicoes.braco, 80, 20);
  posicoes.braco = 80;
  
  Serial.println("OBJETO_SOLTO");
}

void retornarDefletor() {
  Serial.println("RETORNANDO_DEFLETOR...");
  estadoAtual = RETORNANDO_DEFLETOR;
  
  // Retorna motor 1 se moveu (inverte direção)
  if (motor1_moveu) {
    moverMotor1(PASSOS_REGIAO, !direcao_m1_cw, RPM_TARGET);
    motor1_moveu = false;
  }
  
  // Retorna motor 3 se moveu (inverte direção)
  if (motor3_moveu) {
    moverMotor3(PASSOS_REGIAO, !direcao_m3_cw, RPM_TARGET);
    motor3_moveu = false;
  }
  
  Serial.println("DEFLETOR_RETORNADO");
}

void voltar_posicao_inicial() {
  Serial.println("VOLTANDO...");
  estadoAtual = VOLTANDO_POSICAO;
  
  move_servo_gradual(servoGarra, posicoes.garra, 120, 40);
  posicoes.garra = 120;
  delay(200);
  
  move_servo_gradual(servoBase, posicoes.base, 90, 40);
  posicoes.base = 90;
  delay(200);
  
  move_servo_gradual(servoBraco, posicoes.braco, 120, 40);
  posicoes.braco = 120;
  delay(200);
  
  move_servo_gradual(servoAntebraco, posicoes.antebraco, 60, 40);
  posicoes.antebraco = 60;
  
  estadoAtual = AGUARDANDO;
  Serial.println("PRONTO");
}

// =====================================================================
// CICLO COMPLETO AUTOMÁTICO
// Fluxo: Defletor → Soltar → Retornar Defletor → Posição Inicial
// (Esteira controlada independentemente por outro sistema)
// =====================================================================
void ciclo_automatico(String regiao) {
  Serial.println("=== INICIANDO CICLO AUTOMATICO ===");
  Serial.print("REGIAO_DESTINO:");
  Serial.println(regiao);
  
  regiaoAtual = regiao;
  
  // 1. Mover defletor para a posição correta ANTES de soltar
  moverDefletorParaRegiao(regiao);
  delay(500);
  
  // 2. Soltar objeto
  soltar_objeto();
  delay(500);
  
  // 3. Retornar defletor à posição inicial
  retornarDefletor();
  delay(500);
  
  // 4. Voltar garra à posição inicial
  voltar_posicao_inicial();
  
  Serial.println("=== CICLO FINALIZADO ===");
  Serial.println("OK");
}

// ===== SETUP =====
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=====================================================");
  Serial.println("  SISTEMA AUTOMATIZADO - GARRA ROBOTICA");
  Serial.println("  Separacao de objetos por Regioes do Brasil");
  Serial.println("=====================================================");
  
  // Configura motores de passo
  pinMode(IN1_M1, OUTPUT);
  pinMode(IN2_M1, OUTPUT);
  pinMode(IN3_M1, OUTPUT);
  pinMode(IN4_M1, OUTPUT);
  motorOff_M1();
  
  pinMode(IN1_M3, OUTPUT);
  pinMode(IN2_M3, OUTPUT);
  pinMode(IN3_M3, OUTPUT);
  pinMode(IN4_M3, OUTPUT);
  motorOff_M3();
  
  // Configura servos
  servoGarra.attach(SERVO_GARRA);
  servoBase.attach(SERVO_BASE);
  servoAntebraco.attach(SERVO_ANTEBRACO);
  servoBraco.attach(SERVO_BRACO);
  
  Serial.println("\nComandos disponiveis:");
  Serial.println("  INICIAR        - Pega objeto e aguarda leitura do QR");
  Serial.println("  REGIAO:<nome>  - Processa regiao (norte/nordeste/centro-oeste/sudeste/sul)");
  Serial.println("  C              - Calibracao inicial");
  Serial.println("  STATUS         - Mostra estado atual do sistema");
  Serial.println("  PARAR          - Interrompe ciclo atual");
  Serial.println("  RESET          - Reset de emergencia");
  
  // Calibração inicial automática
  calibracao_inicial();
  
  Serial.println("\nSistema pronto para operacao!");
  Serial.println("READY");
}

// ===== LOOP PRINCIPAL =====
void loop() {
  // Indicador visual de atividade
  static unsigned long ultimoPisca = 0;
  if (millis() - ultimoPisca > 2000) {
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    ultimoPisca = millis();
  }
  
  // Processa comandos seriais
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    
    if (comando.length() > 0) {
      Serial.print(">>> CMD: ");
      Serial.println(comando);
      
      // INICIAR - Começa o ciclo pegando o objeto
      if (comando.equalsIgnoreCase("INICIAR")) {
        if (estadoAtual == AGUARDANDO) {
          pegar_objeto();
        } else {
          Serial.println("ERRO:CICLO_EM_ANDAMENTO");
        }
      }
      // REGIAO:<nome> - Recebido quando QR code é lido pelo frontend
      else if (comando.startsWith("REGIAO:") || comando.startsWith("regiao:")) {
        if (estadoAtual == AGUARDANDO_QR) {
          String regiao = comando.substring(7);
          regiao.trim();
          ciclo_automatico(regiao);
        } else {
          Serial.println("ERRO:NAO_AGUARDANDO_QR");
          Serial.print("ESTADO_ATUAL:");
          switch(estadoAtual) {
            case AGUARDANDO: Serial.println("AGUARDANDO"); break;
            case PEGANDO_OBJETO: Serial.println("PEGANDO_OBJETO"); break;
            case AGUARDANDO_QR: Serial.println("AGUARDANDO_QR"); break;
            case MOVENDO_DEFLETOR: Serial.println("MOVENDO_DEFLETOR"); break;
            case SOLTANDO_OBJETO: Serial.println("SOLTANDO_OBJETO"); break;
            case RETORNANDO_DEFLETOR: Serial.println("RETORNANDO_DEFLETOR"); break;
            case VOLTANDO_POSICAO: Serial.println("VOLTANDO_POSICAO"); break;
          }
        }
      }
      // Calibração manual
      else if (comando.equalsIgnoreCase("C") || comando.equalsIgnoreCase("CALIBRAR")) {
        calibracao_inicial();
        Serial.println("OK");
      }
      // Status do sistema
      else if (comando.equalsIgnoreCase("STATUS")) {
        Serial.print("ESTADO:");
        switch(estadoAtual) {
          case AGUARDANDO: Serial.println("AGUARDANDO"); break;
          case PEGANDO_OBJETO: Serial.println("PEGANDO_OBJETO"); break;
          case AGUARDANDO_QR: Serial.println("AGUARDANDO_QR"); break;
          case MOVENDO_DEFLETOR: Serial.println("MOVENDO_DEFLETOR"); break;
          case SOLTANDO_OBJETO: Serial.println("SOLTANDO_OBJETO"); break;
          case RETORNANDO_DEFLETOR: Serial.println("RETORNANDO_DEFLETOR"); break;
          case VOLTANDO_POSICAO: Serial.println("VOLTANDO_POSICAO"); break;
        }
        Serial.print("REGIAO_ATUAL:");
        Serial.println(regiaoAtual.length() > 0 ? regiaoAtual : "NENHUMA");
        Serial.println("OK");
      }
      // Reset de emergência
      else if (comando.equalsIgnoreCase("RESET")) {
        Serial.println("EXECUTANDO_RESET...");
        motorOff_M1();
        motorOff_M3();
        motor1_moveu = false;
        motor3_moveu = false;
        regiaoAtual = "";
        estadoAtual = AGUARDANDO;
        voltar_posicao_inicial();
        Serial.println("RESET_OK");
      }
      // PARAR - Interrompe o ciclo atual
      else if (comando.equalsIgnoreCase("PARAR") || comando.equalsIgnoreCase("STOP")) {
        Serial.println("INTERROMPENDO_CICLO...");
        motorOff_M1();
        motorOff_M3();
        motor1_moveu = false;
        motor3_moveu = false;
        regiaoAtual = "";
        estadoAtual = AGUARDANDO;
        Serial.println("CICLO_INTERROMPIDO");
        Serial.println("OK");
      }
      else {
        Serial.print("COMANDO_DESCONHECIDO:");
        Serial.println(comando);
      }
    }
  }
}
