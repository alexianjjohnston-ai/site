from flask import Flask, render_template, request, redirect
import json, os, uuid, smtplib
from email.mime.text import MIMEText
from PIL import Image   # NEW

app = Flask(__name__)

# ----------- CONFIG -----------
EMAIL_ADDRESS = "Alexianjjohnston@gmail.com"
EMAIL_PASSWORD = "izwc nbwc oilo ujvl"
SONGS_FILE = 'songs.json'
ARTISTS_FILE = 'artists.json'
EMAILS_FILE = 'emails.json'
MUSIC_FOLDER = 'static/music'
IMG_FOLDER = 'static/img'
BANNER_FILE = 'static/img/banner.png'   # NEW

os.makedirs(MUSIC_FOLDER, exist_ok=True)
os.makedirs(IMG_FOLDER, exist_ok=True)

# ----------- HELPERS -----------
def load_json(path):
    if os.path.exists(path):
        with open(path,'r') as f:
            return json.load(f)
    return []

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

def crop_to_square(img_path):  # NEW
    try:
        img = Image.open(img_path)
        width, height = img.size
        min_side = min(width, height)
        left = (width - min_side) / 2
        top = (height - min_side) / 2
        right = (width + min_side) / 2
        bottom = (height + min_side) / 2
        img = img.crop((left, top, right, bottom))
        img = img.resize((500, 500))  # Standard album cover size
        img.save(img_path)
    except Exception as e:
        print("Cropping failed:", e)

# ----------- ROUTES -----------
@app.route('/')
def index():
    songs = load_json(SONGS_FILE)
    artists = load_json(ARTISTS_FILE)
    return render_template(
        'index.html',
        songs=songs,
        artists=artists,
        label_name="HOMOSEXUAL",
        banner=BANNER_FILE
    )

@app.route('/admin', methods=['GET','POST'])
def admin():
    UPLOAD_KEY = os.getenv('UPLOAD_KEY','change-me')
    key = request.args.get('key','')
    if key != UPLOAD_KEY:
        return "Unauthorized",401

    message = ''
    songs = load_json(SONGS_FILE)
    artists = load_json(ARTISTS_FILE)
    emails = load_json(EMAILS_FILE)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'upload_song':
            title = request.form.get('title','Untitled')
            artist_name = request.form.get('artist','Unknown')
            producer = request.form.get('producer','')
            features = request.form.get('features','')
            audio_file = request.files.get('audio')
            cover_file = request.files.get('image')

            audio_filename = ''
            cover_filename = 'placeholder.jpg'

            if audio_file:
                audio_filename = f"{uuid.uuid4().hex}_{audio_file.filename}"
                audio_path = os.path.join(MUSIC_FOLDER,audio_filename)
                audio_file.save(audio_path)

            if cover_file:
                cover_filename = f"{uuid.uuid4().hex}_{cover_file.filename}"
                cover_path = os.path.join(IMG_FOLDER,cover_filename)
                cover_file.save(cover_path)
                crop_to_square(cover_path)  # NEW

            songs.append({
                'title': title,
                'artist': artist_name,
                'producer': producer,
                'features': features,
                'filename': f'/static/music/{audio_filename}',
                'cover': f'/static/img/{cover_filename}'
            })
            save_json(SONGS_FILE,songs)
            message = f"Song '{title}' uploaded successfully."

        elif action == 'add_artist':
            name = request.form.get('name','Unknown')
            bio = request.form.get('bio','')
            profile_file = request.files.get('image')
            profile_filename = 'artist_placeholder.jpg'
            if profile_file:
                profile_filename = f"{uuid.uuid4().hex}_{profile_file.filename}"
                profile_path = os.path.join(IMG_FOLDER,profile_filename)
                profile_file.save(profile_path)
                crop_to_square(profile_path)  # NEW
            artists.append({
                'name': name,
                'bio': bio,
                'profile': f'/static/img/{profile_filename}'
            })
            save_json(ARTISTS_FILE,artists)
            message = f"Artist '{name}' added successfully."

        elif action == 'upload_banner':  # NEW
            banner_file = request.files.get('banner')
            if banner_file:
                banner_path = os.path.join(IMG_FOLDER, "banner.png")
                banner_file.save(banner_path)
                message = "Banner updated successfully."

    return render_template(
        'admin.html',
        songs=songs,
        artists=artists,
        message=message,
        label_name="HOMOSEXUAL",
        banner=BANNER_FILE
    )

# ----------- RUN -----------
if __name__ == '__main__':
    print("Starting local Yeezy-style music promo site...")
    app.run(debug=True)
