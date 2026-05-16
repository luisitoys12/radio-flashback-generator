from flask import Flask, render_template, request, jsonify, send_file
import feedparser
import os
import uuid
import re
import requests as req
from gtts import gTTS
from pydub import AudioSegment
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

OUTPUT_DIR = "outputs"
MUSIC_DIR = "static/music"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

VOICES = {
    "es-mx": "🇲🇽 Español México",
    "es": "🇪🇸 Español España",
    "es-us": "🌎 Español Neutro (US)",
}

@app.route('/')
def index():
    return render_template('index.html', voices=VOICES)

@app.route('/fetch-rss', methods=['POST'])
def fetch_rss():
    data = request.json
    urls = data.get('urls', [])
    max_items = data.get('max_items', 3)
    noticias = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            feed_title = feed.feed.get('title', 'Sin titulo')
            for entry in feed.entries[:max_items]:
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))
                summary = re.sub('<[^<]+?>', '', summary)
                summary = summary[:300].strip()
                noticias.append({'fuente': feed_title, 'titulo': title, 'resumen': summary})
        except Exception as e:
            noticias.append({'error': str(e), 'url': url})
    return jsonify({'noticias': noticias})

@app.route('/upload-music-file', methods=['POST'])
def upload_music_file():
    """Sube un archivo MP3 desde el dispositivo del usuario"""
    if 'file' not in request.files:
        return jsonify({'error': 'No se recibio archivo'}), 400
    f = request.files['file']
    if not f.filename.lower().endswith('.mp3'):
        return jsonify({'error': 'Solo se aceptan archivos .mp3'}), 400
    uid = str(uuid.uuid4())[:8]
    filename = f"temp_music_{uid}.mp3"
    filepath = os.path.join(MUSIC_DIR, filename)
    f.save(filepath)
    return jsonify({'success': True, 'file': filename})

@app.route('/upload-music-url', methods=['POST'])
def upload_music_url():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL vacia'}), 400
    try:
        r = req.get(url, timeout=20, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200:
            return jsonify({'error': f'No se pudo descargar: HTTP {r.status_code}'}), 400
        uid = str(uuid.uuid4())[:8]
        filename = f"temp_music_{uid}.mp3"
        filepath = os.path.join(MUSIC_DIR, filename)
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return jsonify({'success': True, 'file': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    texto = data.get('texto', '')
    voice = data.get('voice', 'es-mx')
    music_file = data.get('music_file', '')
    music_volume = int(data.get('music_volume', -18))
    delete_after = data.get('delete_music_after', False)

    if not texto:
        return jsonify({'error': 'Texto vacio'}), 400

    uid = str(uuid.uuid4())[:8]
    voice_path = os.path.join(OUTPUT_DIR, f"voz_{uid}.mp3")
    final_path = os.path.join(OUTPUT_DIR, f"flashback_{uid}.mp3")

    try:
        tts = gTTS(text=texto, lang=voice, slow=False)
        tts.save(voice_path)
    except Exception as e:
        return jsonify({'error': f'Error TTS: {str(e)}'}), 500

    selected_music = None
    if music_file:
        candidate = os.path.join(MUSIC_DIR, os.path.basename(music_file))
        if os.path.exists(candidate):
            selected_music = candidate

    if selected_music:
        try:
            voz = AudioSegment.from_mp3(voice_path)
            musica = AudioSegment.from_mp3(selected_music)
            musica = musica + music_volume
            if len(musica) < len(voz):
                loops = (len(voz) // len(musica)) + 2
                musica = musica * loops
            musica = musica[:len(voz) + 2000].fade_out(2000)
            mezcla = musica.overlay(voz)
            mezcla.export(final_path, format="mp3", bitrate="192k")
            os.remove(voice_path)
            if delete_after and os.path.basename(music_file).startswith('temp_music_'):
                os.remove(selected_music)
        except Exception as e:
            os.rename(voice_path, final_path)
    else:
        os.rename(voice_path, final_path)

    filename = f"flashback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
    return jsonify({'file': os.path.basename(final_path), 'filename': filename})

@app.route('/download/<file_id>')
def download(file_id):
    safe_id = os.path.basename(file_id)
    path = os.path.join(OUTPUT_DIR, safe_id)
    filename = request.args.get('filename', 'flashback.mp3')
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name=filename)
    return jsonify({'error': 'Archivo no encontrado'}), 404

@app.route('/music-list')
def music_list():
    files = [f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')]
    return jsonify({'files': files})

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
