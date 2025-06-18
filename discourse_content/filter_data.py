import json
import re
import requests
import pytesseract
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
import os
from config import PYTESSERACT_PATH

# Paths
INPUT_DIR = "discourse_content/cache/raw_posts"
OUTPUT_FILE = "discourse_content/cache/filtered_posts/discourse_filtered.json"

# Tesseract path (optional for Windows users)
pytesseract.pytesseract.tesseract_cmd = PYTESSERACT_PATH

TARGET_USERS = {"carlton", "Saransh_Saini", "Jivraj", "s.anand"}

def clean_html_and_remove_noise(cooked):
    soup = BeautifulSoup(cooked, "html.parser")
    return soup.get_text().strip()

def extract_image_urls(cooked):
    return re.findall(r'https://[^"\s]+\.(?:png|jpg|jpeg)', cooked)

def ocr_from_url(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        image = Image.open(BytesIO(r.content))
        # Convert palette images with transparency to RGBA first
        if image.mode == "P":
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        return f"[OCR error: {str(e)}]"


def process_posts(posts):
    post_dict = {p["post_number"]: p for p in posts}
    qa_pairs = []

    def clean_text(text):
        text = re.sub(r"(?:Screenshot|image)[^\n]*?\d+×\d+[^\n]*?KB", "", text, flags=re.IGNORECASE)
        text = re.sub(r'@\w+', '', text)  # Remove @mentions like @user
        text = text.replace("\\n", " ").replace("\\", "").replace('\"', ' ')
        text = text.replace('\n', ' ')
        return re.sub(r'\s+', ' ', text).strip()

    for post in posts:
        if post.get("reply_to_post_number") and post["username"] in TARGET_USERS:
            answer_post = post
            question_post = post_dict.get(answer_post["reply_to_post_number"])
            if not question_post:
                continue

            q_text = clean_text(clean_html_and_remove_noise(question_post["cooked"]))
            a_text = clean_text(clean_html_and_remove_noise(answer_post["cooked"]))

            q_images = extract_image_urls(question_post["cooked"])
            a_images = extract_image_urls(answer_post["cooked"])

            q_ocr = [ocr_from_url(url) for url in q_images]
            a_ocr = [ocr_from_url(url) for url in a_images]

            if any(q_ocr):
                q_text += " [Image OCR] " + " ".join(clean_text(txt) for txt in q_ocr)
            if any(a_ocr):
                a_text += " [Image OCR] " + " ".join(clean_text(txt) for txt in a_ocr)

            qa_pairs.append({
                "question": q_text,
                "answer": a_text,
                "answered_by": answer_post["username"],
                "url": f"https://discourse.onlinedegree.iitm.ac.in{answer_post['post_url']}"
            })

    return qa_pairs

def filter_data():
    all_qa_pairs = []
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(INPUT_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                posts = json.load(f)
                print(f"📄 Processing {filename} with {len(posts)} posts...")
                qa_cleaned = process_posts(posts)
                all_qa_pairs.extend(qa_cleaned)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_qa_pairs, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Total {len(all_qa_pairs)} Q&A pairs saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    filter_data()
