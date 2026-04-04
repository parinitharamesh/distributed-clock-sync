import socket
import time
import json
import threading
import queue
from cryptography.fernet import Fernet
from flask import Flask, Response
from flask_cors import CORS

# ─────────────────────────────────────────────
# SHARED SECRET KEY (must match server.py)
# ─────────────────────────────────────────────
SHARED_KEY = b'DMGpGgCZTHSYOGEqBP8j0JW0OzMSwtqnH0TZAbLnLWM='
cipher = Fernet(SHARED_KEY)

SERVER_IP = "10.20.205.105"
UDP_PORT  = 12345
UI_PORT   = 5001      # open client_ui.html → connects here

CLIENT_ID = input("Enter Client ID: ")

# ─────────────────────────────────────────────
# SSE event queue
# ─────────────────────────────────────────────
event_queue = queue.Queue()

def push(event_type, data):
    event_queue.put({"type": event_type, "data": data})

# ─────────────────────────────────────────────
# Flask app for live UI
# ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

@app.route('/stream')
def stream():
    def generate():
        while True:
            try:
                event = event_queue.get(timeout=20)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    return Response(generate(), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ─────────────────────────────────────────────
# UDP sync loop (runs in background thread)
# ─────────────────────────────────────────────
def sync_loop():
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(5)

    MAX_RETRIES = 3
    seq_number  = 0
    last_delay  = 0.0
    last_offset = 0.0
    last_corrected = 0.0

    print(f"\n[UDP]  Syncing with {SERVER_IP}:{UDP_PORT}")
    print(f"[UI]   Open client_ui.html in your browser\n")

    try:
        while True:
            seq_number += 1
            retries = 0
            success = False

            while retries < MAX_RETRIES:
                try:
                    T1 = time.time()
                    last_corrected = T1 + last_offset

                    msg = f"SYNC|{seq_number}|{CLIENT_ID}|{T1}|{last_delay}|{last_offset}|{last_corrected}"
                    encrypted_msg = cipher.encrypt(msg.encode())
                    client.sendto(encrypted_msg, (SERVER_IP, UDP_PORT))

                    raw_response, _ = client.recvfrom(4096)
                    T4 = time.time()

                    try:
                        decrypted_response = cipher.decrypt(raw_response).decode()
                    except Exception:
                        print(f"[SECURITY] Could not decrypt server response — retrying...")
                        push("error", {"msg": "Decryption failed, retrying...", "seq": seq_number})
                        retries += 1
                        continue

                    parts = decrypted_response.split("|")
                    if parts[0] != "ACK" or len(parts) < 4:
                        retries += 1
                        continue

                    ack_seq = int(parts[1])
                    T2      = float(parts[2])
                    T3      = float(parts[3])

                    if ack_seq != seq_number:
                        print(f"[WARN] Seq mismatch: sent {seq_number}, got {ack_seq} — retrying...")
                        retries += 1
                        continue

                    delay          = (T4 - T1) - (T3 - T2)
                    offset         = ((T2 - T1) + (T3 - T4)) / 2
                    corrected_time = time.time() + offset
                    last_delay     = delay
                    last_offset    = offset
                    last_corrected = corrected_time

                    print(f"[{time.strftime('%H:%M:%S')}] seq={seq_number} | "
                          f"delay={delay:.6f}s | offset={offset:.6f}s | "
                          f"corrected={time.ctime(corrected_time)}")

                    push("sync", {
                        "time":      time.strftime('%H:%M:%S'),
                        "client_id": CLIENT_ID,
                        "seq":       seq_number,
                        "retries":   retries,
                        "delay":     round(delay, 6),
                        "offset":    round(offset, 6),
                        "corrected": time.ctime(corrected_time),
                        "status":    "success"
                    })

                    success = True
                    break

                except socket.timeout:
                    retries += 1
                    print(f"[TIMEOUT] seq={seq_number}, retry {retries}/{MAX_RETRIES}...")
                    push("timeout", {"seq": seq_number, "retry": retries})

            if not success:
                print(f"[ERROR] seq={seq_number} lost after {MAX_RETRIES} retries.\n")
                push("sync", {
                    "time":      time.strftime('%H:%M:%S'),
                    "client_id": CLIENT_ID,
                    "seq":       seq_number,
                    "retries":   retries,
                    "delay":     0,
                    "offset":    0,
                    "corrected": "—",
                    "status":    "failed"
                })

            time.sleep(5)

    except KeyboardInterrupt:
        pass
    finally:
        client.close()

# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=sync_loop, daemon=True).start()
    app.run(port=UI_PORT, threaded=True)

