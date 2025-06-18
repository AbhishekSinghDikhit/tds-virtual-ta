import os
import json
import requests
import numpy as np
import pickle
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Constants
QA_JSON_PATH = "discourse_content/cache/filtered_posts/discourse_filtered.json"
EMBEDDINGS_PICKLE_CACHE_PATH = "discourse_content/cache/question_embeddings.pkl"
EMBEDDINGS_JSON_CACHE_PATH = "discourse_content/cache/question_embeddings.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-3-small"

# -------------------- Load Q&A Data --------------------
def load_qa_data(path=QA_JSON_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# -------------------- JSON Cache Utilities --------------------
def load_embedding_cache_json(path=EMBEDDINGS_JSON_CACHE_PATH):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_embedding_cache_json(cache, path=EMBEDDINGS_JSON_CACHE_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f)

# -------------------- Compute All Embeddings and Save to Pickle & JSON --------------------
def get_cached_embeddings(qa_data, pickle_path=EMBEDDINGS_PICKLE_CACHE_PATH, json_path=EMBEDDINGS_JSON_CACHE_PATH):
    if os.path.exists(pickle_path):
        print(f"[INFO] Loading cached embeddings from {pickle_path}")
        with open(pickle_path, "rb") as f:
            return pickle.load(f)

    print("[INFO] Computing embeddings and saving to cache...")
    questions = [item["question"] for item in qa_data]
    embeddings = []

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    max_chars_per_batch = 10000
    max_chars_per_question = 2000
    current_batch = []
    current_char_count = 0
    batch_num = 0

    for q in questions:
        cleaned = q.strip()[:max_chars_per_question]
        if current_char_count + len(cleaned) > max_chars_per_batch:
            print(f"[INFO] Sending batch {batch_num} with {len(current_batch)} questions ({current_char_count} chars)")
            payload = {
                "model": EMBEDDING_MODEL,
                "input": current_batch
            }
            response = requests.post(OPENAI_EMBEDDING_URL, headers=headers, json=payload)
            response.raise_for_status()
            batch_embeddings = [item["embedding"] for item in response.json()["data"]]
            embeddings.extend(batch_embeddings)

            batch_num += 1
            current_batch = []
            current_char_count = 0

        current_batch.append(cleaned)
        current_char_count += len(cleaned)

    if current_batch:
        print(f"[INFO] Sending final batch {batch_num} with {len(current_batch)} questions ({current_char_count} chars)")
        payload = {
            "model": EMBEDDING_MODEL,
            "input": current_batch
        }
        response = requests.post(OPENAI_EMBEDDING_URL, headers=headers, json=payload)
        response.raise_for_status()
        batch_embeddings = [item["embedding"] for item in response.json()["data"]]
        embeddings.extend(batch_embeddings)

    embeddings_np = np.array(embeddings)

    with open(pickle_path, "wb") as f:
        pickle.dump(embeddings_np, f)

    # Also cache to JSON for reuse of individual embeddings
    json_cache = {questions[i]: embeddings[i] for i in range(len(questions))}
    save_embedding_cache_json(json_cache, json_path)

    return embeddings_np

# -------------------- Similarity Functions --------------------
def cosine_similarity(a, b):
    a_norm = a / np.linalg.norm(a)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)
    return np.dot(b_norm, a_norm)

def find_similar_questions(user_embedding, qa_data, stored_embeddings, top_n=1, threshold=0.5):
    similarities = cosine_similarity(user_embedding, stored_embeddings)

    scored_results = [
        (qa_data[i], float(similarities[i]))
        for i in range(len(qa_data))
    ]
    sorted_results = sorted(scored_results, key=lambda x: x[1], reverse=True)
    return [entry for entry in sorted_results if entry[1] >= threshold][:top_n]

# -------------------- Entry Point Function --------------------
def find_similar_questions_later(user_embedding):
    qa_data = load_qa_data()
    stored_embeddings = get_cached_embeddings(qa_data)
    return find_similar_questions(user_embedding, qa_data, stored_embeddings)

def process_data():
    qa_data = load_qa_data()
    get_cached_embeddings(qa_data)
    return None