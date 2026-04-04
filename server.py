import socket
import time
import json
import threading
import queue
from collections import defaultdict
from cryptography.fernet import Fernet
from flask import Flask, Response
from flask_cors import CORS

# ─────────────────────────────────────────────
# SHARED SECRET KEY (must match client.py)
# ─────────────────────────────────────────────
SHARED_KEY = b'DMGpGgCZTHSYOGEqBP8j0JW0OzMSwtqnH0TZAbLnLWM='
cipher = Fernet(SHARED_KEY)

HOST     = "0.0.0.0"
UDP_PORT = 12345
UI_PORT  = 5000       # open server_ui.html → connects here

# ─────────────────────────────────────────────
# SSE event queue — UI listens to this
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
# Per-client stats
# ─────────────────────────────────────────────
client_stats = defaultdict(lambda: {
    "request_count": 0,
    "delays": [],
    "offsets": [],
    "corrected_times": [],
    "client_id": "Unknown"
})

def build_summary(addr, stats):
    delays  = stats["delays"]
    offsets = stats["offsets"]
    cts     = stats["corrected_times"]
    return {
        "client_id":     stats["client_id"],
        "addr":          f"{addr[0]}:{addr[1]}",
        "total":         stats["request_count"],
        "avg_delay":     round(sum(delays) / len(delays), 6),
        "min_delay":     round(min(delays), 6),
        "max_delay":     round(max(delays), 6),
        "avg_offset":    round(sum(offsets) / len(offsets), 6),
        "last_10_times": [time.ctime(ct) for ct in cts[-10:]]
    }

# ─────────────────────────────────────────────
# UDP server (runs in background thread)
# ─────────────────────────────────────────────
def udp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST, UDP_PORT))
    server_socket.settimeout(10)
    print(f"[UDP]  Listening on port {UDP_PORT}")
    print(f"[UI]   Open server_ui.html in your browser\n")

    try:
        while True:
            try:
                raw_data, addr = server_socket.recvfrom(4096)

                # Decrypt
                try:
                    decrypted = cipher.decrypt(raw_data).decode()
                except Exception:
                    print(f"[SECURITY] Bad packet from {addr} — dropping.")
                    push("security", {"addr": f"{addr[0]}:{addr[1]}", "msg": "Decryption failed"})
                    continue

                parts = decrypted.split("|")
                if parts[0] != "SYNC" or len(parts) < 7:
                    continue

                seq         = parts[1]
                client_id   = parts[2]
                T1          = float(parts[3])
                c_delay     = float(parts[4])
                c_offset    = float(parts[5])
                c_corrected = float(parts[6])

                T2 = time.time()
                time.sleep(0.001)
                T3 = time.time()

                # Update stats
                stats = client_stats[addr]
                stats["client_id"] = client_id
                stats["request_count"] += 1
                stats["delays"].append(c_delay)
                stats["offsets"].append(c_offset)
                stats["corrected_times"].append(c_corrected)
                count = stats["request_count"]

                print(f"[{time.strftime('%H:%M:%S')}] #{count} {client_id} | seq={seq} | "
                      f"delay={c_delay:.6f}s | offset={c_offset:.6f}s")

                # Push live event to UI
                push("request", {
                    "time":      time.strftime('%H:%M:%S'),
                    "client_id": client_id,
                    "addr":      f"{addr[0]}:{addr[1]}",
                    "seq":       seq,
                    "count":     count,
                    "delay":     round(c_delay, 6),
                    "offset":    round(c_offset, 6),
                    "corrected": time.ctime(c_corrected)
                })

                # Summary every 10 requests
                if count % 10 == 0:
                    summary = build_summary(addr, stats)
                    push("summary", summary)
                    print(f"\n{'='*50}")
                    print(f"SUMMARY — {client_id}: avg_delay={summary['avg_delay']}s | avg_offset={summary['avg_offset']}s")
                    print(f"{'='*50}\n")

                # Send encrypted ACK
                response_plain = f"ACK|{seq}|{T2}|{T3}"
                encrypted_resp = cipher.encrypt(response_plain.encode())
                server_socket.sendto(encrypted_resp, addr)

            except socket.timeout:
                continue

    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()

# ─────────────────────────────────────────────
# Entry point — UDP in background, Flask in main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=udp_server, daemon=True).start()
    app.run(port=UI_PORT, threaded=True)
