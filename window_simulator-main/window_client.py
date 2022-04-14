import socket
import sys

HOST = 'window'  # The server's hostname or IP address
PORT = 12345        # The port used by the server

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print("Connected")
    s.settimeout(120)
    while True:
        try:
            bytes = input("> ").encode('utf-8')
            if bytes == b'':
                continue
            elif bytes in (b'quit', b'exit', b'q'):
                break
            s.sendall(bytes)
            receiving = True
            received_bytes = b''
            while receiving:
                try:
                    received_bytes += s.recv(65536)
                    s.settimeout(.1)
                except:
                    receiving = False
                    s.settimeout(120)
            print(received_bytes.decode('utf-8'))
        except KeyboardInterrupt:
            break
            
    sys.exit()
