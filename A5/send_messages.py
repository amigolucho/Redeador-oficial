import socket
import sys

_debug_ = True

def debug_print(message):
    """Prints debug messages if debugging is enabled."""
    if _debug_:
        print(f"[DEBUG] {message}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python send_messages.py <IP:PORT destino> <mensaje> <IP:PORT envío>")
        sys.exit(1)

    dest_ip, dest_port = sys.argv[1].split(":")
    msg = sys.argv[2]
    ip, port = sys.argv[3].split(":")

    dest_port = int(dest_port)
    port = int(port)

    if (dest_ip, dest_port) == (ip, port):
        print("El packete ya está en la dirección de destino, no se puede enviar a sí mismo.")
        sys.exit(1)
    
    # Definiendo el packete
    packet = f"{dest_ip};{dest_port};{msg}".encode()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(packet, (ip, int(port)))
    
    debug_print(f"Paquete enviado a {ip}:{port} con contenido: {packet.decode()}")
    s.close()