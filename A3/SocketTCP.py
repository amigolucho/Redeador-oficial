import socket
import random
import time

# Variables globales
TIMEOUT = 2
UDP_BUFF_SIZE = 1024
MAX_TRIES = 15      # reintentos máximos por segmento (handshake y datos)

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

    def send(self, message):
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
            ack = SocketTCP.create_segment([1, 0, 0, seg[3] + len(seg[4]), ''])
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
            if seg[3] < self.seq:
                ack = SocketTCP.create_segment([1, 0, 0, seg[3] + len(seg[4]), ''])
                self.socketUDP.sendto(ack, ads)
                dbg("La respuesta no llegó y nos reenviaron el mensaje, se reenvía el ACK")

    def recv(self, buff_size):
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