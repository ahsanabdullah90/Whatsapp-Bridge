import os
import base64
import queue
import threading
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from faster_whisper import WhisperModel

app = Flask(__name__)
msg_queue = queue.Queue()

# --- 1. CONFIGURATION ---
BASE_DIR = r"C:\WhatsAppBridge\Data\Chats"
LOG_DIR = r"C:\WhatsAppBridge\Logs"
MODEL_SIZE = "base"

if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"ingest_{datetime.now().strftime('%Y%m%d')}.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- 2. WHISPER SETUP ---
logger.info("Pre-loading Whisper model...")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

# --- 3. BACKGROUND WORKER ---
def transcribe_worker():
    while True:
        task = msg_queue.get()
        if task is None: break
        try:
            segments, _ = model.transcribe(task['audio_path'], beam_size=5)
            transcript = " ".join([s.text for s in segments]).strip()
            
            with open(task['xml_path'], "r", encoding="utf-8") as f:
                content = f.read()
            
            placeholder = f"[[PENDING_TRANSCRIPTION_{task['ts']}]]"
            final_text = f"[VOICE NOTE]: {transcript}"
            
            new_content = content.replace(placeholder, final_text)
            temp_path = task['xml_path'] + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            os.replace(temp_path, task['xml_path'])
            
            logger.info(f"Transcription patched: {task['xml_path']}")
        except Exception as e:
            logger.error(f"Worker Failure: {e}")
        finally:
            msg_queue.task_done()

threading.Thread(target=transcribe_worker, daemon=True).start()

# --- 4. CORE LOGIC ---
def is_duplicate(xml_path, ts):
    if not os.path.exists(xml_path): return False
    with open(xml_path, 'r', encoding='utf-8') as f:
        f.seek(max(0, os.path.getsize(xml_path) - 2000)) 
        return f'<timestamp>{ts}</timestamp>' in f.read()

@app.route('/ingest', methods=['POST'])
def ingest():
    try:
        data = request.json
        raw_name = data.get("contact_name", "Unknown")
        phone_num = data.get("phone", "Unknown")
        
        contact_folder = "".join([c for c in raw_name if c.isalnum() or c in (' ', '_')]).strip()
        
        contact_dir = os.path.join(BASE_DIR, contact_folder)
        audio_dir = os.path.join(contact_dir, "Audio")
        for d in [contact_dir, audio_dir]:
            if not os.path.exists(d): os.makedirs(d)

        ts = int(data.get("timestamp"))
        dt = datetime.fromtimestamp(ts)
        
        xml_filename = f"{contact_folder}_{dt.strftime('%Y')}.xml"
        xml_file = os.path.join(contact_dir, xml_filename)

        if is_duplicate(xml_file, ts):
            return jsonify({"status": "ignored"}), 200

        body = data.get("body") or ""
        audio_tag = ""
        
        if data.get("media_data") and data.get("type") in ['ptt', 'audio']:
            audio_filename = f"{ts}.ogg"
            path_to_audio = os.path.join(audio_dir, audio_filename)
            with open(path_to_audio, "wb") as f:
                f.write(base64.b64decode(data.get("media_data")))
            
            body = f"[[PENDING_TRANSCRIPTION_{ts}]]"
            audio_tag = f"\n        <audio_file>{audio_filename}</audio_file>"
            msg_queue.put({'audio_path': path_to_audio, 'xml_path': xml_file, 'ts': ts})

        quoted = f"\n        <quoted_msg><author>{data.get('quoted_author')}</author><body>{data.get('quoted_body')}</body></quoted_msg>" if data.get("quoted_body") else ""
        
        entry = f"""    <message type="{data.get('type')}">
        <sender>{"Me" if data.get('fromMe') else raw_name}</sender>
        <phone>{phone_num}</phone>
        <timestamp>{ts}</timestamp>
        <time>{dt.strftime("%H:%M:%S")}</time>
        <status>{"Outgoing" if data.get('fromMe') else "Incoming"}</status>{quoted}{audio_tag}
        <body>{body}</body>
    </message>\n"""

        if not os.path.exists(xml_file):
            with open(xml_file, "w", encoding="utf-8") as f:
                f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<chat contact="{raw_name}" year="{dt.strftime("%Y")}">\n{entry}</chat>')
        else:
            with open(xml_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            if content.endswith("</chat>"):
                new_content = content[:-7] + entry + "</chat>"
                temp_path = xml_file + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                os.replace(temp_path, xml_file)

        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Ingest Error: {e}")
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    app.run(port=5005)