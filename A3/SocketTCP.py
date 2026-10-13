import socket
import random

# Variables globales
BUFF_SIZE = 16
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

    '''
    Función que pasa segmentos TCP a un diccionario.
    '''
    @staticmethod
    def parse_segment(seg):
        header = {}
        lines = seg.split('\n')

        for line in lines:
            if ':' in line:
                name, info = line.split(":")
                header[name] = info

        return header

    '''
    Función que crea segmentos TCP a partir de un diccionario.
    '''
    @staticmethod
    def create_segment(header):
        seg = ""

        for key, value in header.items():
            seg += f"{key}:{value}\n"

        return seg.encode()

    '''
    Función que se encarga que este objeto escuche la dirección address
    '''
    def bind(self,  address):
        self.bind_address = address
        self.socketUDP.bind(address)

    '''
    Función que inicia la conexión entre objetos, a uno con la dirección 
    address. Implementa el lado del cliente edl 3-way handshake.
    '''
    def connect(self, address):
        self.seq = random.randint(0, 100)
        self.connect_address = address

        syn = f"--HEAD--\nACK:{0}\nSYN:{1}\nFIN:{0}\nseq:{self.seq}\n\r\n"
        #head_1 = SocketTCP.create_segment(syn)
        print("1 step: HEAD:\n",syn)

        while True:
            try:
                self.socketUDP.sendto(syn.encode(), address)
                self.socketUDP.settimeout(TIMEOUT)
                print("Enviando el 1WH")
                msg, from_address = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                seg = SocketTCP.parse_segment(msg.decode())
                print("Recibiendo el 2HW:\n", seg)

                if (seg["ACK"] and seg["SYN"] == 1) and (seg["seq"] == self.seq + 1):
                    self.seq += 2
                    ack = f"--HEAD--\nACK:{1}\nSYN:{0}\nFIN:{0}\nseq:{self.seq}\n\r\n"
                    #head_2 = SocketTCP.create_segment(syn)
                    print("3 step: HEAD:\n", ack)

                    self.socketUDP.sendto(ack.encode(), from_address)
                    self.socketUDP.settimeout(TIMEOUT)
                    print("3WH completado con éxito")
           
            except TimeoutError:
                #Timeout, se envìa de nuevo
                continue
        


    '''
    Función que espera una petición SYN. Implementa el lado del servidor del 
    3-way handshake. Si el handshake retorna exitosamente, retorna un objeto
    junto la dirección que esta escuhando.
    '''
    def accept(self):
        while True:
            try:
                #Cubre caso inicial
                self.socketUDP.settimeout(None)
                msg, client_address = self.socketUDP.recvfrom(UDP_BUFF_SIZE)
                seg = SocketTCP.parse_segment(msg.decode())
                print("Recibiendo el 1WH:\n", seg)
                if seg['SYN'] == '1':
                    print(type(seg['seq']))
                    self.seq = int3
                    (seg['seq']) + 1
                    syn_ack = f"--HEAD--\nACK:{1}\nSYN:{1}\nFIN:{0}\nseq:{self.seq}\n\r\n"
                    print("2 step: ", syn_ack)
                    self.socketUDP.sendto(syn_ack.encode(), client_address)

            except Exception:
                continue


    '''
    Función que maneja el Stop & Wait desde el lado del emisor.
    Divide el mensaje en trozos de tamaño máximo 16 bytes.
    '''
    def send(message):
        pass

    '''
    Función que maneja el Stop & Wait desde el lado del receptor.
    Recibe el largo del mensaje en bytes, y luego comienza a recibir los datos, 
    hasta que se hayan recibido min(message_length, buff_size)
    '''
    def recv(buff_size):
        pass