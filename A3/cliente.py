import socket

if __name__ == "__main__":
    BUFF_SIZE = 16 # Bytes

    address = ('localhost', 5000)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(address)
    
    file_path = input("Ingrese la ruta de su archivo ")

    with open(file_path, 'r', encoding='utf-8') as f:
        msg = f.read()  
        msg_length = len(msg)
    
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