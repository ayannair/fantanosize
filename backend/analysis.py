import nltk
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from scipy.special import softmax
import torch

nltk.download('punkt')

# keywords for each topic
keywords = {
    'lyrics': ['lyrics', 'words', 'writing', 'verses', 'chorus', 'hook', 'lines', 'bars', 'line', 'wordplay'],
    'production': ['beat', 'melody', 'harmony', 'rhythm', 'production', 'sound', 'instrumentation', 'arrangement', 'synths', 'bass', 'drums', 'guitar', 'keys', 'mix', 'mastering', 'sonically'],
    'features': ['feature', 'collaboration', 'guest', 'featuring', 'appearance', 'cameo', 'contribution'],
    'vocals': ['vocals', 'singing', 'rap', 'voice', 'delivery', 'performance', 'flow'],
    'originality': ['originality', 'innovation', 'unique', 'fresh', 'groundbreaking', 'experimental', 'creative', 'distinct', 'progressive', 'pioneering', 'original', 'clone', 'derivative', 'influence', 'inspired', 'homage', 'tribute', 'authentic', 'ripping off', 'generic'],
    'concept': ['concept', 'theme', 'cohesion', 'structure', 'production quality', 'is about', 'message', 'substance', 'narrative', 'story'],
}

# load tokenizer and model
MODEL = "cardiffnlp/twitter-roberta-base-sentiment"
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL)

weights = {
    'neg': 0.1,
    'neu': 0.2,
    'pos': 0.7
}

def extract_sentences(text):
    return nltk.sent_tokenize(text)

def extract_topic_sentences(sentences):
    topic_sentences = {topic: '' for topic in keywords}
    for sentence in sentences:
        for topic, words in keywords.items():
            if any(word in sentence.lower() for word in words):
                topic_sentences[topic] += sentence + ' '
    return topic_sentences

def get_review_segment(transcript):
    target_phrase = "this album a listen"
    lower_transcript = transcript.lower()
    
    pos = lower_transcript.rfind(target_phrase)
    
    if pos == -1:
        # if target phrase is not found, return last 10% of the transcript
        return transcript[int(len(transcript) * 0.90):]
    
    preceding_text = transcript[:pos]
    sentences = extract_sentences(preceding_text)

    # get last 7 sentences of transcript
    review_segment = ' '.join(sentences[-7:])
    return review_segment

def analyze_topic(topic_text):
    encoded_text = tokenizer(topic_text, return_tensors='pt', truncation=True, padding=True, max_length=512)
    input_ids = encoded_text['input_ids']
    attention_mask = encoded_text['attention_mask']

    with torch.no_grad():
        output = model(input_ids=input_ids, attention_mask=attention_mask)
        scores = output.logits[0].detach().numpy()
        scores = softmax(scores)
    
    return {
        'roberta_neg': float(scores[0]),
        'roberta_neu': float(scores[1]),
        'roberta_pos': float(scores[2])
    }

def compute_score(score_dict):
    combined_score = (score_dict['roberta_neg']*weights['neg'] +
                      score_dict['roberta_neu']*weights['neu'] +
                      score_dict['roberta_pos']*weights['pos'])
    return combined_score / 0.7 * 100

def analyze_text_file(file_path, review_info_fp):
    with open(file_path, 'r') as file:
        text = file.read()

    sentences = extract_sentences(text)

    topic_sentences = extract_topic_sentences(sentences)
    review_seg = get_review_segment(text)

    scores = {
        'lyrics_score': compute_score(analyze_topic(topic_sentences["lyrics"])),
        'production_score': compute_score(analyze_topic(topic_sentences["production"])),
        'features_score': compute_score(analyze_topic(topic_sentences["features"])),
        'vocals_score': compute_score(analyze_topic(topic_sentences["vocals"])),
        'originality_score': compute_score(analyze_topic(topic_sentences["originality"])),
        'concept_score': compute_score(analyze_topic(topic_sentences["concept"])),
    }

    average_score = sum(scores.values()) / len(scores)
    review_segment_score = compute_score(analyze_topic(review_seg))

    # check if review segment score is within 15 of average of all topic scores
    if abs(review_segment_score - average_score) <= 15:
        overall_score = review_segment_score
    else:
        overall_score = average_score

    scores['overall_score'] = overall_score

    with open(review_info_fp, 'w') as f:
        f.write(f"Lyrics segment: {topic_sentences['lyrics']}\n\n")
        f.write(f"Production segment: {topic_sentences['production']}\n\n")
        f.write(f"Features segment: {topic_sentences['features']}\n\n")
        f.write(f"Vocals segment: {topic_sentences['vocals']}\n\n")
        f.write(f"Originality segment: {topic_sentences['originality']}\n\n")
        f.write(f"Concept segment: {topic_sentences['concept']}\n\n")
        f.write(f"Review segment: {review_seg}\n\n")
    
    return scores
