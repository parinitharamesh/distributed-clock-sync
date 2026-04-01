import socket
import time
from cryptography.fernet import Fernet

# ─────────────────────────────────────────────
# SHARED SECRET KEY (must match server.py)
# ─────────────────────────────────────────────
SHARED_KEY = b'DMGpGgCZTHSYOGEqBP8j0JW0OzMSwtqnH0TZAbLnLWM='
cipher = Fernet(SHARED_KEY)

SERVER_IP = "192.168.2.154"
PORT = 12345

CLIENT_ID = input("Enter Client ID: ")

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.settimeout(5)

# ─────────────────────────────────────────────
# MOD 3: Reliability settings
# ─────────────────────────────────────────────
MAX_RETRIES = 3
seq_number  = 0   # increments with every successful exchange

print("\nClock Sync Client Started (Secure + Reliable UDP)...\n")

try:
    while True:
        seq_number += 1
        retries = 0
        success = False

        while retries < MAX_RETRIES:
            try:
                T1 = time.time()

                # Placeholder values for first packet (no prior stats)
                delay_to_send  = 0.0
                offset_to_send = 0.0
                corrected_to_send = T1

                # ─────────────────────────────────────────
                # MOD 3: Include sequence number in packet
                # MOD 2: Encrypt before sending
                # ─────────────────────────────────────────
                msg = f"SYNC|{seq_number}|{CLIENT_ID}|{T1}|{delay_to_send}|{offset_to_send}|{corrected_to_send}"
                encrypted_msg = cipher.encrypt(msg.encode())
                client.sendto(encrypted_msg, (SERVER_IP, PORT))

                # Receive encrypted response
                raw_response, _ = client.recvfrom(4096)

                T4 = time.time()

                # MOD 2: Decrypt response
                try:
                    decrypted_response = cipher.decrypt(raw_response).decode()
                except Exception:
                    print(f"[SECURITY] Could not decrypt server response — retrying...")
                    retries += 1
                    continue

                # Expected: "ACK|<seq>|<T2>|<T3>"
                parts = decrypted_response.split("|")
                if parts[0] != "ACK" or len(parts) < 4:
                    print(f"[WARN] Unexpected response format: {decrypted_response}")
                    retries += 1
                    continue

                ack_seq = int(parts[1])
                T2      = float(parts[2])
                T3      = float(parts[3])

                # MOD 3: Verify the ACK matches our seq number
                if ack_seq != seq_number:
                    print(f"[WARN] Seq mismatch: sent {seq_number}, got ACK {ack_seq} — retrying...")
                    retries += 1
                    continue

                # ─────────────────────────────────────────
                # Clock calculations (same as before)
                # ─────────────────────────────────────────
                delay          = (T4 - T1) - (T3 - T2)
                offset         = ((T2 - T1) + (T3 - T4)) / 2
                corrected_time = time.time() + offset

                print(f"[{time.strftime('%H:%M:%S')}] Client ID   : {CLIENT_ID}")
                print(f"  Seq Number     : {seq_number}")
                if retries > 0:
                    print(f"  Retries Needed : {retries}")
                print(f"  Network Delay  : {delay:.6f} seconds")
                print(f"  Clock Offset   : {offset:.6f} seconds")
                print(f"  Corrected Time : {time.ctime(corrected_time)}")
                print()

                success = True
                break   # exit retry loop

            except socket.timeout:
                retries += 1
                print(f"[TIMEOUT] No response for seq={seq_number}, retry {retries}/{MAX_RETRIES}...")

        if not success:
            print(f"[ERROR] Packet seq={seq_number} lost after {MAX_RETRIES} retries. Skipping.\n")

        time.sleep(5)

except KeyboardInterrupt:
    print("\nClient stopped.")

finally:
    client.close()
