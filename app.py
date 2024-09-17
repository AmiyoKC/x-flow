from flask import Flask, render_template, jsonify, redirect, request, session
import spotify
from spotipy.oauth2 import SpotifyOAuth
import base64
import requests
import datetime
import os
from dotenv import load_dotenv
from flask_session import Session
from redis import Redis
from datetime import timedelta
from flask_cors import CORS








app = Flask(__name__)
CORS(app, supports_credentials=True)
load_dotenv()

# Get the secret key from environment variables
app.config["ENV"] = os.getenv("FLASK_ENV", "development")

# Redis configuration - hope this works
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "session:"
app.config["SESSION_REDIS"] = Redis.from_url(os.getenv("REDIS_URL"))  # Use the Redis URL from environment variables

app.config['SESSION_REFRESH_EACH_REQUEST'] = True

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

Session(app)


app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')
redis_connected = False



try:
    redis = Redis.from_url(os.getenv("REDIS_URL"))
    redis.ping()
    print("Connected to Redis on startup")
except Exception as e:
    print(f"Failed to connect to Redis on startup: {e}")

# Spotify API credentials from environment variables
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI', 'http://localhost:5001/callback')

SCOPE = 'playlist-modify-public'

if app.config["ENV"] == "production":
    app.config.update(
        SESSION_COOKIE_SECURE=True,  # Only transmit cookies over HTTPS
        SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript from accessing cookies
        SESSION_COOKIE_SAMESITE='None',  # Lax ensures cookies are sent for the same-site requests
        SESSION_COOKIE_DOMAIN='.onrender.com'  # Set domain explicitly

    )
else:
    app.config.update(
        SESSION_COOKIE_SECURE=False,  # In local development, do not require secure cookies
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
    )

print(f'Flask environment is {app.config["ENV"]}')


# Spotify API endpoints

GENRE_URL = 'https://api.spotify.com/v1/recommendations/available-genre-seeds'
  
distance = list(range(1, 20))
age = list(range(18, 75))
hours = list(range(0, 4))
minutes = list(range(0, 60))
NUM_DIVS = 3 # this is number of sections for entire workout. each will have it's own target BPM


@app.route("/")
def hello_world():
  # Get the access token using Client Credentials Flow
  access_token = get_spotify_access_token()

  if not access_token:
    return "Error: Could not authenticate with Spotify API", 500

  headers = {'Authorization': f'Bearer {access_token}'}

  # Make a request to the Spotify API to get available genres
  response = requests.get(GENRE_URL, headers=headers)

  if response.status_code == 200:
      genres = response.json().get('genres', [])
      print(f'Genres {genres}')
  else:
      print(f'Error retrieving genres: {response.status_code}, {response.text} using hardcoded genres instea' )
      genres  = ["acoustic", "afrobeat", "alt-rock", "alternative", "ambient", "anime", "black-metal", "bluegrass", "blues", "bossanova", "brazil", "breakbeat", "british", "cantopop", "chicago-house", "children", "chill", "classical", "club", "comedy", "country", "dance", "dancehall", "death-metal", "deep-house", "detroit-techno", "disco", "disney", "drum-and-bass", "dub", "dubstep", "edm", "electro", "electronic", "emo", "folk", "forro", "french", "funk", "garage", "german", "gospel", "goth", "grindcore", "groove", "grunge", "guitar", "happy", "hard-rock", "hardcore", "hardstyle", "heavy-metal", "hip-hop", "holidays", "honky-tonk", "house", "idm", "indian", "indie", "indie-pop", "industrial", "iranian", "j-dance", "j-idol", "j-pop", "j-rock", "jazz", "k-pop", "kids", "latin", "latino", "malay", "mandopop", "metal", "metal-misc", "metalcore", "minimal-techno", "movies", "mpb", "new-age", "new-release", "opera", "pagode", "party", "philippines-opm", "piano", "pop", "pop-film", "post-dubstep", "power-pop", "progressive-house", "psych-rock", "punk", "punk-rock", "r-n-b", "rainy-day", "reggae", "reggaeton", "road-trip", "rock", "rock-n-roll", "rockabilly", "romance", "sad", "salsa", "samba", "sertanejo", "show-tunes", "singer-songwriter", "ska", "sleep", "songwriter", "soul", "soundtracks", "spanish", "study", "summer", "swedish", "synth-pop", "tango", "techno", "trance", "trip-hop", "turkish", "work-out", "world-music"]

  return render_template('home.html',
                         distance=distance,
                         hours=hours,
                         minutes=minutes,
                         genres=genres,
                         age=age)




@app.route('/login')
def login():
  sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                          client_secret=SPOTIPY_CLIENT_SECRET,
                          redirect_uri=SPOTIPY_REDIRECT_URI,
                          scope=SCOPE)
  auth_url = sp_oauth.get_authorize_url()
  print(f"Authorization URL: {auth_url}")  # Print the auth URL for debugging
  print(f"Session before login redirect: {session}")
  
  session.modified = True  # Mark session as modified

  return redirect(auth_url)


