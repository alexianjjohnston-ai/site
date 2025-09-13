# yeezy_style_music_site.py
from flask import Flask, render_template, request, redirect, url_for, flash
import json, os, uuid, smtplib
from email.mime.text import MIMEText
from PIL import Image

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")

# -------- CONFIG --------
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")       # set on Render or locally
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")     # app password
UPLOAD_KEY = os.getenv("UPLOAD_KEY", "change-me")

DATA_SONGS = "songs.json"
DATA_ARTISTS = "artists.json"
DATA_MERCH = "merch.json"
DATA_EMAILS = "emails.json"
DATA_SETTINGS = "site_settings.json"

STATIC_MUSIC = "static/music"
STATIC_IMG = "static/img"
os.makedirs(STATIC_MUSIC, exist_ok=True)
os.makedirs(STATIC_IMG, exist_ok=True)

# -------- Helpers --------
def load_json(path, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def send_email(to_email, subject, message):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("[email] credentials not set, skipping send.")
        return
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, [to_email], msg.as_string())
        server.quit()
        print(f"[email] sent to {to_email}")
    except Exception as e:
        print("[email] send failed:", e)

def crop_to_square(path, size=800):
    try:
        img = Image.open(path)
        w, h = img.size
        m = min(w,h)
        left = (w - m)/2
        top = (h - m)/2
        right = left + m
        bottom = top + m
        img = img.crop((left, top, right, bottom))
        img = img.resize((size, size))
        img.save(path)
    except Exception as e:
        print("crop error:", e)

# -------- Routes --------
@app.route("/")
def index():
    songs = load_json(DATA_SONGS, {})
    artists = load_json(DATA_ARTISTS, {})
    settings = load_json(DATA_SETTINGS, {})
    label_name = settings.get("label_name", "HOMOSEXUAL")
    hero = settings.get("hero_image", "/static/img/banner.png")
    favicon = settings.get("favicon", "/static/img/favicon.ico")
    # songs is dict -> show values sorted by title
    songs_list = list(songs.values())
    return render_template("index.html",
                           songs=songs_list,
                           artists=list(artists.values()),
                           label_name=label_name,
                           hero=hero,
                           favicon=favicon)

@app.route("/merch")
def merch():
    merch = load_json(DATA_MERCH, {})
    return render_template("merch.html", merch=list(merch.values()))

# Simple artist page
@app.route("/artist/<artist_id>")
def artist_page(artist_id):
    songs = load_json(DATA_SONGS, {})
    artists = load_json(DATA_ARTISTS, {})
    artist = artists.get(artist_id)
    if not artist:
        return redirect("/")
    songs_list = [s for s in songs.values() if s["artist_id"] == artist_id]
    return render_template("artist.html", artist=artist, songs=songs_list)

# Subscribe
@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email")
    artist_name = request.form.get("artist")
    if not email or not artist_name:
        flash("Missing email or artist", "error")
        return redirect("/")
    emails = load_json(DATA_EMAILS, {})
    # store per artist name (simple)
    if artist_name not in emails:
        emails[artist_name] = []
    if email not in emails[artist_name]:
        emails[artist_name].append(email)
        save_json(DATA_EMAILS, emails)
        # send confirmation
        send_email(email, f"Subscribed to {artist_name}",
                   f"You will receive notifications for new releases by {artist_name}.")
        flash("Subscribed! Check your email.", "success")
    else:
        flash("Already subscribed.", "info")
    return redirect("/")

