import socket
import random

# Variables globales
TIMEOUT = 5
UDP_BUFF_SIZE = 1024

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
        lines = seg.split('\n')

        for line in lines:
            if ':' in line:
                name, info = line.split(":")
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
        print("1 step: HEAD:\n",syn.decode())

        while True:
            try:
                self.socketUDP.settimeout(TIMEOUT)
                self.socketUDP.sendto(syn, address)
                print("Enviando el 1WH")
                msg, from_address = self.socketUDP.recvfrom(UDP_BUFF_SIZE) # esta direccion es la del nuevo socket q se creo
                self.connect_address = from_address
                self.socketUDP.settimeout(None)
                seg = SocketTCP.parse_segment(msg.decode())
                print("Recibiendo el 2HW:\n", seg)

                if (seg[0] and seg[1] == 1) and (seg[3] == self.seq + 1):
                    self.seq += 2
                    ack = SocketTCP.create_segment([1, 0, 0, self.seq, 'no info'])
                    print("Enviando el 3WH HEAD:\n", ack)

                    self.socketUDP.sendto(ack, self.bind_address)
                    print("3WH completado con éxito")
                break
           
            except TimeoutError:
                #Timeout, se envìa de nuevo
                continue

    def accept(self):
        '''
        Función que espera una petición SYN. Implementa el lado del servidor del 
        3-way handshake. Si el handshake retorna exitosamente, retorna un objeto
        junto la dirección que esta escuhando.
        '''
        while True:
            try:
                #Cubre caso inicial
                self.socketUDP.settimeout(None)
                msg, client_address = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                seg = SocketTCP.parse_segment(msg.decode())
                print("Recibiendo el 1WH:\n", seg)
                if seg[1]:
                    self.seq = seg[3] + 1
                    syn_ack = SocketTCP.create_segment([1, 1, 0, self.seq, 'no info'])
                    print("2 step: ", syn_ack)

                    new_socketTCP = SocketTCP()
                    new_socketTCP.seq = self.seq
                    new_socketTCP.bind(('localhost', 0))
                    new_address = new_socketTCP.socketUDP.getsockname()
                    new_socketTCP.connect_address = new_address
                    print("Nueva dirección asignada: ", new_address)
                    print("Enviando el 2WH:\n", seg)
                    new_socketTCP.socketUDP.sendto(syn_ack, client_address)
                #----------
                msg, client_address = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                seg = SocketTCP.parse_segment(msg.decode())
                print("Recibiendo el 3WH:\n", seg)

                return new_socketTCP, new_address

            except TimeoutError:
                continue

    def send(self, message):
        '''
        Función que maneja el Stop & Wait desde el lado del emisor.
        Divide el mensaje en trozos de tamaño máximo 16 bytes. 
        Recibe el mensaje ya encodeado
        '''
        msg_len = len(message)
        msg = f"mesagge_lenght = {len(message)}" # Tamaño en bytes    
        HEAD = SocketTCP.create_segment([0, 0, 0, self.seq, msg])
        print("Enviando un mensaje de largo: ", msg_len)
        self.socketUDP.sendto(HEAD, self.connect_address) 
        print("Enviando el mensaje por tandas de 16 bytes")

        i = 0
        index = 0
        ACK = 1
        while msg_len > self.BUFF_SIZE and ACK:
            try:
                ACK = 0
                buffer = message[i: i + self.BUFF_SIZE]

                HEAD = SocketTCP.create_segment([0, 0, 0, self.seq, buffer])
                print("Mensaje de esta tanda: \n", HEAD)
                self.socketUDP.settimeout(TIMEOUT)
                self.socketUDP.sendto(HEAD, self.connect_address)
                
                print("Esperando la respuesta, sino reenviar ", self.connect_address)
                msg, _ = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                print("Verificando la respuesta: ", msg)
                seg = SocketTCP.parse_segment(msg.decode())
                ACK = seg[0]

                msg_len -= self.BUFF_SIZE
                i += self.BUFF_SIZE
                print(f"Enviando paquete nro {index + 1}")
                index += 1
                # Recibe la respuesta

            except TimeoutError:
                ACK = 1
                continue

        # Mandamos el último buffer, y en caso de ser pequeño, el ùnico
        HEAD = SocketTCP.create_segment([0, 0, 0, self.seq, message[-msg_len:]])
        print("Enviando el ultimo o unico chunk: ", message[-msg_len:])
        self.socketUDP.sendto(HEAD, self.connect_address)
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

        target = min(self.missing_data, buff_size)  

        while len(self.stack_data) < target:
            msg, ads = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
            seg = SocketTCP.parse_segment(msg.decode())
            self.stack_data += seg[4]
            self.seq += len(seg[4])               
            ACK = SocketTCP.create_segment([1, 0, 0, self.seq, ''])
            self.socketUDP.sendto(ACK, ads)

        buff = self.stack_data[:target]
        self.stack_data = self.stack_data[target:]
        self.missing_data -= target                 

        return buff.encode()