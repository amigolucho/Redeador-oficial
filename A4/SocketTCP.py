import socket
import random
import time
from CongestionControl import CongestionControl
from slidingWindowCC import SlidingWindowCC

# Variables globales
TIMEOUT = 2
UDP_BUFF_SIZE = 1024
MAX_TRIES = 15      # reintentos máximos por segmento (handshake y datos)
MSS = 8             # tamaño máximo (bytes) de los datos de un segmento en Go-Back-N
GBN_WINDOW = 8      # ventana fija (en segmentos) de Go-Back-N sin control de congestión

# Modo debug: True imprime lo que hace el código (incluyendo cómo maneja las pérdidas),
# False no imprime nada. Las líneas de recuperación llevan el prefijo "[PERDIDA]".
DEBUG = True


def dbg(*args):
    if DEBUG:
        print(*args)


class SocketTCP:
    def __init__(self):
        # Variables
        self.socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socketUDP.settimeout(TIMEOUT)

        self.bind_address = None
        self.connect_address = None
        self.seq = None

        self.missing_data = 0
        self.stack_data = ""
        self.msg_len = None
        self.BUFF_SIZE = 16

        self.pending_segment = None
        self.seen_syns = set()

        # --- Tarea 4: Go-Back-N y control de congestión ---
        self.MSS = MSS
        self.congestion_control_on = True       # se cambia con set_congestion_control()
        self.congestion_controler = None        # se crea en cada send_using_go_back_n
        self.number_of_sent_segments = 0        # segmentos enviados en el último send go_back_n

    """
    Suponiendo una estructura del tipo:

    --HEAD--\n
    ACK:(1 o 0)\n
    SYN:(1 o 0)\n
    FIN:(1 o 0)\n
    seq:(info)\n\r\n
    Área de información (16 bytes)

    Donde la elección de 1 o 0 es para saber que mensajes esta enviando

    Numeración: SYN y FIN no consumen número. Cada segmento de datos (incluido el que
    informa el largo) avanza el seq en la cantidad de bytes que lleva, y el ACK de un
    segmento lleva seq + largo de sus datos.
    """

    @staticmethod
    def parse_segment(seg):
        '''
        Función que pasa segmentos TCP a una lista del tipo [ACK, SYN, FIN, seq, data].
        '''
        header = []
        head, data = seg.split("\r\n", 1)  
        lines = head.split('\n')

        for line in lines:
            if ':' in line:
                _, info = line.split(":")
                header.append(int(info))
        header.append(data)

        return header

    @staticmethod
    def create_segment(info):
        '''
        Función que crea segmentos TCP a partir de una lista del tipo [ACK, SYN, FIN, seq, data].
        data debe venir en bytes.
        '''
        if isinstance(info[4], str):
            info[4] = info[4].encode()
        header = f"--HEAD--\nACK:{info[0]}\nSYN:{info[1]}\nFIN:{info[2]}\nseq:{info[3]}\n\r\n"

        return header.encode() + info[4]

    def bind(self,  address):
        '''
        Función que se encarga que este objeto escuche la dirección address
        '''
        self.bind_address = address
        self.socketUDP.bind(address)

    def connect(self, address):
        '''
        Función que inicia la conexión entre objetos, a uno con la dirección
        address. Implementa el lado del cliente del 3-way handshake.
        '''
        x = random.randint(0, 100)
        self.seq = x
        self.bind_address = address

        syn = SocketTCP.create_segment([0, 1, 0, x, 'no info'])
        self.socketUDP.settimeout(TIMEOUT)

        while True:
            self.socketUDP.sendto(syn, address)
            dbg("Enviando el 1WH: ", syn)
            try:
                msg, from_address = self.socketUDP.recvfrom(UDP_BUFF_SIZE) # esta direccion es la del nuevo socket q se creo
            except TimeoutError:
                #Timeout, se envìa de nuevo
                dbg("[PERDIDA] Timeout esperando el 2WH, se reenvía el SYN")
                continue
            # SUperó el timeout
            seg = SocketTCP.parse_segment(msg.decode())
            dbg("Recibiendo el 2HW:\n", seg)
            if (seg[0] and seg[1] == 1) and (seg[3] == x + 1):
                #self.socketUDP.settimeout(None)
                self.connect_address = from_address
                self.seq += 2
                ack = SocketTCP.create_segment([1, 0, 0, self.seq, 'no info'])
                dbg("Enviando el 3WH HEAD:\n", ack)
                self.socketUDP.sendto(ack, self.connect_address)
                dbg("3WH completado con éxito")
                return

    def accept(self):
        '''
        Función que espera una petición SYN. Implementa el lado del servidor del
        3-way handshake. Si el handshake retorna exitosamente, retorna un objeto
        junto la dirección que esta escuhando.
        '''
        while True:
            self.socketUDP.settimeout(None)
            try:
                msg, client_address = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
            except (ConnectionRefusedError, ConnectionResetError):
                continue
            seg = SocketTCP.parse_segment(msg.decode())
            dbg("Recibiendo el 1WH:\n", seg)
            if not seg[1] or seg[0]:
                continue

            key = (client_address, seg[3])
            if key in self.seen_syns:           # SYN repetido de una conexión ya atendida
                dbg("SYN repetido, se ignora")
                continue
            self.seen_syns.add(key)

            x = seg[3]
            new_socketTCP = SocketTCP()
            new_socketTCP.bind(('localhost', 0))
            new_address = new_socketTCP.socketUDP.getsockname()
            new_socketTCP.connect_address = client_address
            new_socketTCP.socketUDP.settimeout(TIMEOUT)
            new_socketTCP.seq = x + 2           # seq con que el cliente enviará su primer segmento
            dbg("Nueva dirección asignada: ", new_address)
            syn_ack = SocketTCP.create_segment([1, 1, 0, x + 1, 'no info'])
            dbg("Enviando el 2WH:\n", syn_ack)

            established = False
            while True:
                new_socketTCP.socketUDP.sendto(syn_ack, client_address)
                try:
                    msg, client_address = new_socketTCP.socketUDP.recvfrom(UDP_BUFF_SIZE)

                except TimeoutError:
                        dbg("[PERDIDA] Timeout esperando el 3WH, se reenvía el SYN+ACK")
                        continue
                seg = SocketTCP.parse_segment(msg.decode())
                if seg[0] and seg[3] == new_socketTCP.seq + 1:
                    continue
                if not seg[0]:
                    # Caso borde: se perdió el último ACK y el cliente ya empezó a enviar datos.
                    # Ese segmento sirve de ACK implícito y queda pendiente para recv().
                    dbg("Llegó DATA en vez del ACK final: se toma como ACK implícito")
                    new_socketTCP.pending_segment = seg
                established = True
                break
            
            if not established:
                dbg("El cliente no completó el handshake, se descarta")
                new_socketTCP.socketUDP.close()
                continue

            dbg("3WH completado")
            return new_socketTCP, new_address

    def send_using_stop_and_wait(self, message):
        '''
        Función que maneja el Stop & Wait desde el lado del emisor.
        Divide el mensaje en trozos de tamaño máximo 16 bytes.
        Recibe el mensaje ya encodeado
        '''
        self.socketUDP.settimeout(TIMEOUT)
        # El primer segmento informa el largo; luego van los trozos de 16 bytes.
        chunks = [f"msg_len = {len(message)}".encode()]
        chunks += [message[i: i + self.BUFF_SIZE] for i in range(0, len(message), self.BUFF_SIZE)]
        dbg(f"Enviando un mensaje de largo {len(message)} en {len(chunks)} segmentos (incluyendo el largo)")

        for index, data in enumerate(chunks):
            expected = self.seq + len(data)             # seq del ACK que lo confirma
            segment = SocketTCP.create_segment([0, 0, 0, self.seq, data])
            dbg(f"Enviando segmento {index + 1}/{len(chunks)} a {self.connect_address}: {data}")
            while True:
                self.socketUDP.sendto(segment, self.connect_address)
                try:
                    raw, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                except TimeoutError:
                    dbg("[PERDIDA] Timeout esperando el ACK, se reenvía el segmento")
                    continue
                seg = SocketTCP.parse_segment(raw.decode())
                dbg("Verificando la respuesta: ", seg)
                if ads == self.connect_address and seg[0] and not seg[1] and not seg[2] \
                        and seg[3] == expected:
                    break
                dbg("Timeout, se reenvía el segmento")

            self.seq = expected

        dbg("Mensaje enviado con éxito")

    def _ack_duplicate(self, seg, ads):
        '''
        Si seg es un segmento de datos ya recibido (su ACK se perdió), reenvía su ACK.
        Retorna True si era un duplicado.
        '''
        if seg[0] or seg[1] or seg[2]:
            return False
        if seg[3] < self.seq:
            # CAMBIO T4: se reenvía el ACK acumulativo (self.seq). Con Stop & Wait es el mismo
            # valor que antes (el duplicado es siempre el último segmento); con Go-Back-N
            # confirma todo lo recibido de una vez.
            ack = SocketTCP.create_segment([1, 0, 0, self.seq, ''])
            self.socketUDP.sendto(ack, ads)
            return True
        return False
