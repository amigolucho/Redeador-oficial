import socket
import SocketTCP

def parse_segment(seg):
    header = {}
    lines = seg.split('\n')
    print(lines)
    for line in lines:
        if ':' in line:
            print(line.split(":"))
            name, info = line.split(":")
            header[name] = info
    return header

if __name__ == "__main__":
    BUFF_SIZE = 16 # Bytes

    address = ('localhost', 5000)
    server_socketTCP = SocketTCP.SocketTCP()
    print("CHECK 1")
    server_socketTCP.bind(address)
    print("CHECK 2")
    connection_socketTCP, new_address = server_socketTCP.accept()
    print("CHECK 3")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 3000))
    print("Socket de servidor creado con exito")

    server_socket.listen(1)

    while True:
        msg = ""
        new_socket, new_socket_address = server_socket.accept()
        print("Aceptando nueva conexion, recibimos mensajes")
        print("Esperando el HEAD")
        head = new_socket.recv(37) #Tamaño del head entre 35 y 37
        print("HEAD\n", head.decode())
        info = parse_segment(head.decode())
        
        buffer = new_socket.recv(BUFF_SIZE) 

        while len(buffer) > 0: # mientras se reciba mensaje
            #print(buffer)
            #print(len(buffer))
            msg += buffer.decode()
            buffer = new_socket.recv(BUFF_SIZE) 

        print(f"Mensaje recibido con exito: {msg}, con un largo {len(msg)}") 
    
    print("Cerrando socket, chaooo")
    server_socket.close()






