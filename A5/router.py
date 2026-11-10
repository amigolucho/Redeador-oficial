import socket
import sys

_debug_ = True

def debug_print(message):
    """Prints debug messages if debugging is enabled."""
    if _debug_:
        print(f"[DEBUG] {message}")

def parse_packet(IP_BRAcKETS: bytes) -> dict:
    """
    Función que permite extraer los headers y datos del paquete 
    recibido, transformando a una estructura de datos conveniente
    """
    ip, port, msg = IP_BRAcKETS.split(b";")
    structured_data = {
        "ip": ip.decode(),
        "port": int(port.decode()),
        "msg": msg.decode()
    }

    return structured_data

def create_packet(structured_data: dict) -> bytes:
    """
    Función que permite crear un paquete a partir de los headers y datos en una estructura de datos conveniente
    """
    ip = structured_data["ip"]
    port = structured_data["port"]
    msg = structured_data["msg"]
    packet = f"{ip};{port};{msg}".encode()
    return packet

def forward_packet(final: tuple[str, int], msg: str, send: tuple[str, int], s: socket.socket = None) -> None:
    """
    Función que permita enviar mensajes en el formato correcto hacia cualquier dirección IP y puerto especificado.
    """
    if s is None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            packet = create_packet({"ip": final[0], "port": final[1], "msg": msg})
        s.sendto(packet, (send[0], send[1]))
        debug_print(f"Paquete enviado a {send[0]}:{send[1]} con contenido: {packet.decode()}")

def check_routes(routes_files_name: str, destinarion_address: tuple[str, int]) -> tuple[str, int]:
    """
    Función que revisa en orden la tabla de rutas para indicar la adirección del siguiente salto.
    """
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

            if (int(initial_port) <= destinarion_address[1] <= int(dest_port)):#dest_ip == destinarion_address[0] and ver si comparar la ip o no ya q es solo uno
                debug_print(f"Ruta encontrada para {destinarion_address}: siguiente salto {next_hop_ip}:{next_hop_port}")   
                return (next_hop_ip, int(next_hop_port))
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

    IP_packet_v1 = b"127.0.0.1;8881;Hello, world!"
    parsed_IP_packet = parse_packet(IP_packet_v1)
    IP_packet_v2 = create_packet(parsed_IP_packet)
    debug_print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))

    # Creando socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        print(f"Router escuchando en {host}:{port}")

        while True:
            data, addr = s.recvfrom(1024)
            print(f"Recibiendo paquete desde {addr}: {data.decode()}")
            packet = parse_packet(data)
            if packet["ip"] == host and packet["port"] == port:
                print(f"Paquete destinado a este router. Tiene el siguiente mensaje: \n {packet['msg']}")
            else:
                next_hop = check_routes(path_table, (packet['ip'], packet['port'])) # next_hop_ip, next_hop_port
                if next_hop is not None:
                    forward_packet((packet['ip'], packet['port']), packet['msg'], next_hop, s)
                    print(f"Reenviando paquete {packet['ip']} con destino final ({packet['ip']}:{packet['port']}) desde la direccion actual ({host}:{port}) hacia ({next_hop[0]}:{next_hop[1]})")
                else:
                    print(f"No hay rutas hacia ({packet['ip']}:{packet['port']} para paquete con mensaje: {packet['msg']}")