# Admin area (single route for forms)
@app.route("/admin", methods=["GET", "POST"])
def admin():
    key = request.args.get("key", "")
    if key != UPLOAD_KEY:
        return "Unauthorized", 401

    message = None
    songs = load_json(DATA_SONGS, {})
    artists = load_json(DATA_ARTISTS, {})
    merch = load_json(DATA_MERCH, {})
    settings = load_json(DATA_SETTINGS, {})

    if request.method == "POST":
        action = request.form.get("action")

        # ---- SONG: add / edit / delete ----
        if action == "add_song" or action == "edit_song":
            song_id = request.form.get("song_id") or str(uuid.uuid4())
            title = request.form.get("title","Untitled")
            artist_id = request.form.get("artist_id")
            producer = request.form.get("producer","")
            features = request.form.get("features","")
            audio = request.files.get("audio")
            cover = request.files.get("cover")

            # filenames default to old values if editing
            old = songs.get(song_id, {})
            audio_filename = old.get("filename","")
            cover_filename = old.get("cover","/static/img/placeholder.jpg")

            if audio:
                afn = f"{uuid.uuid4().hex}_{secure_filename(audio.filename)}"
                audio.save(os.path.join(STATIC_MUSIC, afn))
                audio_filename = f"/static/music/{afn}"

            if cover:
                cfn = f"{uuid.uuid4().hex}_{secure_filename(cover.filename)}"
                cover_path = os.path.join(STATIC_IMG, cfn)
                cover.save(cover_path)
                crop_to_square(cover_path, size=800)
                cover_filename = f"/static/img/{cfn}"

            songs[song_id] = {
                "id": song_id,
                "title": title,
                "artist_id": artist_id,
                "artist": artists.get(artist_id, {}).get("name", "Unknown"),
                "producer": producer,
                "features": features,
                "filename": audio_filename,
                "cover": cover_filename
            }
            save_json(DATA_SONGS, songs)
            message = "Song saved."
            # notify subscribers
            emails = load_json(DATA_EMAILS, {})
            artist_name = songs[song_id]["artist"]
            for e in emails.get(artist_name, []):
                send_email(e, f"New release: {title}",
                           f"{artist_name} released {title}. Listen: {request.url_root}")

        elif action == "delete_song":
            song_id = request.form.get("song_id")
            if song_id in songs:
                songs.pop(song_id)
                save_json(DATA_SONGS, songs)
                message = "Song deleted."

        # ---- ARTIST: add / edit / delete ----
        elif action in ("add_artist","edit_artist"):
            artist_id = request.form.get("artist_id") or str(uuid.uuid4())
            name = request.form.get("name","Unknown")
            bio = request.form.get("bio","")
            profile = request.files.get("profile")
            old = artists.get(artist_id, {})
            profile_filename = old.get("profile", "/static/img/artist_placeholder.jpg")
            if profile:
                pfn = f"{uuid.uuid4().hex}_{secure_filename(profile.filename)}"
                profile_path = os.path.join(STATIC_IMG, pfn)
                profile.save(profile_path)
                crop_to_square(profile_path, size=800)
                profile_filename = f"/static/img/{pfn}"
            artists[artist_id] = {
                "id": artist_id,
                "name": name,
                "bio": bio,
                "profile": profile_filename
            }
            save_json(DATA_ARTISTS, artists)
            message = "Artist saved."

        elif action == "delete_artist":
            artist_id = request.form.get("artist_id")
            if artist_id in artists:
                # remove songs by this artist
                songs = load_json(DATA_SONGS, {})
                songs = {k:v for k,v in songs.items() if v.get("artist_id") != artist_id}
                save_json(DATA_SONGS, songs)
                artists.pop(artist_id)
                save_json(DATA_ARTISTS, artists)
                message = "Artist and their songs deleted."

        # ---- MERCH: add / edit / delete ----
        elif action in ("add_merch","edit_merch"):
            merch_id = request.form.get("merch_id") or str(uuid.uuid4())
            name = request.form.get("name","Item")
            price = request.form.get("price","0.00")
            desc = request.form.get("description","")
            image = request.files.get("image")
            merch_data = load_json(DATA_MERCH, {})
            old = merch_data.get(merch_id, {})
            image_filename = old.get("image","/static/img/placeholder.jpg")
            if image:
                mfn = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                image_path = os.path.join(STATIC_IMG, mfn)
                image.save(image_path)
                crop_to_square(image_path, size=800)
                image_filename = f"/static/img/{mfn}"
            merch_data[merch_id] = {"id":merch_id,"name":name,"price":price,"description":desc,"image":image_filename}
            save_json(DATA_MERCH, merch_data)
            message = "Merch item saved."

        elif action == "delete_merch":
            merch_id = request.form.get("merch_id")
            merch_data = load_json(DATA_MERCH, {})
            if merch_id in merch_data:
                merch_data.pop(merch_id)
                save_json(DATA_MERCH, merch_data)
                message = "Merch deleted."

        # ---- SETTINGS ----
        elif action == "update_settings":
            label_name = request.form.get("label_name","HOMOSEXUAL")
            settings = load_json(DATA_SETTINGS, {})
            settings["label_name"] = label_name
            favicon = request.files.get("favicon")
            hero = request.files.get("hero")
            if favicon:
                fn = f"favicon_{uuid.uuid4().hex}_{secure_filename(favicon.filename)}"
                p = os.path.join(STATIC_IMG, fn)
                favicon.save(p)
                settings["favicon"] = f"/static/img/{fn}"
            if hero:
                fn = f"hero_{uuid.uuid4().hex}_{secure_filename(hero.filename)}"
                p = os.path.join(STATIC_IMG, fn)
                hero.save(p)
                # crop to wide banner (center square then resize wide)
                try:
                    img = Image.open(p)
                    img = img.resize((1600, 400))
                    img.save(p)
                except:
                    pass
                settings["hero_image"] = f"/static/img/{fn}"
            save_json(DATA_SETTINGS, settings)
            message = "Settings updated."

    # refresh data after POST
    songs = load_json(DATA_SONGS, {})
    artists = load_json(DATA_ARTISTS, {})
    merch = load_json(DATA_MERCH, {})
    settings = load_json(DATA_SETTINGS, {})
    return render_template("admin.html",
                           songs=list(songs.values()),
                           artists=list(artists.values()),
                           merch=list(merch.values()),
                           settings=settings,
                           message=message,
                           label_name=settings.get("label_name","HOMOSEXUAL"))

# need secure_filename
from werkzeug.utils import secure_filename

# -------- run --------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
