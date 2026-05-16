from flask import Flask, render_template, request, jsonify, send_file
import feedparser
import os
import uuid
import re
import subprocess
from pydub import AudioSegment
from datetime import datetime

app = Flask(__name__)

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("static/music", exist_ok=True)

VOICES = {
    "es-MX-DaliaNeural": "🇲🇽 Dalia (México - Femenina)",
    "es-MX-JorgeNeural": "🇲🇽 Jorge (México - Masculino)",
    "es-ES-ElviraNeural": "🇪🇸 Elvira (España - Femenina)",
    "es-ES-AlvaroNeural": "🇪🇸 Álvaro (España - Masculino)",
    "es-US-PalomaNeural": "🌎 Paloma (Neutro)"
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
                noticias.append({
                    'fuente': feed_title,
                    'titulo': title,
                    'resumen': summary
                })
        except Exception as e:
            noticias.append({'error': str(e), 'url': url})
    return jsonify({'noticias': noticias})

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    texto = data.get('texto', '')
    voice = data.get('voice', 'es-MX-DaliaNeural')
    music_file = data.get('music_file', None)
    music_volume = int(data.get('music_volume', -18))

    if not texto:
        return jsonify({'error': 'Texto vacio'}), 400

    uid = str(uuid.uuid4())[:8]
    voice_path = os.path.join(OUTPUT_DIR, f"voz_{uid}.mp3")
    final_path = os.path.join(OUTPUT_DIR, f"flashback_{uid}.mp3")

    # Usar edge-tts via subprocess para evitar conflicto asyncio/Flask
    try:
        result = subprocess.run(
            ["edge-tts", "--voice", voice, "--text", texto, "--write-media", voice_path],
            timeout=60,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return jsonify({'error': f'TTS error: {result.stderr}'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout generando audio, texto muy largo'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    if not os.path.exists(voice_path):
        return jsonify({'error': 'No se genero el archivo de voz'}), 500

    # Mezclar con musica si hay
    music_dir = "static/music"
    music_files = [f for f in os.listdir(music_dir) if f.endswith('.mp3')]

    selected_music = None
    if music_file and music_file in music_files:
        selected_music = os.path.join(music_dir, music_file)
    elif music_files and not music_file:
        selected_music = None
    elif music_files and music_file == music_files[0]:
        selected_music = os.path.join(music_dir, music_files[0])

    if selected_music and os.path.exists(selected_music):
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
        except Exception as e:
            os.rename(voice_path, final_path)
    else:
        os.rename(voice_path, final_path)

    filename = f"flashback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
    return jsonify({'file': os.path.basename(final_path), 'filename': filename})

@app.route('/download/<file_id>')
def download(file_id):
    # Seguridad: solo permitir archivos en outputs/
    safe_id = os.path.basename(file_id)
    path = os.path.join(OUTPUT_DIR, safe_id)
    filename = request.args.get('filename', 'flashback.mp3')
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name=filename)
    return jsonify({'error': 'Archivo no encontrado'}), 404

@app.route('/music-list')
def music_list():
    music_dir = "static/music"
    files = [f for f in os.listdir(music_dir) if f.endswith('.mp3')]
    return jsonify({'files': files})

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
