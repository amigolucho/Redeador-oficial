import socket
import sys

_debug_ = False
RR = {} # Diccionario para gestionar el round rubin contando cuantas veces se a accedido a una ruta. 

def debug_print(message):
    """Prints debug messages if debugging is enabled."""
    if _debug_:
        print(f"[DEBUG] {message}")

def parse_packet(IP_BRACKETS: bytes) -> dict:
    """
    Extrae los headers y datos del paquete. El TTL es opcional.
    """
    parts = IP_BRACKETS.split(b";", 3)
    ip, port = parts[0], parts[1]

    if len(parts) == 4 and parts[2].isdigit():
        ttl = int(parts[2].decode())
        msg = parts[3]
    else:
        ttl = None
        msg = b";".join(parts[2:])

    return {
        "ip": ip.decode(),
        "port": int(port.decode()),
        "msg": msg.decode(),
        "ttl": ttl
    }

def create_packet(structured_data: dict) -> bytes:
    """
    Crea un paquete a partir de la estructura. Si no hay TTL, no lo incluye.
    """
    ip = structured_data["ip"]
    port = structured_data["port"]
    msg = structured_data["msg"]
    ttl = structured_data.get("ttl")

    if ttl is None:
        packet = f"{ip};{port};{msg}".encode()
    else:
        packet = f"{ip};{port};{ttl};{msg}".encode()
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
            parts = line.split(" ")  # el formato de la línea es:  RED I_port F_port next_IP next_PORT , por ej 127.0.0.1/24 8881 8882 127.0.0.1 8882

            if len(parts) != 5:
                debug_print(f"Línea de ruta inválida: {line}")
                continue  # Ignorar líneas mal formateadas
            dest_ip, initial_port, dest_port, next_hop_ip, next_hop_port = parts

            if (int(initial_port) <= port <= int(dest_port)):#dest_ip == destinarion_address[0] and ver si comparar la ip o no ya q es solo uno
                debug_print(f"Ruta encontrada para {destinarion_address}: siguiente salto {next_hop_ip}:{next_hop_port}")   
                candidate_routes.append((next_hop_ip, int(next_hop_port)))
    
    if candidate_routes:
        # Seleccionar la ruta con el siguiente salto más cercano (implementación del algoritmo Round Robin)
        key = (initial_port, dest_port)
        i = RR.get(key, 0) % len(candidate_routes)
        RR[key] = (i + 1) % len(candidate_routes) 
        debug_print(f"key: {key}, i: {i}, RR[key]: {RR[key]}, candidate_routes: {candidate_routes}")
        return candidate_routes[i]

    debug_print(f"No se encontró ruta para {destinarion_address}")  
    return None

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python router.py <host_IP> <port> <path_tables>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    path_table = sys.argv[3]
    debug_print(f"Router IP: {host}, Router port: {port}, Router table: {path_table}")

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
                print(f"Paquete destinado a este router. Tiene el siguiente mensaje: \n {packet['msg']}")
            else:
                next_hop = check_routes(path_table, (packet['ip'], packet['port'])) # next_hop_ip, next_hop_port
                if next_hop is not None:
                    if packet['ttl'] is not None:
                        packet['ttl'] -= 1  # Decrementar el TTL antes de reenviar
                    #forward_packet((packet['ip'], packet['port']), packet['msg'], next_hop, s)
                    created_packet = create_packet(packet)
                    s.sendto(created_packet, next_hop)
                    debug_print(f"Paquete enviado a {packet['ip']}:{packet['port']} con contenido: {packet['msg']}")
                    debug_print(f"Nuevo TTL del paquete: {packet['ttl']}")
                    print(f"Reenviando paquete {packet['msg']} con destino final ({packet['ip']}:{packet['port']}) desde la direccion actual ({host}:{port}) hacia ({next_hop[0]}:{next_hop[1]})")
                else:
                    print(f"No hay rutas hacia ({packet['ip']}:{packet['port']} para paquete con mensaje: {packet['msg']}")
