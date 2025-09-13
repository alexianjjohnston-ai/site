from flask import Flask, render_template, request, redirect, send_from_directory
import json, os, uuid, smtplib
from email.mime.text import MIMEText
from PIL import Image

app = Flask(__name__)

# -------- CONFIG --------
EMAIL_ADDRESS = "Alexianjjohnston@gmail.com"
EMAIL_PASSWORD = "izwc nbwc oilo ujvl"   # Gmail App Password
SONGS_FILE = 'songs.json'
ARTISTS_FILE = 'artists.json'
EMAILS_FILE = 'emails.json'
MUSIC_FOLDER = 'static/music'
IMG_FOLDER = 'static/img'
FAVICON_FILE = 'static/img/favicon.ico'

os.makedirs(MUSIC_FOLDER, exist_ok=True)
os.makedirs(IMG_FOLDER, exist_ok=True)

# -------- HELPERS --------
def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def send_email(to_email, subject, message):
    try:
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, [to_email], msg.as_string())
        server.quit()
    except Exception as e:
        print("Email sending failed:", e)

def crop_image(image_path, size=(500, 500)):
    try:
        img = Image.open(image_path)
        img = img.convert("RGB")
        img.thumbnail(size)
        img.save(image_path)
    except Exception as e:
        print("Image crop failed:", e)

# -------- ROUTES --------
@app.route('/')
def index():
    songs = load_json(SONGS_FILE, [])
    artists = load_json(ARTISTS_FILE, [])
    return render_template("index.html",
        songs=songs,
        artists=artists,
        label_name="HOMOSEXUAL"
    )

@app.route('/merch')
def merch():
    return render_template("merch.html", label_name="HOMOSEXUAL")

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/img'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/admin', methods=['GET','POST'])
def admin():
    UPLOAD_KEY = os.getenv('UPLOAD_KEY', 'change-me')
    key = request.args.get('key', '')
    if key != UPLOAD_KEY:
        return "Unauthorized", 401

    songs = load_json(SONGS_FILE, [])
    artists = load_json(ARTISTS_FILE, [])
    emails = load_json(EMAILS_FILE, {})

    message = ""

    if request.method == 'POST':
        action = request.form.get('action')

        # ---- Upload Song ----
        if action == 'upload_song':
            title = request.form.get('title','Untitled')
            artist_name = request.form.get('artist','Unknown')
            producer = request.form.get('producer','')
            features = request.form.get('features','')
            audio_file = request.files.get('audio')
            cover_file = request.files.get('image')

            audio_filename, cover_filename = '', '/static/img/placeholder.jpg'

            if audio_file:
                audio_filename = f"{uuid.uuid4().hex}_{audio_file.filename}"
                audio_path = os.path.join(MUSIC_FOLDER, audio_filename)
                audio_file.save(audio_path)

            if cover_file:
                cover_filename = f"{uuid.uuid4().hex}_{cover_file.filename}"
                cover_path = os.path.join(IMG_FOLDER, cover_filename)
                cover_file.save(cover_path)
                crop_image(cover_path)

            song = {
                'id': uuid.uuid4().hex,
                'title': title,
                'artist': artist_name,
                'producer': producer,
                'features': features,
                'filename': f'/static/music/{audio_filename}',
                'cover': f'/static/img/{cover_filename}'
            }
            songs.append(song)
            save_json(SONGS_FILE, songs)
            message = f"Song '{title}' uploaded successfully."

            # notify subscribers
            if artist_name in emails:
                for e in emails[artist_name]:
                    send_email(e, f"New release by {artist_name}",
                        f"{artist_name} just dropped {title}\nListen: http://127.0.0.1:5000")

        # ---- Add Artist ----
        elif action == 'add_artist':
            name = request.form.get('name','Unknown')
            bio = request.form.get('bio','')
            profile_file = request.files.get('image')

            profile_filename = '/static/img/artist_placeholder.jpg'
            if profile_file:
                profile_filename = f"{uuid.uuid4().hex}_{profile_file.filename}"
                profile_path = os.path.join(IMG_FOLDER, profile_filename)
                profile_file.save(profile_path)
                crop_image(profile_path)

            artists.append({
                'id': uuid.uuid4().hex,
                'name': name,
                'bio': bio,
                'profile': f'/static/img/{profile_filename}'
            })
            save_json(ARTISTS_FILE, artists)
            message = f"Artist '{name}' added successfully."

        # ---- Delete Song ----
        elif action == 'delete_song':
            song_id = request.form.get('song_id')
            songs = [s for s in songs if s['id'] != song_id]
            save_json(SONGS_FILE, songs)
            message = "Song deleted."

        # ---- Delete Artist ----
        elif action == 'delete_artist':
            artist_id = request.form.get('artist_id')
            artists = [a for a in artists if a['id'] != artist_id]
            save_json(ARTISTS_FILE, artists)
            message = "Artist deleted."

    return render_template("admin.html",
        songs=songs,
        artists=artists,
        message=message,
        label_name="HOMOSEXUAL"
    )

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    artist = request.form.get('artist')
    if email and artist:
        data = load_json(EMAILS_FILE, {})
        if artist not in data:
            data[artist] = []
        if email not in data[artist]:
            data[artist].append(email)
        save_json(EMAILS_FILE, data)
        send_email(email, f"Subscribed to {artist}",
            f"You are now subscribed to notifications for {artist} releases.")
    return redirect('/')

# -------- RUN --------
if __name__ == '__main__':
    print("Starting HOMOSEXUAL label site...")
    app.run(debug=True)
