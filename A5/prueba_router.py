import socket
import sys

_debug_ = False

def debug_print(message):
    """Prints debug messages if debugging is enabled."""
    if _debug_:
        print(f"[DEBUG] {message}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print('Uso: python prueba_router.py "<IP;puerto;TTL>" <IP_router_inicial> <puerto_router_inicial>')
        sys.exit(1)

    headers = sys.argv[1]
    ip = sys.argv[2]
    port = int(sys.argv[3])

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    with open("headers.txt", "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            paquete = f"{headers};{linea}".encode()
            debug_print(f"Enviando paquete a {ip}:{port} con contenido: {paquete.decode()}")
            s.sendto(paquete, (ip, port))

    s.close()