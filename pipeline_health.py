import socket
import sys
import time

def check_port(name, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        result = s.connect_ex(('127.0.0.1', port))
        if result == 0:
            print(f"[OK] {name} is active on port {port}")
            return True
        else:
            print(f"[ERROR] {name} is OFFLINE (Port {port})")
            return False

print("=== PIPELINE HANDSHAKE CHECK ===")
n8n_ok = check_port("n8n Engine", 5678)
ingest_ok = check_port("Ingest Server", 5005)

if n8n_ok and ingest_ok:
    print("SUCCESS: All handshakes verified. Ready for Bridge.")
    sys.exit(0)
else:
    print("CRITICAL: Pipeline is broken. Check the windows above for errors.")
    sys.exit(1)