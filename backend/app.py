from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import yt_dlp
import whisper
import json
from analysis import analyze_text_file
from lyrics import fetch_album_tracks_and_lyrics, get_song_topic, GENAI_API_KEY
from db import get_db  # Import the function to get the MongoDB client
from bson import ObjectId  # Import ObjectId

app = Flask(__name__)
CORS(app)

YOUTUBE_API_KEY = 'AIzaSyD51Le8K5o-gwgQFWdiKJpQdrKFh-jU9sI'
FFMPEG_PATH = '/opt/homebrew/bin/ffmpeg'

# Initialize MongoDB client and collection
db = get_db()
collection = db['albums']  # Replace with your collection name

def cleanup_translations():
    try:
        # Define the regex pattern to match titles containing " by Genius .... "
        pattern = r'.* by Genius .*'
        
        # Find and delete entries matching the pattern
        result = collection.delete_many({'title': {'$regex': pattern, '$options': 'i'}})
        
        # Print the number of deleted entries
        print(f"Deleted {result.deleted_count} entries with translations.")
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")


def download_audio(url):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'audio.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'ffmpeg_location': FFMPEG_PATH,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return 'audio.wav'
    except Exception as e:
        raise Exception(f'Error downloading audio: {str(e)}')

def transcribe_audio(audio_file):
    try:
        model = whisper.load_model("tiny")
        print("Loading model...")
        result = model.transcribe(audio_file, fp16=False)
        print("Transcribed audio")
        transcription_text = result["text"]

        with open('transcript.txt', "w") as f:
            f.write(transcription_text)
        
        return transcription_text
    except Exception as e:
        raise Exception(f'Error transcribing audio: {str(e)}')

@app.route('/search')
def search():
    query = request.args.get('query')
    
    try:
        # Check if the album is already in the database
        db_result = collection.find_one({'title': {'$regex': query, '$options': 'i'}})
        
        if db_result:
            # Convert ObjectId to string
            db_result['_id'] = str(db_result['_id'])
            with open('results.json', 'w') as f:
                json.dump(db_result, f, indent=4)
            return jsonify(db_result)

        # If the album is not found in the database, proceed with the YouTube API call
        search_query = f'{query} TheNeedleDrop review'

        params = {
            'key': YOUTUBE_API_KEY,
            'part': 'snippet',
            'type': 'video',
            'maxResults': 1,
            'q': search_query
        }
        url = 'https://www.googleapis.com/youtube/v3/search'
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()

        video_id = data['items'][0]['id']['videoId']
        youtube_link = f'https://www.youtube.com/watch?v={video_id}'
        
        if youtube_link:
            audio = download_audio(youtube_link)
            transcribe_audio(audio)
            
            review_info_fp = 'review_info.txt'  # Ensure this path is correct for your setup
            scores = analyze_text_file('transcript.txt', review_info_fp)

            lyrics, title = fetch_album_tracks_and_lyrics(query)

            results = {
                'title': title,
                'score': scores,
                'lyrics': lyrics,
                'total_inputs': 1
            }
            
            # Insert or update the album data in MongoDB
            collection.update_one(
                {'title': title},
                {'$set': results},
                upsert=True
            )

            # Clean up translations
            cleanup_translations()

            with open('results.json', 'w') as f:
                json.dump(results, f, indent=4)

            return jsonify(results)
            
        return jsonify({'link': youtube_link})
    
    except requests.exceptions.HTTPError as http_err:
        return jsonify({'error': f'HTTP error occurred: {http_err}'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get_topic')
def get_topic():
    song_title = request.args.get('song_title')
    lyrics_dict_path = 'results.json'

    try:
        # Attempt to fetch the lyrics from the database first
        album_data = collection.find_one({
            'lyrics': {'$elemMatch': {'title': song_title}}
        })

        if album_data:
            # Write the database data to lyrics_dict_path
            with open(lyrics_dict_path, 'w') as f:
                json.dump(album_data, f, indent=4)
        
        with open(lyrics_dict_path, 'r') as f:
            lyrics_dict = json.load(f)

        # Log available keys for debugging
        print("Available song titles:", [v['title'] for v in lyrics_dict.get('lyrics', {}).values()])

        # Find the song entry based on the title
        song_entry = next((item for key, item in lyrics_dict.get('lyrics', {}).items() if item['title'] == song_title), None)

        if song_entry:
            lyrics = song_entry['lyrics']
            topic = get_song_topic(lyrics, GENAI_API_KEY)
            return jsonify({'topic': topic})
        else:
            return jsonify({'error': 'Song title not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/autocomplete')
def autocomplete():
    query = request.args.get('query', '').lower()
    if not query:
        return jsonify([])

    # Perform a case-insensitive search
    results = collection.find({
        'title': {'$regex': query, '$options': 'i'}
    })

    suggestions = [result['title'] for result in results]
    return jsonify(suggestions)

if __name__ == '__main__':
    app.run(debug=True)
