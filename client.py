import socket
import time

SERVER_IP = "127.0.0.1"
PORT = 12345

# Ask user for client ID
CLIENT_ID = input("Enter Client ID: ")

# Create UDP socket
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Timeout handling
client.settimeout(5)

print("\nClock Sync Client Started...\n")

try:
    while True:
        try:
            # Record send time
            T1 = time.time()

            # Send sync request
            client.sendto(b"SYNC", (SERVER_IP, PORT))

            # Receive server timestamps
            data, _ = client.recvfrom(1024)

            # Record receive time
            T4 = time.time()

            # Decode server timestamps
            T2, T3 = map(float, data.decode().split(","))

            # Calculate delay
            delay = (T4 - T1) - (T3 - T2)

            # Calculate clock offset
            offset = ((T2 - T1) + (T3 - T4)) / 2

            # Correct local clock
            local_time = time.time()
            corrected_time = local_time + offset

            print(f"\nClient ID: {CLIENT_ID}")
            print(f"Network Delay: {delay:.6f} seconds")
            print(f"Clock Offset: {offset:.6f} seconds")
            print(f"Corrected Time: {time.ctime(corrected_time)}\n")
            # Wait before next sync
            time.sleep(5)

        except socket.timeout:
            print("Server not responding... retrying")

except KeyboardInterrupt:
    print("\nClient stopped.")

finally:
    client.close()