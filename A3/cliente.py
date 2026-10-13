import socket
import random
import SocketTCP

if __name__ == "__main__":
    BUFF_SIZE = 16 # Bytes

    address = ('localhost', 5000)
    client_socketTCP = SocketTCP.SocketTCP()
    print("CHECK 1")
    client_socketTCP.connect(address)
    print("CHECK 2")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(address)

    
    file_path = input("Ingrese la ruta de su archivo ")

    with open(file_path, 'r', encoding='utf-8') as f:
        msg = f.read()  
        msg_length = len(msg)
    #acá enviar el header?

    ack = input("Mensaje ACK? (1 o 0): ")
    syn = input("Mensaje SYN? (1 o 0): ")
    fin = input("Mensaje FIN? (1 o 0): ")
    seq = random.randint(0, 100)
    print("Tu número de seq es ", seq)

    head = f"--HEAD--\nACK:{ack}\nSYN:{syn}\nFIN:{fin}\nseq:{seq}\n\r\n"
    print("Enviando HEAD:\n", head)
    client_socket.send(head.encode())
    
    i = 0 # index   
    while msg_length > BUFF_SIZE:
        buffer = msg[i: i + BUFF_SIZE]

        client_socket.send(buffer.encode())
        msg_length -= BUFF_SIZE
        i += BUFF_SIZE
        print(f"Enviando paquete nro {i + 1}")

    # Mandamos el ùltimo buffer, y en caso de ser pequeño, el ùnico
    client_socket.send(msg[-msg_length:].encode())

    print(file_path)
    print("Mensaje en bytes ", msg.encode(), " y su largo ", len(msg))

    print("Cerrando el socket, chaooo")
    client_socket.close()