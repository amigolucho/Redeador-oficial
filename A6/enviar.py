import socket, sys

dest_port = int(sys.argv[1])
primer_router = int(sys.argv[2])
largo = int(sys.argv[3])

msg = "a" * largo
paquete = f"127.0.0.1;{dest_port};10;347;0;{len(msg)};0;{msg}".encode()
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(paquete, ("127.0.0.1", primer_router))