#función auxiliar para ahorrar código
    def _next_data(self):
        '''
        Retorna los datos (str) del próximo segmento de datos en orden y envía su ACK.
        Ignora todo lo que no sea un segmento de datos y re-confirma los duplicados.
        '''
        while True:
            if self.pending_segment is not None:
                seg, ads = self.pending_segment, self.connect_address
                self.pending_segment = None
            else:
                try:
                    msg, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                except TimeoutError:
                    continue
                seg = SocketTCP.parse_segment(msg.decode())
            dbg(f"Recibiendo mensaje: {seg} desde {ads}. seq actual: {self.seq}")
            if seg[0] or seg[1] or seg[2]:      # debería ser solo un segmento de datos
                continue
            if seg[3] == self.seq:              # el segmento esperado
                self.seq += len(seg[4])
                ack = SocketTCP.create_segment([1, 0, 0, self.seq, ''])
                self.socketUDP.sendto(ack, ads)
                return seg[4]
            if seg[0] or seg[1] or seg[2]:
                    dbg("Se envia un mensaje con ACK SYN o FIN, lo cual esta mal lol")
                    continue
            # CAMBIO T4: duplicado (seq < esperado) o fuera de orden (seq > esperado, solo ocurre
            # en Go-Back-N): se descarta y se reenvía el ACK acumulativo (self.seq).
            ack = SocketTCP.create_segment([1, 0, 0, self.seq, ''])
            self.socketUDP.sendto(ack, ads)
            dbg(f"[PERDIDA] Segmento duplicado o fuera de orden (seq={seg[3]}, esperado={self.seq}), se reenvía el ACK {self.seq}")

    def recv_using_stop_and_wait(self, buff_size):
        '''
        Función que maneja el Stop & Wait desde el lado del receptor.
        Recibe el largo del mensaje en bytes, y luego comienza a recibir los datos,
        hasta que se hayan recibido min(message_length, buff_size)
        '''
        self.socketUDP.settimeout(None)

        if self.missing_data == 0:              # llamada nueva: primero llega el largo
            _, msg_len = self._next_data().split('=')
            self.msg_len = int(msg_len)
            self.missing_data = self.msg_len
            dbg("Recibiendo el largo: ", msg_len)

        target = min(self.missing_data, buff_size)

        while len(self.stack_data) < target:
            self.stack_data += self._next_data()

        buff = self.stack_data[:target]
        self.stack_data = self.stack_data[target:]
        self.missing_data -= target

        return buff.encode()

    # ------------------------------------------------------------------
    # Tarea 4: Go-Back-N con control de congestión
    # ------------------------------------------------------------------
    def send(self, message, mode="stop_and_wait"):
        '''
        Envía message (bytes) usando el ARQ indicado en mode: "stop_and_wait" o "go_back_n".
        '''
        if mode == "stop_and_wait":
            self.send_using_stop_and_wait(message)
        elif mode == "go_back_n":
            self.send_using_go_back_n(message)
        else:
            raise ValueError(f"mode inválido: {mode}")

    def recv(self, buff_size, mode="stop_and_wait"):
        '''
        Recibe hasta buff_size bytes usando el ARQ indicado en mode.
        '''
        if mode == "stop_and_wait":
            return self.recv_using_stop_and_wait(buff_size)
        elif mode == "go_back_n":
            return self.recv_using_go_back_n(buff_size)
        raise ValueError(f"mode inválido: {mode}")

    def set_congestion_control(self, on):
        '''
        Activa (True) o desactiva (False) el control de congestión en send_using_go_back_n.
        Desactivado, la ventana queda fija en GBN_WINDOW segmentos.
        '''
        self.congestion_control_on = bool(on)

    def _send_length_segment(self, length):
        '''
        Envía de forma confiable (Stop & Wait) el segmento que informa el largo del mensaje.
        '''
        data = f"msg_len = {length}".encode()
        expected = self.seq + len(data)
        segment = SocketTCP.create_segment([0, 0, 0, self.seq, data])
        while True:
            self.socketUDP.sendto(segment, self.connect_address)
            self.number_of_sent_segments += 1
            try:
                raw, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
            except TimeoutError:
                dbg("[PERDIDA] Timeout esperando el ACK del largo, se reenvía")
                continue
            seg = SocketTCP.parse_segment(raw.decode())
            if ads == self.connect_address and seg[0] and not seg[1] and not seg[2] \
                    and seg[3] == expected:
                break
        self.seq = expected

    def _send_data_segment(self, seq, data):
        segment = SocketTCP.create_segment([0, 0, 0, seq, data])
        self.socketUDP.sendto(segment, self.connect_address)
        self.number_of_sent_segments += 1

    def _cc_debug(self, evento):
        '''Debug de la ventana de congestión.'''
        cc = self.congestion_controler
        dbg(f"[CC] {evento}: cwnd={cc.get_cwnd():.1f} B, ventana={cc.get_MSS_in_cwnd()} seg, "
            f"estado={cc.current_state}, ssthresh={cc.get_ssthresh()}")

    def send_using_go_back_n(self, message):
        '''
        Función que maneja Go-Back-N desde el lado del emisor. Divide el mensaje en trozos de
        MSS bytes. Con congestion_control_on la ventana la define CongestionControl; si no,
        es fija (GBN_WINDOW segmentos).
        '''
        self.number_of_sent_segments = 0
        t_inicio = time.time()
        self.socketUDP.settimeout(TIMEOUT)

        # El largo se informa primero (igual que en Stop & Wait) y de forma confiable.
        self._send_length_segment(len(message))
        data_list = [message[i: i + self.MSS] for i in range(0, len(message), self.MSS)]
        if not data_list:
            return

        cc_on = self.congestion_control_on
        self.congestion_controler = CongestionControl(self.MSS)
        cc = self.congestion_controler
        window_size = cc.get_MSS_in_cwnd() if cc_on else GBN_WINDOW
        if cc_on:
            self._cc_debug("inicio")
        data_window = SlidingWindowCC(window_size, data_list, self.seq)

        end_seq = self.seq + len(message)
        base = 0                    # índice del primer segmento sin confirmar
        next_to_send = 0            # índice del próximo segmento a enviar
        timer_start = time.time()   # el timer es el del segmento más antiguo sin confirmar

        while base < len(data_list):
            # 1) enviar los segmentos de la ventana que aún no se envían
            while next_to_send < base + window_size and next_to_send < len(data_list):
                slot = next_to_send - base
                self._send_data_segment(data_window.get_sequence_number(slot), data_window.get_data(slot))
                if next_to_send == base:
                    timer_start = time.time()
                next_to_send += 1

            # 2) esperar un ACK hasta que se cumpla el timeout del segmento base
            remaining = TIMEOUT - (time.time() - timer_start)
            try:
                if remaining <= 0:
                    raise TimeoutError
                self.socketUDP.settimeout(remaining)
                raw, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
            except TimeoutError:
                dbg(f"[PERDIDA] Timeout en seq={data_window.get_sequence_number(0)}: se vuelve a enviar desde la base")
                if cc_on:
                    cc.event_timeout()
                    window_size = cc.get_MSS_in_cwnd()
                    data_window.update_window_size(window_size)
                    self._cc_debug("timeout")
                next_to_send = base
                timer_start = time.time()
                continue

            seg = SocketTCP.parse_segment(raw.decode())
            if ads != self.connect_address or not seg[0] or seg[1] or seg[2]:
                continue
            ack_seq = seg[3]

            # 3) mover la ventana según el ACK. Se repite por si el ACK cae más allá de la
            # ventana actual (caso borde cuando la ventana se achicó tras un timeout).
            while base < len(data_list):
                steps = 0
                for i in range(window_size):
                    d = data_window.get_data(i)
                    if d is None or ack_seq < data_window.get_sequence_number(i) + len(d):
                        break
                    steps += 1
                if steps == 0:
                    break

                new_window_size = window_size
                if cc_on:
                    for _ in range(steps):
                        cc.event_ack_received()
                    new_window_size = cc.get_MSS_in_cwnd()

                data_window.move_window(steps)
                base += steps
                next_to_send = max(next_to_send, base)
                timer_start = time.time()

                if new_window_size != window_size:
                    window_size = new_window_size
                    data_window.update_window_size(window_size)
                if cc_on:
                    self._cc_debug(f"ACK {ack_seq}")

        self.seq = end_seq
        self.socketUDP.settimeout(TIMEOUT)
        dbg(f"[GBN] Mensaje enviado con éxito: {self.number_of_sent_segments} segmentos enviados, "
            f"{time.time() - t_inicio:.3f} s")

    def recv_using_go_back_n(self, buff_size):
        '''
        Función que maneja Go-Back-N desde el lado del receptor. El receptor no cambia respecto
        a Stop & Wait: acepta solo el segmento esperado y ante uno duplicado o fuera de orden
        descarta y reenvía el ACK acumulativo (ver _next_data).
        '''
        return self.recv_using_stop_and_wait(buff_size)

    def close(self):
        '''
        Función que implementa el cierre de conección desde el lado del "Host A"
        '''
        self.socketUDP.settimeout(TIMEOUT)
        MAX_TIMEOUTS = 3
        FIN = SocketTCP.create_segment([0, 0, 1, self.seq, ''])
        dbg(f"Cerrando conexión con direcciòn: {self.connect_address}, msg {FIN}")
        dbg(f"Esperando el FIN+ACK")
        msg = [-1, -1, -1, -1, -1]
        while not(msg[0] and msg[2] and (not msg[1]) and (msg[3] == self.seq + 1)) and MAX_TIMEOUTS > 0:
            self.socketUDP.sendto(FIN, self.connect_address)
            try: 
                raw, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                msg = SocketTCP.parse_segment(raw.decode())
                dbg(f"Mensaje FIN recibido: {FIN}")
            except TimeoutError:
                MAX_TIMEOUTS -= 1
                dbg(f"[PERDIDA] Timeout esperando el FIN+ACK, se reenvía el FIN (quedan {MAX_TIMEOUTS})")
                continue
        if not MAX_TIMEOUTS: # Paso por 3 timeouts
            dbg("3 Timeouts y no se recibió FIN+ACK, asumiendo cierre del HOST B")
            self.socketUDP.close()
            dbg("Conexión cerrada por parte del HOST A")
            return

        dbg("El mensaje FIN es válido")
        dbg("Confirmando el cierre de conexión por parte del HOST A")
        self.seq += 2
        ACK = SocketTCP.create_segment([1, 0, 0, self.seq, ''])
        for i in range(3):                      # el último ACK se envía 3 veces
            dbg(f"Enviando el último ACK ({i + 1}/3)")
            self.socketUDP.sendto(ACK, ads)
            time.sleep(TIMEOUT)                 # se espera un timeout entre cada envío
        self.socketUDP.close()
        dbg("Conexión cerrada por parte del HOST A")

        dbg("Chaooo")
        
    def recv_close(self):
        '''
        Función que implementa el cierre de conección desde el lado del "Host B"
        '''
        MAX_TIMEOUTS = 3
        while True:
            raw, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
            msg = SocketTCP.parse_segment(raw.decode())
            if self._ack_duplicate(msg, ads):
                dbg(f"[PERDIDA] Dato duplicado (seq={msg[3]}) antes del FIN: se reenvía su ACK")
                continue
            break
        dbg(f"Iniciando cierre de conexión {msg} y seq: {self.seq}")
        if msg[2] and (not msg[0] and not msg[1]) and (msg[3] == self.seq):
            self.seq = msg[3] + 1
            self.socketUDP.settimeout(TIMEOUT)
            dbg(f"Cerrando conexión por parte de HOST B: {msg}, conexion: {ads}")
            FINACK = SocketTCP.create_segment([1, 0, 1, self.seq, ''])
            self.socketUDP.sendto(FINACK, ads)
            dbg("Esperando el ultimo ACK para cerrar la conexión")
            while not (msg[0] and (msg[3] == self.seq + 1)) and MAX_TIMEOUTS > 0:
                dbg(f"DEBG: {msg} MAX {MAX_TIMEOUTS} seq: {self.seq}")
                try:
                    raw, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                    msg = SocketTCP.parse_segment(raw.decode())
                    dbg(f"mensaje ACK recibido: {msg}")
                except TimeoutError:
                    MAX_TIMEOUTS -= 1
                    dbg(f"[PERDIDA] Timeout esperando el último ACK (quedan {MAX_TIMEOUTS})")
                    continue
            if not MAX_TIMEOUTS:
                dbg("No se recibió el último ACK, se asume conexión cerrada")
                self.socketUDP.close()
                return
            self.socketUDP.close()
            dbg("Conexión cerrada por parte del HOST B")

        else:
            dbg("EL HOST B NO RECIBIO EL FIN CORRECTAMENTE")

        dbg("CHaooOAo")