@app.route('/callback')
def callback():
  print(f"Session before callback: {session}")  # Add this to inspect the session content
  print(f'Request header is {request.headers}')
  print(f"Request cookies: {request.cookies}")  # Add this line to print cookies


  sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SCOPE)

  # Get the authorization code from the query parameters
  code = request.args.get('code')
  if code:
    # Exchange the authorization code for an access token
    token_info = sp_oauth.get_access_token(code)
    selected_genres = session.get('selected_genres', [])
    distance = session.get('distance')
    age = int(session.get('age'))
    print(f'age is {age} and its type is {type(age)}')
    minutes = session.get('minutes')
    print('Good Good {minutes}')
    session['access_token'] = token_info['access_token']

    max_heart_rate = 220 - age
    target_bpm  = [int(0.5 * max_heart_rate), int(0.7 * max_heart_rate), int(0.8 * max_heart_rate)]
    playlist = create_playlist(target_bpm, minutes, selected_genres, session['access_token'])
  
    # Return the token information (or handle it in some other way)
    return render_template('playlist.html',
                           selected_genres=selected_genres,
                           minutes=minutes,
                           distance=distance,
                           age=age,
                           target_bpm=target_bpm,
                           playlist=playlist
                           )
  else:
    return "Error: No code provided by Spotify", 400

@app.route('/store_preferences',methods=['POST'])
def store_preferences():
   session.permanent = True  # Set the session to be permanent to use the lifetime

   selected_genres = request.form.getlist('genre')
   distance = request.form.get('number')
   age = request.form.get('age')

   minutes = workout_mins(request.form.get('pace-hr'),request.form.get('pace-min'))
   
   session['selected_genres'] = selected_genres  # Store genres in session
   session['distance'] = int(distance)
   session['minutes'] = minutes
   session['age'] = int(age)

   print(f"Session before login redirect: {session}")

   session.modified = True



   return redirect('/login')


####### SECTION FOR HELPER FUNCTIONS - move these into a module later

# Helper function to get Spotify access token using Client Credentials Flow
# Client Credential flow uses the apps credentials as opposed to a users credentials
# This is used to get the list of genres in the drop-down on the landing page
def get_spotify_access_token():
    auth_string = f"{SPOTIPY_CLIENT_ID}:{SPOTIPY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')

    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {'grant_type': 'client_credentials'}

    response = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)

    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        print(f"Failed to get access token: {response.status_code}, {response.text}")
        return None

# Helper function that breaks down the run into 3 chunks

# Helper functiona converts time to minutes 
def workout_mins(hours, minutes):
   return (int(hours) * 60) + int(minutes)



def create_playlist(target_bpm, minutes, selected_genres, access_token):
   headers = {'Authorization' : f'Bearer {access_token}'}
   user_profile_url = 'https://api.spotify.com/v1/me'
   response = requests.get(user_profile_url,headers=headers)

   if response.status_code != 200:
      return f'Error retrieving the user profile {response.text}'
   
   user_id = response.json()['id']
   ct = datetime.datetime.now()
   playlist = f'xflow-{ct}'
   create_playlist_url = f'https://api.spotify.com/v1/users/{user_id}/playlists'
   payload = {
      'name': playlist,
      'description': f'x-flow running playlist generated at {ct}',
      'public' : True
   }

   response = requests.post(create_playlist_url, headers=headers, json=payload)

   if response.status_code != 200:
      print(f'Error creating playlist {response.text}')

   playlist_id = response.json()['id']
   playlist_url = response.json()['external_urls']['spotify']

   recommendations_url = 'https://api.spotify.com/v1/recommendations'

   limit = int((minutes // 3) / 4) + 1  # each track assumed to be 4 mins long, this calculation gives you the number of songs for each third
   track_list = []
   for i in range(NUM_DIVS):
      
      params = {
          'limit': limit,  
          'seed_genres': ','.join(selected_genres),
          'min_tempo': target_bpm[i] - 0.1 * target_bpm[i],  # Set tempo range
          'max_tempo': target_bpm[i] + 0.1 * target_bpm[i],
          'max_artists': 10
        }
      
      

      response = requests.get(recommendations_url, headers=headers, params=params)
      if response.status_code != 200:
          print(f'Error returning recommendations {response.text}')
      
      track_uris = [track['uri'] for track in response.json()['tracks']]
      print(f'Found {len(track_uris)} tracks to add to the playlist.')


      # Step 4: Add tracks to the newly created playlist
      add_tracks_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
      payload = {
            'uris': track_uris
        }

      response = requests.post(add_tracks_url, headers=headers, json=payload)

      if response.status_code != 201:
        return f"Error adding tracks to playlist: {response.json()}"

      print('Tracks successfully added to the playlist.')
        
   return playlist_url
   
   

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5001, debug=True)