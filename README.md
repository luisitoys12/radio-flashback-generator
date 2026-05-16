# 🎙️ Radio Flashback Generator

Generador de flashbacks informativos para radio usando RSS + Microsoft Edge TTS (gratis, sin API key) + música noticiosa de fondo.

## ✨ Características

- 📰 Lee múltiples feeds RSS automáticamente
- ✏️ Edita el texto antes de generar
- 🎙️ Voces Microsoft Edge TTS en español (México, España, neutro)
- 🎵 Mezcla con música noticiosa de fondo
- ⬇️ Descarga MP3 listo para AzuraCast/Dropbox
- 🌐 100% web, sin instalación para el usuario final

## 🚀 Deploy rápido

```bash
git clone https://github.com/luisitoys12/radio-flashback-generator
cd radio-flashback-generator
pip install -r requirements.txt
python app.py
```

Abre `http://localhost:5000` en tu navegador.

## 🐳 Deploy con Docker

```bash
docker build -t flashback-generator .
docker run -p 5000:5000 flashback-generator
```

## 📻 Voces disponibles

- `es-MX-DaliaNeural` - Español México (femenina)
- `es-MX-JorgeNeural` - Español México (masculina)
- `es-ES-ElviraNeural` - Español España (femenina)
- `es-ES-AlvaroNeural` - Español España (masculino)
- `es-US-PalomaNeural` - Español neutro

## 🎵 Música noticiosa

Sube tu música noticiosa en `static/music/` en formato MP3. La app la mezcla automáticamente con el audio de voz.

## 📄 Licencia

MIT - Uso libre, no comercial.
