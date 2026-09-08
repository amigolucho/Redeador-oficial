import socket
import json
import sys

#Parte 1    
# Función que transforma un mensaje HTTP (en bytes) a una estructura de datos 
def parse_HTTP_message(http_message):
    # Trandformamos el mensaje de bytes a string
    http_message = http_message.decode()

    # Separamos BODY y HEAD
    #print(f"mensaje incial sin procesar {http_message}")
    head, body = http_message.split("\r\n\r\n", 1)
    
    # Dividimos el header en líneas
    header = head.split("\r\n")
    
    # Start line
    start_line = header[0].split(" ", 2)
    http = {}
    
    if start_line[0].startswith("HTTP/"):
        # Es una RESPONSE: HTTP/1.1 200 OK
        http["version"] = start_line[0]
        http["code"] = start_line[1]
        http["status"] = start_line[2]
    else:
        # Es un REQUEST: GET /path HTTP/1.1
        http["method"] = start_line[0]
        http["path"] = start_line[1]
        http["version"] = start_line[2]

    # Iteramos sobre las líneas restantes para obtener los encabezados
    for line in header[1:]:
        if line == "":
            break  # Fin de los encabezados
        header_key, header_value = line.split(": ", 1)
        http[header_key] = header_value

    if body:
        http["body"] = body

    return http

# Función que crea un mensaje HTTP (en bytes) a partir de una estructura de datos
def create_HTTP_message(message):
    # Construimos la línea de inicio
    if 'method' in message:
        request_line = f"{message['method']} {message['path']} {message['version']}\r\n"
    else:
        request_line = f"{message['version']} {message["code"]} {message["status"]}\r\n"

    # Construimos los encabezados
    headers = ""
    for key, value in message.items():
        if key not in ['method', 'path', 'version', 'body', 'status', 'code']:
            headers += f"{key}: {value}\r\n"
    
    # Combinamos la línea de inicio, los encabezados y el cuerpo
    http_message = request_line + headers + "\r\n" + message.get('body', '')
    
    return http_message.encode()  # Devolvemos el mensaje en bytes

# Funcion que solo obtiene los headers de un mensaje
def get_headers(message):
    head = parse_HTTP_message(message)
    head.pop("body", None)
    return head

# Funcion que se encarga de recibir todo el mensaje independiente del tamaño del buffer
def recive_full_message(socket, buff_size):
    end_seq = b'\r\n\r\n'

    # recibimos la primera parte del mensaje
    recv_message = socket.recv(buff_size)
    full_message = recv_message

    # ver si llego completo e ir iterando
    is_complete = end_seq in recv_message
    
    while not is_complete:
        recv_message = socket.recv(buff_size)
        full_message += recv_message
        is_complete = end_seq in recv_message
    
    headers = get_headers(full_message)
    if "method" in headers:
        return full_message

    # Ae busca el body
    cont_len = int(headers["Content-Length"])
    head_end = full_message.find(end_seq) + len(end_seq)
    body_received = len(full_message) - head_end
    rest = cont_len - body_received

    #sacamos todo el contenido de body que venga
    while rest > 0:
        recv_message = socket.recv(buff_size)
        full_message += recv_message

        rest -= len(recv_message)
    
    return full_message

if __name__ == "__main__":
    file_path = sys.argv[1]
    #mekivoque es al reves el server y client jij
    
    with open(file_path, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    USER = datos["nombre"]
    FORBIDDEN = datos["forbidden_words"]
    BLOCKED = datos["blocked"]
    
    buff_size = 1000
    server_socket_address = ('0.0.0.0', 8000)

    print('Creando socket con el cliente - Proxy')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # permite reutilizar el puerto inmediatamente si el script se reinicia
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind(server_socket_address)
    server_socket.listen(30)

    print('... Esperando clientes para reenviar al server')
    while True:
        new_socket, new_socket_address = server_socket.accept()
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # recibimos el mensaje crudo (bytes) que envía el navegador
        recv_message = recive_full_message(new_socket, buff_size)
        
        # Obtenemos el Host y el puesto si es que hay
        parsed_msg = parse_HTTP_message(recv_message)
        print(f"PETICION RECIBIDA: {parsed_msg.get('path')}")
        parsed_msg["X-ElQuePregunta"] = USER
        host_header = parsed_msg["Host"]

        if ":" in host_header:
            host, port = host_header.split(":")
            port  = int(port)
        else:
            host = host_header
            port = 80 #pueto tipico de protocolo http

        # Si piden la imagen del 403, la respondemos directo desde acá
        if parsed_msg["path"].endswith("/images.jpeg"):
            with open("images.jpeg", "rb") as f:
                img_bytes = f.read()
            response_line = f"{parsed_msg['version']} 200 OK\r\n"
            headers = f"Content-Type: image/jpeg\r\nContent-Length: {len(img_bytes)}\r\n\r\n"
            new_socket.send(response_line.encode() + headers.encode() + img_bytes)
            new_socket.close()
            continue
                
        # Engloba los casos donde no se pone el http
        blocked = False
        for url in BLOCKED:
            if url in parsed_msg["path"]:
                print("Intentando acceder a un host blockeado")
                cat_html =  "<!DOCTYPE html><html><head><title>403 Forbidden</title></head><body><h1>403 Forbidden</h1><p>El dominio solicitado esta bloqueado por el proxy.</p><img src=\"/images.jpeg\" alt=\"Acceso bloqueado\"></body></html>"
                error_response = {'status':'error', 'code':'403', 
                    'version':parsed_msg['version'], 'body':cat_html,
                    'Content-Type': 'text/html'}
                a = create_HTTP_message(error_response)
                print(a, "ola")
                new_socket.send(a)
                new_socket.close()
                
                blocked = True
                break
        if blocked:
            continue
            
        print(f"El cliente se quiere conectar al host {host_header}")

        #reenviar el mensaje al real server     
        client_socket.connect((host,port))
        client_socket.send(create_HTTP_message(parsed_msg))
        print("mensaje reenviado al server, esperando respuesta...")

        #esperamos respuesta del server y reenviamos al cliente con las palabras reemplazadas
        response = recive_full_message(client_socket, buff_size)
        #print("respuesta del servidor",response)
        parsed_response = parse_HTTP_message(response)
        #print(f"lens {len(parsed_response["body"])} y delr clen {parsed_response["Content-Length"]}")
        for word, replace in FORBIDDEN.items():
            if word in parsed_response["body"]:
                parsed_response["body"] = parsed_response["body"].replace(word, replace)

        parsed_response["Content-Length"] = str(len(parsed_response["body"].encode()))
        #print("respuesta filtrada", create_HTTP_message(parsed_response))
        new_socket.send(create_HTTP_message(parsed_response))

        # cerramos la conexión
        new_socket.close()
        print(f"conexión con {new_socket_address} ha sido cerrada")
