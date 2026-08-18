from machine import Pin
import time
import random


class TM1940:
    def __init__(self, stb_pin, clk_pin, dio_pin):
        self._stb = Pin(stb_pin, Pin.OUT)
        self._clk = Pin(clk_pin, Pin.OUT)
        self._dio = Pin(dio_pin, Pin.OUT)

        self.digit = [0] * 8

        # Códigos de segmentos de los dígitos 0-9
        self.digitToSegment = [
            0x3F, 0x06, 0x5B, 0x4F, 0x66,
            0x6D, 0x7D, 0x07, 0x7F, 0x6F
        ]

        # Códigos de segmentos de las letras usadas en los mensajes
        self.segmentos = {
            "H": 0x76,
            "O": 0x3F,
            "L": 0x38,
            "A": 0x77,
            "G": 0x7D,
            "!": 0x86,
            "F": 0x31,
            "I": 0x06
        }

    def init(self):
        self.clearDisplay()
        self.setBrightness(7)
        mensaje_final = "GO!"

        # Cuenta atrás 3, 2, 1
        for i in range(3):
            self.sendData(i * 2, self.digitToSegment[3 - i])
            time.sleep_ms(1000)
            self.clearDisplay()
            time.sleep_ms(1000)

        self.tiempo_inicio_ms = time.ticks_ms()
        self.contador_iniciar_juego()

    def readKeys(self):
        # Comando 0x42: leer botones
        self._stb.off()
        self.sendByte(0x42)
        self._dio.init(Pin.IN)
        valor_teclas = 0

        for i in range(8):
            bit = self._dio.value()
            valor_teclas = (valor_teclas << 1) | bit
            self._clk.on()
            time.sleep_us(1)
            self._clk.off()
            time.sleep_us(1)

        self._dio.init(Pin.OUT)
        self._stb.on()
        return valor_teclas

    def contador_iniciar_juego(self):
        self.clearDisplay()
        self.setBrightness(7)
        mensaje_inicio = "GO!"

        # Espera aleatoria antes de soltar al jugador
        tiempo_aleatorio_ms = random.randint(0, 10000)
        print(tiempo_aleatorio_ms / 1000)

        tiempo_limite = self.tiempo_inicio_ms + tiempo_aleatorio_ms
        tiempo_actual_ms = time.ticks_ms()

        contador_pulsos = 0
        anterior_boton_pulsado = 0
        tiempo_ultimo_pulso = 0

        while tiempo_limite > tiempo_actual_ms:
            boton_pulsado_actual = self.readKeys()
            # Pulsación detectada (botón S1 = bit 128), con antirrebote de 50 ms
            if anterior_boton_pulsado == 0 and boton_pulsado_actual == 128:
                tiempo_actual_ms = time.ticks_ms()
                tiempo_desde_ultimo_pulso = time.ticks_diff(tiempo_actual_ms, tiempo_ultimo_pulso)

                if tiempo_desde_ultimo_pulso >= 50:
                    contador_pulsos = contador_pulsos + 1
                    print("Pulsado boton!, Contador pulsado: ", contador_pulsos, " veces")
                    tiempo_ultimo_pulso = tiempo_actual_ms
                    mensaje_perdida = "FAIL"
                    print("Presionado antes del go!, perdio")
                    for posicion_letra, letra in enumerate(mensaje_perdida):
                        self.sendData(posicion_letra * 2, self.segmentos[letra])

            anterior_boton_pulsado = boton_pulsado_actual
            tiempo_actual_ms = time.ticks_ms()

        # Muestra "GO!" al terminar la espera
        for posicion_letra, letra in enumerate(mensaje_inicio):
            self.sendData(posicion_letra * 2, self.segmentos[letra])

        tiempo_inicio_ms = time.ticks_ms()

        # Mide el tiempo de reacción del jugador
        while True:
            boton_actual = self.readKeys()
            if anterior_boton_pulsado == 0 and boton_actual == 128:
                tiempo_actual_ms = time.ticks_ms()
                tiempo_desde_ultimo_pulso = time.ticks_diff(tiempo_actual_ms, tiempo_ultimo_pulso)

                if tiempo_desde_ultimo_pulso >= 50:
                    contador_pulsos = contador_pulsos + 1
                    print(contador_pulsos)
                    tiempo_ultimo_pulso = tiempo_actual_ms

                    tiempo_reaccion_ms = time.ticks_diff(tiempo_actual_ms, tiempo_inicio_ms)

                    # Protección para que no desborde el display (8 dígitos)
                    if tiempo_reaccion_ms > 99999999:
                        tiempo_reaccion_ms = 99999999

                    tiempo_reaccion_str = str(tiempo_reaccion_ms)

                for posicion_letra, digito in enumerate(tiempo_reaccion_str):
                    self.sendData(posicion_letra * 2, self.digitToSegment[int(digito)])

        anterior_boton_pulsado = boton_pulsado_actual

    def clearDisplay(self):
        for i in range(8):
            self.displayDigit(i, 0x00)

    def setBrightness(self, brightness):
        if brightness > 7:
            brightness = 7
        if brightness < 0:
            brightness = 0
        # Comando 0x88: control de brillo
        self.sendCommand(0x88 | brightness)

    def displayDigit(self, position, data):
        if position < 0 or position >= 8:
            return
        self.digit[position] = data
        self.sendData(position << 1, self.digit[position])

    def sendCommand(self, command):
        self._stb.off()
        self.sendByte(command)
        self._stb.on()

    def sendData(self, address, data):
        # Comando 0x44: escribir datos; cada dígito ocupa 2 direcciones (0xC0 + dir)
        self.sendCommand(0x44)
        self._stb.off()
        self.sendByte(0xC0 | address)
        self.sendByte(data)
        self._stb.on()

    def sendByte(self, data):
        # Envía 8 bits por DIO, del menos significativo al más significativo
        for i in range(8):
            self._dio.value(data & 0x01)
            time.sleep_us(1)
            self._clk.on()
            time.sleep_us(1)
            self._clk.off()
            time.sleep_us(1)
            data >>= 1