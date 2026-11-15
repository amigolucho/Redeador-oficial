import socket
import sys

RR = {} # Diccionario para gestionar el round rubin contando cuantas veces se a accedido a una ruta. 
_debug_ = False
HEADER_SIZE = 16  # Tamaño del header en bytes (string) sin contar el mensaje

def debug_print(message):
    """Prints debug messages if debugging is enabled."""
    if _debug_:
        print(f"[DEBUG] {message}")

def parse_packet(IP_BRACKETS: bytes) -> dict:
    """
    Extrae los headers y datos del paquete.
    """
    try:
        ip, port, ttl, id, offset, size, flag, msg = IP_BRACKETS.decode().split(";", 7) 
    except ValueError:
        debug_print(f"Error al parsear el paquete: {IP_BRACKETS.decode()}")
        return None
    
    return {
        "ip": ip,
        "port": int(port),
        "ttl": int(ttl),
        "id": int(id),
        "offset": int(offset),
        "size": int(size),
        "flag": int(flag),
        "msg": msg,
    }

def create_packet(structured_data: dict) -> bytes:
    """
    Crea un paquete a partir de la estructura.
    """
    ip = structured_data["ip"]
    port = structured_data["port"]
    ttl = structured_data['ttl']
    id = structured_data['id']
    offset = structured_data['offset']
    size = structured_data['size']
    flag = structured_data['flag']
    msg = structured_data["msg"]

    packet = f"{ip};{port};{ttl};{id};{offset};{size};{flag};{msg}".encode() # ejemplo: "127.0.0.1;8881;10;1;0;1024;0;Hello, world!"
    return packet

def forward_packet(final: tuple[str, int], msg: str, send: tuple[str, int], s: socket.socket = None) -> None:
    """
    Función que permitirá enviar un paquete a la dirección de destino final, pasando por el siguiente salto.
    """
    if s is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    packet = create_packet({"ip": final[0], "port": final[1], "msg": msg})
    s.sendto(packet, (send[0], send[1]))
    debug_print(f"Paquete enviado a {send[0]}:{send[1]} con contenido: {packet.decode()}")

def check_routes(routes_files_name: str, destinarion_address: tuple[str, int]) -> tuple[str, int]:
    """
    Función que revisa en orden la tabla de rutas para indicar la adirección del siguiente salto.
    """
    ip, port = destinarion_address
    candidate_routes = []

    with open(routes_files_name, "r") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # Ignorar líneas vacías o comentarios
            parts = line.split(" ")  # el formato de la línea es:  RED I_port F_port next_IP next_PORT MTU, por ej 127.0.0.1/24 8881 8882 127.0.0.1 8882 50

            if len(parts) != 6:
                debug_print(f"Línea de ruta inválida: {line}")
                continue  # Ignorar líneas mal formateadas
            dest_ip, initial_port, dest_port, next_hop_ip, next_hop_port, MTU = parts

            if (int(initial_port) <= port <= int(dest_port)): #dest_ip == destinarion_address[0] and ver si comparar la ip o no ya q es solo uno
                key = (initial_port, dest_port)
                debug_print(f"Ruta encontrada para {destinarion_address}: siguiente salto {next_hop_ip}:{next_hop_port}")   
                candidate_routes.append((next_hop_ip, int(next_hop_port), int(MTU)))
    
    if candidate_routes:
        # Seleccionar la ruta con el siguiente salto más cercano (implementación del algoritmo Round Robin)
        i = RR.get(key, 0) % len(candidate_routes)
        RR[key] = (i + 1) % len(candidate_routes) 
        debug_print(f"key: {key}, i: {i}, RR[key]: {RR[key]}, candidate_routes: {candidate_routes}")
        return (candidate_routes[i])

    debug_print(f"No se encontró ruta para {destinarion_address}")  
    return None

def fragment_IP_packet(IP_packet: bytes, MTU: int) -> list[dict]:
    """
    Función que fragmenta un paquete IP en varios paquetes según el MTU.
    """
    msg_len = MTU - HEADER_SIZE # Tamaño permitido del mensaje en bytes después de restar el tamaño del header
    packet = parse_packet(IP_packet)
    msg = packet["msg"]
    
    if len(msg) <= msg_len:
        debug_print(f"No es necesario fragmentar el paquete: {packet}\n")
        return [parse_packet(IP_packet)]  # No es necesario fragmentar
    # Hay que fragmentar el mensaje
    fragmented_packets = []
    half_size = len(msg) // 2 
    # Resolvemos recursivamente como si fuera un árbol
    left_packet = create_packet({**packet, 'msg': msg[:half_size], 'size': half_size, 'flag': 1}) # Fragmento izquierdo
    right_packet = create_packet({**packet, 'msg': msg[half_size:], 'offset': packet['offset'] + half_size, 'size':len(msg)-half_size}) # Fragmento derecho
    debug_print(f"Fragmentando paquete: {packet}\n en dos fragmentos: {left_packet} y {right_packet}\n")
    
    fragmented_packets += fragment_IP_packet(left_packet, MTU) + fragment_IP_packet(right_packet, MTU) 
    return fragmented_packets

