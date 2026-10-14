import SocketTCP   # si tu archivo se llama SocketTCP.py, usa: import SocketTCP
address = ('localhost', 5000)
# SERVER
print("[DEBUG] creando socket y haciendo bind en", address)
server_socketTCP = SocketTCP.SocketTCP()
server_socketTCP.bind(address)
print("[DEBUG] bind OK, escuchando en", server_socketTCP.bind_address)
print("[DEBUG] esperando accept()...")
connection_socketTCP, new_address = server_socketTCP.accept()
print("[DEBUG] accept OK")
print("[DEBUG]   new_address         =", new_address)
print("[DEBUG]   cliente (dest)      =", connection_socketTCP.connect_address)
print("[DEBUG]   seq tras handshake  =", connection_socketTCP.seq)
print("[DEBUG]   direccion distinta? =", new_address != server_socketTCP.connect_address)

# test 1
print("\n[DEBUG] ===== TEST 1 =====")
buff_size = 16
expected = "Mensje de len=16".encode()
print("[DEBUG] llamando recv(%d), esperado=%r (len=%d)" % (buff_size, expected, len(expected)))
full_message = connection_socketTCP.recv(buff_size)
print("Test 1 received:", full_message)
if full_message == "Mensje de len=16".encode(): print("Test 1: Passed")
else: print("Test 1: Failed")

# test 2
print("\n[DEBUG] ===== TEST 2 =====")
buff_size = 19
expected = "Mensaje de largo 19".encode()
print("[DEBUG] llamando recv(%d), esperado=%r (len=%d)" % (buff_size, expected, len(expected)))
full_message = connection_socketTCP.recv(buff_size)
print("Test 2 received:", full_message)
if full_message == "Mensaje de largo 19".encode(): print("Test 2: Passed")
else: print("Test 2: Failed")

# test 3
print("\n[DEBUG] ===== TEST 3 =====")
buff_size = 14
print("[DEBUG] llamando recv(%d) por primera vez (parte 1)" % buff_size)
message_part_1 = connection_socketTCP.recv(buff_size)

print("[DEBUG] llamando recv(%d) por segunda vez (parte 2)" % buff_size)
message_part_2 = connection_socketTCP.recv(buff_size)
print("[DEBUG] parte1 + parte2 = %r (len=%d)" % (
    message_part_1 + message_part_2, len(message_part_1 + message_part_2)))
print("Test 3 received:", message_part_1 + message_part_2)
if (message_part_1 + message_part_2) == "Mensaje de largo 19".encode(): print("Test 3: Passed")
else: print("Test 3: Failed")