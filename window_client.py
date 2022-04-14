import socket

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
            print(s.recv(1024).decode('utf-8'))
        except KeyboardInterrupt:
            break
