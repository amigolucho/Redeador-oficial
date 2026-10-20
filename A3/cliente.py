import SocketTCP   # si tu archivo se llama SocketTCP.py, usa: import SocketTCP
import sys
# CLIENT

# Uso: python3 test_cl.py localhost 8000 < archivo.txt
if len(sys.argv) != 3:
    print("Uso: python3 test_cl.py <host> <puerto> < archivo.txt")
    sys.exit(1)
address = (sys.argv[1], int(sys.argv[2]))

address = ('localhost', 5000)

print("[DEBUG] creando socket cliente")
client_socketTCP = SocketTCP.SocketTCP()
print("[DEBUG] llamando connect(%s)..." % (address,))
client_socketTCP.connect(address)
print("[DEBUG] connect OK")
print("[DEBUG]   servidor (dest)     =", client_socketTCP.connect_address)
print("[DEBUG]   bind (dest)     =", client_socketTCP.bind_address)
print("[DEBUG]   seq tras handshake  =", client_socketTCP.seq)
print("[DEBUG]   dest != address?    =", client_socketTCP.bind_address != ('127.0.0.1', 5000))


# test 1
print("\n[DEBUG] ===== TEST 1 =====")
message = "Mensje de len=16".encode()
print("[DEBUG] enviando %r (len=%d) | seq antes=%d" % (message, len(message), client_socketTCP.seq))
client_socketTCP.send(message)
print("[DEBUG] send OK | seq despues=%d" % client_socketTCP.seq)

# test 2
print("\n[DEBUG] ===== TEST 2 =====")
message = "Mensaje de largo 19".encode()
print("[DEBUG] enviando %r (len=%d) | seq antes=%d" % (message, len(message), client_socketTCP.seq))
client_socketTCP.send(message)
print("[DEBUG] send OK | seq despues=%d" % client_socketTCP.seq)

# test 3
print("\n[DEBUG] ===== TEST 3 =====")
message = "Mensaje de largo 19".encode()
print("[DEBUG] enviando %r (len=%d) | seq antes=%d" % (message, len(message), client_socketTCP.seq))
client_socketTCP.send(message)
print("[DEBUG] send OK | seq despues=%d" % client_socketTCP.seq)
print("[DEBUG] fin de los tests del cliente")

#test 4
print("\n[DEBUG] ===== TEST 4 (archivo por stdin) =====")
message = sys.stdin.buffer.read()#  .encode()
print(message)
print("[DEBUG] enviando archivo (len=%d) | seq antes=%d" % (len(message), client_socketTCP.seq))
client_socketTCP.send(message)
print("[DEBUG] send OK | seq despues=%d" % client_socketTCP.seq)
print("[DEBUG] fin de los tests del cliente")


print("[DEBUG] Cerrando conexion")
client_socketTCP.close()