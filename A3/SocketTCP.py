import socket
import time
import random

# Variables globales
TIMEOUT = 2
UDP_BUFF_SIZE = 1024
# Simular pèrdida
LOSS = 0.2

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
    
    """
    Suponiendo una estruct8ura del tipo:

    --HEAD--\n
    ACK:(1 o 0)\n
    SYN:(1 o 0)\n
    FIN:(1 o 0)\n
    seq:(info)\n\r\n
    Área de información (16 bytes)

    Donde la elección de 1 o 0 es para saber que mensajes esta enviando
    """

    @staticmethod
    def parse_segment(seg):
        '''
        Función que pasa segmentos TCP a una lista del tipo [ACK, SYN, FIN, seq, data].
        '''
        header = []
        head, data = seg.split("\r\n")
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
        address. Implementa el lado del cliente edl 3-way handshake.
        '''
        self.seq = random.randint(0, 100)
        self.bind_address = address

        syn = SocketTCP.create_segment([0, 1, 0, self.seq, 'no info'])
        self.socketUDP.settimeout(TIMEOUT)

        while True:
            self.socketUDP.sendto(syn, address)
            print("Enviando el 1WH: ", syn)
            try:
                msg, from_address = self.socketUDP.recvfrom(UDP_BUFF_SIZE) # esta direccion es la del nuevo socket q se creo
            except TimeoutError:
                #Timeout, se envìa de nuevo
                continue
            # SUperó el timeout
            seg = SocketTCP.parse_segment(msg.decode())
            print("Recibiendo el 2HW:\n", seg)
            if (seg[0] and seg[1] == 1) and (seg[3] == self.seq + 1):
                #self.socketUDP.settimeout(None)
                self.connect_address = from_address
                self.seq += 2
                ack = SocketTCP.create_segment([1, 0, 0, self.seq, 'no info'])
                print("Enviando el 3WH HEAD:\n", ack)
                self.socketUDP.sendto(ack, self.connect_address)
                print("3WH completado con éxito")
                break

    def accept(self):
        '''
        Función que espera una petición SYN. Implementa el lado del servidor del 
        3-way handshake. Si el handshake retorna exitosamente, retorna un objeto
        junto la dirección que esta escuhando.
        '''
        while True:
            #Cubre caso inicial
            self.socketUDP.settimeout(None)
            msg, client_address = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
            seg = SocketTCP.parse_segment(msg.decode())
            print("Recibiendo el 1WH:\n", seg)
            if not seg[1] or seg[0]:
                continue
            #ver si el syn esta repetido

            self.seq = seg[3] + 1
            new_socketTCP = SocketTCP()
            new_socketTCP.bind(('localhost', 0))
            new_address = new_socketTCP.socketUDP.getsockname()
            new_socketTCP.connect_address = client_address
            new_socketTCP.socketUDP.settimeout(TIMEOUT)
            new_socketTCP.seq = self.seq + 1
            print("Nueva dirección asignada: ", new_address)
            syn_ack = SocketTCP.create_segment([1, 1, 0, self.seq, 'no info'])
            print("Enviando el 2WH:\n", syn_ack)
            

            while True:
                new_socketTCP.socketUDP.sendto(syn_ack, client_address)
                try:
                    msg, client_address = new_socketTCP.socketUDP.recvfrom(UDP_BUFF_SIZE)
                    seg = SocketTCP.parse_segment(msg.decode())
                    if seg[0] and seg[3] == self.seq + 1:
                        break#ver el caso borde

                except TimeoutError:
                    continue

            print("Recibiendo el 3WH:\n", seg)
            return new_socketTCP, new_address

    def send(self, message):
        '''
        Función que maneja el Stop & Wait desde el lado del emisor.
        Divide el mensaje en trozos de tamaño máximo 16 bytes. 
        Recibe el mensaje ya encodeado
        '''
        msg_len = len(message)
        first_time = 1 # booleano para saber si aun no envia el largo
        self.socketUDP.settimeout(TIMEOUT)

        i = 0
        index = 0
        ACK = 0
        while msg_len > self.BUFF_SIZE or first_time:
            if first_time:
                buffer = f"msg_len = {len(message)}" # Tamaño en bytes   
                HEAD = SocketTCP.create_segment([0, 0, 0, self.seq, buffer])
                print(f"Enviando un mensaje de largo: {len(buffer)} a {self.connect_address}")
                self.socketUDP.sendto(HEAD, self.connect_address) 
                
            else:
                buffer = message[i: i + self.BUFF_SIZE]
                HEAD = SocketTCP.create_segment([0, 0, 0, self.seq, buffer])
                print("Mensaje de esta tanda: \n", HEAD)
                self.socketUDP.sendto(HEAD, self.connect_address)

            try:
                print("Esperando la respuesta, sino reenviar ", self.connect_address)
                raw, _ = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                msg = SocketTCP.parse_segment(raw.decode())
                print("Verificando la respuesta: ", msg)
            except TimeoutError:
                continue
            ACK = msg[0]
            if (not ACK) and (self.seq != msg[3] - len(buffer)):
                print("El mensaje recibido tenia un ACK o seq inválidos: ", msg)
                continue
            self.seq = msg[3]# Deberia haber recibido self.seq + len(msg)
            if first_time:
                print("Como es la respuesta del largo, no restamos nada")
                first_time = 0
                continue
            
            msg_len -= self.BUFF_SIZE
            i += self.BUFF_SIZE
            print(f"Enviando paquete nro {index + 1}")
            index += 1

        # Mandamos el último buffer, y en caso de ser pequeño, el ùnico
        HEAD = SocketTCP.create_segment([0, 0, 0, self.seq, message[-msg_len:]])
        print("Enviando el ultimo o unico chunk: ", message[-msg_len:])
        ACK = 0
        seq = -10
        print("Esperando la última respuesta, para terminar")
        while (not ACK):# En este punto msg_len deberìa ser pequeño
            self.socketUDP.sendto(HEAD, self.connect_address)
            print("Enviando a: ", self.connect_address)
            try:
                raw, _ = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                msg = SocketTCP.parse_segment(raw.decode())
                print(f"Mensaje recibido {msg}")
                seq = msg[3]
                if self.seq + msg_len != seq:
                    continue
            except TimeoutError:
                continue
            ACK = msg[0]
            self.seq += msg_len
        print("Mensaje enviado con éxito")
        
    def recv(self, buff_size):
        '''
        Función que maneja el Stop & Wait desde el lado del receptor.
        Recibe el largo del mensaje en bytes, y luego comienza a recibir los datos, 
        hasta que se hayan recibido min(message_length, buff_size)
        '''
        self.socketUDP.settimeout(None)

        if self.missing_data == 0:                 
            msg, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
            HEAD = SocketTCP.parse_segment(msg.decode())
            _, msg_len = HEAD[4].split('=')
            self.msg_len = int(msg_len)
            self.missing_data = self.msg_len
            print(f"mm aber :{HEAD[4]}: fss")
            self.seq += len(HEAD[4])
            ack = SocketTCP.create_segment([1, 0, 0, self.seq, ''])
            self.socketUDP.sendto(ack, ads)
            print("Recibiendo el largo: ", msg_len)

        target = min(self.missing_data, buff_size)  
        MAX = 2
        while len(self.stack_data) < target:
            MAX -= 1
            #if MAX < 0:
            #    raise ValueError("Este es el mensaje de error")
                
            msg, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
            seg = SocketTCP.parse_segment(msg.decode())
            print(f"Recibiendo mensaje: {seg} desde {ads}. seq actual: {self.seq}")
            # Acà no deberia haber timeout
            if seg[0] or seg[1] or seg[2]: # Deberia ser solo la secuencia
                continue
            if self.seq == seg[3] + len(seg[4]):
                print("La respuesta no llego y nos reenviaron el mensaje, simplemente reenviamos lo mismo sin modificar\n", seg)
                print(f"ADS: {ads}, connect: {self.connect_address}")
                ACK = SocketTCP.create_segment([1, 0, 0, self.seq, ''])
                self.socketUDP.sendto(ACK, ads)
                continue
            print(f"El mensaje era correcto {ads} y {self.connect_address}")
            self.stack_data += seg[4]
            self.seq += len(seg[4])               
            ACK = SocketTCP.create_segment([1, 0, 0, self.seq, ''])
            self.socketUDP.sendto(ACK, ads)

        buff = self.stack_data[:target]
        self.stack_data = self.stack_data[target:]
        self.missing_data -= target                 

        return buff.encode()