def reassemble_IP_packet(fragment_list: list[dict]) -> bytes:
    """
    Función que reensambla los fragmentos de un paquete IP en un solo paquete.
    """
    if len(fragment_list) == 1:
        if fragment_list[0]['flag'] == fragment_list[0]['offset'] == 0:
            debug_print(f"Paquete sin fragmentar recibido: {fragment_list[0]['msg']}")
            return create_packet(fragment_list[0])
        debug_print(f"Paquete inválido recibido: {fragment_list[0]}")
        return None

    # Ordenar los fragmentos por offset
    fragment_list.sort(key=lambda x: x['offset'])

    if fragment_list[0]['offset'] != 0 or fragment_list[-1]['flag'] != 0:
        debug_print(f"Fragmentos inválidos: primer offset {fragment_list[0]['offset']}, último flag {fragment_list[-1]['flag']}")
        return None

    for anterior, actual in zip(fragment_list, fragment_list[1:]):
        if anterior['offset'] + anterior['size'] != actual['offset']:
            debug_print(f"Falta un fragmento entre offset {anterior['offset']} y {actual['offset']}")
            return None

    # Concatenar los mensajes de los fragmentos
    reassembled_msg = ''.join(
        fragment['msg'] for fragment in fragment_list
    )
    # Crear un nuevo paquete con el mensaje reensamblado y los headers del primer fragmento
    first_fragment = fragment_list[0]
    reassembled_packet = create_packet({
        **first_fragment,
        "offset": 0,
        "size": len(reassembled_msg),
        "flag": 0,
        "msg": reassembled_msg,
    })

    debug_print(f"Paquete reensamblado: {reassembled_packet}")
    return reassembled_packet

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python router.py <host_IP> <port> <path_tables>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    path_table = sys.argv[3]
    debug_print(f"Router IP: {host}, Router port: {port}, Router table: {path_table}")
    resamble_fragments = {}

    #IP_packet_v1 = b"127.0.0.1;8881;Hello, world!"
    #parsed_IP_packet = parse_packet(IP_packet_v1)
    #IP_packet_v2 = create_packet(parsed_IP_packet)
    #debug_print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))

    # Creando socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        debug_print(f"Router escuchando en {host}:{port}")

        while True:
            data, addr = s.recvfrom(1024)
            debug_print(f"Recibiendo paquete desde {addr}: {data.decode()}")
            packet = parse_packet(data)

            if packet['ttl'] is not None and packet['ttl'] <= 0:
                print(f"Se recibió paquete [{packet['msg']}] con TTL 0")
                continue
            if packet["ip"] == host and packet["port"] == port:
                resamble_fragments.setdefault(packet['id'], []).append(packet)
                print(f"Paquete destinado a este router. Tiene el siguiente mensaje: \n {packet['msg']}")
                reassembled_packet = reassemble_IP_packet(resamble_fragments.get(packet['id'], [])) 
                if reassembled_packet is not None:
                    resamble_fragments.pop(packet['id'], None) # Limpiar los fragmentos almacenados para este paquete
                    print(f"Packete reensamblado correctamente: {parse_packet(reassembled_packet)}")
            else:
                next_hop = check_routes(path_table, (packet['ip'], packet['port'])) # next_hop_ip, next_hop_port, mtu
                if next_hop is not None:
                    next_hop_ip, next_hop_port, MTU = next_hop
                    packet['ttl'] -= 1  # Decrementar el TTL antes de reenviar
                    #forward_packet((packet['ip'], packet['port']), packet['msg'], next_hop, s)
                    fragmented_packets = fragment_IP_packet(create_packet(packet), MTU)
                    for fp in fragmented_packets:
                        s.sendto(create_packet(fp), (next_hop_ip, next_hop_port))
                        debug_print(f"Paquete fragmentado enviado a {next_hop_ip}:{next_hop_port} con contenido: {fp['msg']}")
                    #debug_print(f"Paquete enviado a {packet['ip']}:{packet['port']} con contenido: {packet['msg']}")
                    #debug_print(f"Nuevo TTL del paquete: {packet['ttl']}")
                    print(f"Reenviando paquete {packet['msg']} con destino final ({packet['ip']}:{packet['port']}) desde la direccion actual ({host}:{port}) hacia ({next_hop_ip}:{next_hop_port})")
                else:
                    print(f"No hay rutas hacia ({packet['ip']}:{packet['port']} para paquete con mensaje: {packet['msg']}")

