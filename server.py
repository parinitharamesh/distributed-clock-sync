import socket
import time

HOST = "0.0.0.0"
PORT = 12345

# Create UDP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind server
server_socket.bind((HOST, PORT))

# Timeout so program doesn't freeze
server_socket.settimeout(10)

print("Clock Sync Server Started...\n")

try:
    while True:
        try:
            # Receive request from client
            data, addr = server_socket.recvfrom(1024)

            print(f"Request received from {addr}")

            # Server receive timestamp
            T2 = time.time()

            # Simulate small processing delay
            time.sleep(0.001)

            # Server send timestamp
            T3 = time.time()

            # Send timestamps back
            response = f"{T2},{T3}"
            server_socket.sendto(response.encode(), addr)

        except socket.timeout:
            continue

except KeyboardInterrupt:
    print("\nServer stopped.")

finally:
    server_socket.close()