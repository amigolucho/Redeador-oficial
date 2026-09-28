import socket

if __name__ == "__main__":
    BUFF_SIZE = 16 # Bytes

    address = ('localhost', 5000)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(address)
    print("Socket de servidor creado con exito")

    server_socket.listen(1)

    while True:
        msg = ""
        new_socket, new_socket_address = server_socket.accept()
        print("Aceptando nueva conexion, recibimos mensajes")
        
        buffer = new_socket.recv(BUFF_SIZE) 

        while len(buffer) > 0: # mientras se reciba mensaje
            #print(buffer)
            #print(len(buffer))
            msg += buffer.decode()
            buffer = new_socket.recv(BUFF_SIZE) 

        print(f"Mensaje recibido con exito: {msg}, con un largo {len(msg)}") 
    
    print("Cerrando socket, chaooo")
    server_socket.close()






