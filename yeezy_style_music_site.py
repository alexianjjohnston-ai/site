from flask import Flask, render_template, request, redirect
import json, os, uuid, smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# ----------- CONFIG -----------
EMAIL_ADDRESS = "Alexianjjohnston@gmail.com"  # Your Gmail
EMAIL_PASSWORD = "izwc nbwc oilo ujvl"       # Your Gmail App Password
SONGS_FILE = 'songs.json'
ARTISTS_FILE = 'artists.json'
EMAILS_FILE = 'emails.json'
SETTINGS_FILE = 'site_settings.json'
MUSIC_FOLDER = 'static/music'
IMG_FOLDER = 'static/img'

os.makedirs(MUSIC_FOLDER, exist_ok=True)
os.makedirs(IMG_FOLDER, exist_ok=True)

# ----------- HELPERS -----------
def load_json(path):
    if os.path.exists(path):
        with open(path,'r') as f:
            return json.load(f)
    return {}

def save_json(path,data):
    with open(path,'w') as f:
        json.dump(data,f,indent=2)

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

# ----------- ROUTES -----------
@app.route('/')
def index():
    songs = load_json(SONGS_FILE)
    artists = load_json(ARTISTS_FILE)
    settings = load_json(SETTINGS_FILE)
    label_name = settings.get('label_name', 'HOMOSEXUAL')
    hero_image = settings.get('hero_image', '/static/img/placeholder.jpg')
    return render_template('index.html', songs=songs, artists=artists, label_name=label_name, hero_image=hero_image)

@app.route('/admin', methods=['GET','POST'])
def admin():
    UPLOAD_KEY = os.getenv('UPLOAD_KEY','change-me')
    key = request.args.get('key','')
    if key != UPLOAD_KEY:
        return "Unauthorized",401

    message = ''
    songs = load_json(SONGS_FILE)
    artists = load_json(ARTISTS_FILE)
    settings = load_json(SETTINGS_FILE)
    label_name = settings.get('label_name','HOMOSEXUAL')

    if request.method == 'POST':
        action = request.form.get('action')
        
        # --- Upload or Edit Song ---
        if action in ['upload_song','edit_song']:
            song_id = request.form.get('song_id') or str(uuid.uuid4())
            title = request.form.get('title','Untitled')
            artist_name = request.form.get('artist','Unknown')
            producer = request.form.get('producer','')
            features = request.form.get('features','')
            audio_file = request.files.get('audio')
            cover_file = request.files.get('image')

            audio_filename = songs.get(song_id,{}).get('filename','')
            cover_filename = songs.get(song_id,{}).get('cover','/static/img/placeholder.jpg')

            if audio_file:
                audio_filename = f"{uuid.uuid4().hex}_{audio_file.filename}"
                audio_path = os.path.join(MUSIC_FOLDER,audio_filename)
                audio_file.save(audio_path)

            if cover_file:
                cover_filename = f"{uuid.uuid4().hex}_{cover_file.filename}"
                cover_path = os.path.join(IMG_FOLDER,cover_filename)
                cover_file.save(cover_path)

            songs[song_id] = {
                'title': title,
                'artist': artist_name,
                'producer': producer,
                'features': features,
                'filename': f'/static/music/{audio_filename}',
                'cover': f'/static/img/{cover_filename}'
            }
            save_json(SONGS_FILE,songs)
            message = f"Song '{title}' saved successfully."

            # Notify subscribers
            emails = load_json(EMAILS_FILE)
            if artist_name in emails:
                for e in emails[artist_name]:
                    send_email(e, f"New release by {artist_name}", f"{artist_name} just released '{title}'\nListen now: {request.url_root}")

        # --- Add/Edit Artist ---
        elif action in ['add_artist','edit_artist']:
            artist_id = request.form.get('artist_id') or str(uuid.uuid4())
            name = request.form.get('name','Unknown')
            bio = request.form.get('bio','')
            profile_file = request.files.get('image')
            profile_filename = artists.get(artist_id,{}).get('profile','/static/img/artist_placeholder.jpg')
            if profile_file:
                profile_filename = f"{uuid.uuid4().hex}_{profile_file.filename}"
                profile_path = os.path.join(IMG_FOLDER,profile_filename)
                profile_file.save(profile_path)
            artists[artist_id] = {
                'name': name,
                'bio': bio,
                'profile': f'/static/img/{profile_filename}'
            }
            save_json(ARTISTS_FILE,artists)
            message = f"Artist '{name}' saved successfully."

        # --- Update Site Settings ---
        elif action == 'update_settings':
            label_name = request.form.get('label_name', label_name)
            hero_file = request.files.get('hero_image')
            hero_image = settings.get('hero_image','/static/img/placeholder.jpg')
            if hero_file:
                hero_filename = f"{uuid.uuid4().hex}_{hero_file.filename}"
                hero_path = os.path.join(IMG_FOLDER,hero_filename)
                hero_file.save(hero_path)
                hero_image = f'/static/img/{hero_filename}'
            settings['label_name'] = label_name
            settings['hero_image'] = hero_image
            save_json(SETTINGS_FILE,settings)
            message = "Site settings updated."

    return render_template('admin.html', songs=songs, artists=artists, message=message, label_name=label_name)

@app.route('/subscribe',methods=['POST'])
def subscribe():
    email = request.form.get('email')
    artist = request.form.get('artist')
    if email and artist:
        data = load_json(EMAILS_FILE)
        if artist not in data:
            data[artist] = []
        if email not in data[artist]:
            data[artist].append(email)
        save_json(EMAILS_FILE,data)
        send_email(email, f"Subscribed to {artist}", f"You are now subscribed to notifications for {artist} releases.")
    return redirect('/')

# ----------- RUN -----------
if __name__ == '__main__':
    print("Starting local Yeezy-style music promo site...")
    print(f"Music folder: {os.path.abspath(MUSIC_FOLDER)}")
    print(f"Image folder: {os.path.abspath(IMG_FOLDER)}")
    app.run(debug=True)
