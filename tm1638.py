# Importa la clase Pin, necesaria para controlar los pines (GPIO) de la placa.
from machine import Pin
# Importa las funciones de tiempo (pausas, `ticks_ms`, `ticks_diff`, etc.).
import time
# Importa las funciones para generar números aleatorios.
import random


class TM1940:
    # Constructor: se invoca al crear un objeto TM1940(...) y configura los pines y datos iniciales.
    def __init__(self, stb_pin, clk_pin, dio_pin):
        # Configura el pin STB (selección de chip / "strobe") como salida.
        self._stb = Pin(stb_pin, Pin.OUT)
        # Configura el pin CLK (reloj de la comunicación) como salida.
        self._clk = Pin(clk_pin, Pin.OUT)
        # Configura el pin DIO (línea de datos) como salida (después cambiará a entrada para leer botones).
        self._dio = Pin(dio_pin, Pin.OUT)

        # Lista que guarda el código de segmentos de cada uno de los 8 dígitos del display.
        self.digit = [0] * 8

        # Tabla que convierte los números del 0 al 9 en el código hexadecimal de sus 7 segmentos.
        self.digitToSegment = [
            0x3F, 0x06, 0x5B, 0x4F, 0x66,
            0x6D, 0x7D, 0x07, 0x7F, 0x6F
        ]

        # Diccionario que convierte letras (para mensajes como "GO!" o "FAIL") en códigos de segmentos.
        self.segmentos = {
            "H": 0x76,  # código de segmentos de la letra H
            "O": 0x3F,  # código de segmentos de la letra O
            "L": 0x38,  # código de segmentos de la letra L
            "A": 0x77,  # código de segmentos de la letra A
            "G": 0x7D,  # código de segmentos de la letra G
            "!": 0x86,  # código de segmentos del signo !
            "F": 0x31,  # código de segmentos de la letra F
            "I": 0x06   # código de segmentos de la letra I
        }

    # Inicializa la partida: hace una cuenta atrás (3-2-1) y después arranca la primera parte del juego.
    def init(self):
        # Borra todo lo que haya en los 8 dígitos del display.
        self.clearDisplay()
        # Pone el brillo del display al máximo (nivel 7, de 0 a 7).
        self.setBrightness(7)
        # Mensaje final que se mostrará al terminar la primera parte del juego.
        mensaje_final = "GO!"

        # Bucle que se repite 3 veces (i = 0, 1, 2) para la cuenta atrás 3, 2, 1.
        for i in range(3):
            # Selecciona el número a mostrar: 3, 2, 1 (3 - i).
            codigo_segmento = self.digitToSegment[3 - i]
            # Cada dígito ocupa 2 direcciones de memoria, así que se avanza de 2 en 2.
            direccion = i * 2
            # Envía al display el código de segmentos en la dirección calculada.
            self.sendData(direccion, codigo_segmento)
            # Espera 1000 ms (1 segundo) con el número encendido.
            time.sleep_ms(1000)
            # Borra la pantalla.
            self.clearDisplay()
            # Espera otro segundo con la pantalla vacía.
            time.sleep_ms(1000)
        # Guarda el tiempo (en milisegundos) en que acabó la cuenta atrás; será el inicio del juego.
        self.tiempo_inicio_ms = time.ticks_ms()
        # Llama al método que implementa la primera parte del juego (contar pulsaciones).
        self.contador_iniciar_juego()

    # Lee el estado de los 8 botones y lo devuelve como un número de 8 bits.
    def readKeys(self):
        # Pone el pin STB en nivel bajo para iniciar la comunicación con el chip.
        self._stb.off()
        # Envía el comando 0x42: "leer teclas".
        self.sendByte(0x42)
        # Cambia el pin DIO a modo entrada para poder recibir los datos de los botones.
        self._dio.init(Pin.IN)
        # Variable que irá acumulando los bits de los 8 botones.
        valor_teclas = 0

        # Recorre los 8 botones (un bit por botón).
        for i in range(8):
            # Lee el valor (0 o 1) del botón actual en el pin DIO.
            bit = self._dio.value()
            # Desplaza el valor acumulado un bit a la izquierda y mete dentro el bit leído.
            valor_teclas = (valor_teclas << 1) | bit

            # Pone el reloj en alto (inicio del pulso de reloj).
            self._clk.on()
            # Pequeña espera de 1 microsegundo para estabilizar la comunicación.
            time.sleep_us(1)
            # Pone el reloj en bajo (fin del pulso de reloj).
            self._clk.off()
            # Otra espera de 1 microsegundo.
            time.sleep_us(1)

        # Una vez terminada la lectura, vuelve a poner DIO como salida.
        self._dio.init(Pin.OUT)
        # Pone STB en nivel alto para finalizar la comunicación.
        self._stb.on()
        # Devuelve el número con los 8 bits de los botones.
        return valor_teclas

    # Primera parte del juego: mientras dura una espera aleatoria, el jugador pulsa el botón y cuenta.
    def contador_iniciar_juego(self):
        # Borra la pantalla para empezar limpia.
        self.clearDisplay()
        # Fija el brillo máximo.
        self.setBrightness(7)
        # Mensaje que se mostrará al terminar esta ronda.
        mensaje_inicio = "GO!"

        # Genera un retardo aleatorio entre 0 y 10000 ms (la espera no siempre es igual).
        tiempo_aleatorio_ms = random.randint(0, 10000)
        # Muestra en la consola cuántos segundos de espera aleatoria habrá.
        print(tiempo_aleatorio_ms / 1000)

        # Calcula el tiempo (en ms) en el que debe terminar la espera aleatoria.
        tiempo_limite = self.tiempo_inicio_ms + tiempo_aleatorio_ms
        # Lee el reloj interno para saber el instante actual en ms.
        tiempo_actual_ms = time.ticks_ms()

        # Contador que sumará las pulsaciones del botón.
        contador_pulsos = 0
        # Guarda el valor de las teclas leído en la iteración anterior (para detectar el botón recién pulsado).
        anterior_boton_pulsado = 0
        # Momento (en ms) de la última pulsación detectada.
        tiempo_ultimo_pulso = 0

        # Bucle que se repite mientras la espera aleatoria no haya terminado.
        while tiempo_limite > tiempo_actual_ms:
            # Lee los botones en este instante.
            boton_pulsado_actual = self.readKeys()
            # Detecta una pulsación: antes no estaba pulsado (0) y ahora sí (128 = bit del botón S1).
            if anterior_boton_pulsado == 0 and boton_pulsado_actual == 128:
                # Actualiza el tiempo actual.
                tiempo_actual_ms = time.ticks_ms()
                # Calcula el tiempo transcurrido desde la última pulsación.
                tiempo_desde_ultimo_pulso = time.ticks_diff(tiempo_actual_ms, tiempo_ultimo_pulso)

                # Antirrebote: ignora pulsaciones que lleguen a menos de 50 ms de la anterior.
                if tiempo_desde_ultimo_pulso >= 50:
                    # Suma 1 al contador de pulsaciones.
                    contador_pulsos = contador_pulsos + 1
                    # Imprime el contador en la consola.
                    print("Pulsado boton!, Contador pulsado: ", contador_pulsos, " veces")
                    # Actualiza el momento de la última pulsación.
                    tiempo_ultimo_pulso = tiempo_actual_ms
                    # Mensaje que se muestra en el display (el jugador "falla" al pulsar).
                    mensaje_perdida = "FAIL"
                    print("Presionado antes del go!, perdio")
                    # Recorre cada letra del mensaje junto con su posición.
                    for posicion_letra, letra in enumerate(mensaje_perdida):
                        # Obtiene el código de segmentos de la letra.
                        codigo_segmento = self.segmentos[letra]
                        # Calcula la dirección del dígito (cada letra ocupa 2 direcciones).
                        direccion = posicion_letra * 2
                        # Muestra la letra en el display.
                        self.sendData(direccion, codigo_segmento)

            # Guarda el valor leído como "anterior" para la próxima iteración del bucle.
            anterior_boton_pulsado = boton_pulsado_actual
            # Actualiza el tiempo actual antes de repetir el bucle.
            tiempo_actual_ms = time.ticks_ms()

        # Cuando la espera aleatoria termina, recorre el mensaje final letra por letra.
        for posicion_letra, letra in enumerate(mensaje_inicio):
            # Obtiene el código de segmentos de la letra.
            codigo_segmento = self.segmentos[letra]
            # Calcula la dirección del dígito (2 direcciones por dígito).
            direccion = posicion_letra * 2
            # Muestra la letra en el display.
            self.sendData(direccion, codigo_segmento)

        # Guarda el tiempo (en ms) de inicio de la segunda parte (medir el tiempo de reacción).
        tiempo_inicio_ms = time.ticks_ms()

        # Bucle infinito: segunda parte del juego, se mide el tiempo de reacción tras ver "GO!".
        while True:
            # Lee los botones.
            boton_actual = self.readKeys()
            #si ya habia pulsado y intenta pulsador no pasa nada
            if anterior_boton_pulsado == 0 and boton_actual == 128:
                # Actualiza el momento actual.
                tiempo_actual_ms = time.ticks_ms()
                # Calcula el tiempo desde la última pulsación (para el antirrebote).
                tiempo_desde_ultimo_pulso = time.ticks_diff(tiempo_actual_ms, tiempo_ultimo_pulso)

                # Solo cuenta la pulsación si pasaron al menos 50 ms desde la anterior.
                if tiempo_desde_ultimo_pulso >= 50:
                    # Incrementa el contador de pulsaciones.
                    contador_pulsos = contador_pulsos + 1
                    # Imprime el contador en la consola.
                    print(contador_pulsos)
                    # Actualiza el tiempo de la última pulsación.
                    tiempo_ultimo_pulso = tiempo_actual_ms

                    # Calcula el tiempo de reacción: tiempo transcurrido desde que apareció "GO!".
                    tiempo_reaccion_ms = time.ticks_diff(tiempo_actual_ms, tiempo_inicio_ms)

                    #protecciobn para que el tiempo no salga de display
                    if tiempo_reaccion_ms > 99999999:
                        tiempo_reaccion_ms=  99999999  

                    # Convierte ese número en texto (string) para poder mostrarlo dígito a dígito.
                    tiempo_reaccion_str = str(tiempo_reaccion_ms)


                # Recorre cada dígito del tiempo de reacción y lo muestra en el display.
                for posicion_letra, digito in enumerate(tiempo_reaccion_str):
                    # Obtiene el código de segmentos del dígito (convierte el carácter a número).
                    codigo_segmento = self.digitToSegment[int(digito)]
                    # Calcula la dirección del dígito en el display.
                    direccion = posicion_letra * 2
                    # Muestra el dígito en el display.
                    self.sendData(direccion, codigo_segmento)

        # OJO: esta línea nunca se ejecuta porque el bucle infinito anterior no termina nunca.
        anterior_boton_pulsado = boton_pulsado_actual

    # Borra todos los dígitos del display.
    def clearDisplay(self):
        # Recorre las 8 posiciones del display.
        for i in range(8):
            # Envía el código 0x00 (todo apagado) a la posición i.
            self.displayDigit(i, 0x00)

    # Ajusta el brillo del display usando el comando base 0x88.
    def setBrightness(self, brightness):
        # Limita el brillo al máximo permitido (7).
        if brightness > 7:
            brightness = 7

        # Limita el brillo al mínimo permitido (0).
        if brightness < 0:
            brightness = 0

        # Construye el comando de brillo: 0x88 + nivel de brillo (0-7).
        command = 0x88 | brightness
        # Envía el comando construido al chip.
        self.sendCommand(command)

    # Muestra un dato (código de segmentos) en una posición concreta del display.
    def displayDigit(self, position, data):
        # Si la posición no es válida (fuera de 0-7), no hace nada.
        if position < 0 or position >= 8:
            return

        # Guarda el dato en la lista interna.
        self.digit[position] = data
        # Envía el dato al chip en la dirección real (posición * 2: cada dígito ocupa 2 direcciones).
        self.sendData(position << 1, self.digit[position])

    # Envía un comando al chip manteniendo STB en bajo durante todo el envío.
    def sendCommand(self, command):
        # STB en nivel bajo: comienza la comunicación.
        self._stb.off()
        # Envía el byte del comando.
        self.sendByte(command)
        # STB en nivel alto: termina la comunicación con el comando.
        self._stb.on()

    # Envía datos (código de segmentos) a una dirección concreta del chip.
    def sendData(self, address, data):
        # Envía primero el comando 0x44: "escribir datos en el registro".
        self.sendCommand(0x44)

        # STB en nivel bajo para empezar el envío de los datos.
        self._stb.off()

        # Envía la dirección de memoria donde se escribirá (0xC0 | dirección).
        self.sendByte(0xC0 | address)
        # Envía el dato (código de segmentos) que se va a escribir.
        self.sendByte(data)

        # STB en nivel alto: fin de la comunicación de datos.
        self._stb.on()

    # Envía un byte (8 bits) bit a bit por la línea DIO usando pulsos de reloj.
    def sendByte(self, data):
        # Envía los 8 bits del byte, del menos significativo al más significativo.
        for i in range(8):
            # Coloca en DIO el bit menos significativo del dato (0 o 1).
            self._dio.value(data & 0x01)

            # Pequeña espera para que el valor se estabilice en la línea DIO.
            time.sleep_us(1)

            # Pulso de reloj: CLK en alto indica que el dato en DIO es válido.
            self._clk.on()
            # Espera de 1 microsegundo.
            time.sleep_us(1)

            # Termina el pulso: CLK en bajo.
            self._clk.off()
            # Espera de 1 microsegundo.
            time.sleep_us(1)

            # Desplaza el dato un bit a la derecha para enviar el siguiente bit en la próxima vuelta.
            data >>= 1
