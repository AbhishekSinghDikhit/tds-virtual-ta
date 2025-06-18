import os
import pickle
import json
import requests
from datetime import datetime
import undetected_chromedriver as uc
from config import START_DATE, END_DATE, PAGES, DATE_FORMAT
import time

CATEGORY_URL = "https://discourse.onlinedegree.iitm.ac.in/c/courses/tds-kb/34"
CATEGORY_API_URL = CATEGORY_URL + ".json"
TOPIC_API_FMT = "https://discourse.onlinedegree.iitm.ac.in/t/{slug}/{id}.json"
COOKIE_FILE = "discourse_content/discourse_cookies.pkl"
cache_dir = "discourse_content/cache/raw_posts"

def save_cookies(driver):
    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)

def load_cookies(driver):
    if not os.path.exists(COOKIE_FILE):
        return False
    driver.get("https://discourse.onlinedegree.iitm.ac.in")
    cookies = pickle.load(open(COOKIE_FILE, "rb"))
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()
    return True

def get_requests_session_from_driver(driver):
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])
    return session

def login_if_needed():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)
    print("🔐 Checking for login session...")
    driver.get("https://discourse.onlinedegree.iitm.ac.in")
    if not load_cookies(driver):
        print("\n🔑 Please complete Google SSO login in Chrome window.")
        input("⏸ Waiting...")
        save_cookies(driver)
        print("✅ Login successful. Cookies saved.")
    return driver, get_requests_session_from_driver(driver)

def fetch_all_category_topics(session):
    print(f"\n📡 Fetching all topics from: {CATEGORY_API_URL}")
    topics = []
    for i in range(PAGES):
        url = CATEGORY_API_URL + f"?page={i}"
        print(f"   ➡️ Page {i}")
        r = session.get(url)
        r.raise_for_status()
        data = r.json()
        new_topics = data["topic_list"]["topics"]
        if not new_topics:
            break
        for t in new_topics:
            created = datetime.strptime(t["created_at"][:10], DATE_FORMAT)
            if START_DATE <= created <= END_DATE:
                print(f"   ✅ Found topic: {t['title']} (created on {created})")
                topics.append({
                    "id": t["id"],
                    "slug": t["slug"],
                    "title": t["title"]
                })
            else:
                print(f"   ⚠️ Skipping topic: {t['title']} (created on {created})")
    print(f"🔍 Total topics found: {len(topics)}")
    return topics

def fetch_posts(session, topic_id, slug):
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{topic_id}_posts.json")

    if os.path.exists(cache_file):
        print(f"   🔁 Using cached post data for topic ID {topic_id}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"   📥 Fetching all posts for topic ID {topic_id}")
    base_url = f"https://discourse.onlinedegree.iitm.ac.in/t/{slug}/{topic_id}.json"

    all_posts = []
    page = 1

    while True:
        url = f"{base_url}?page={page}"
        print(f"   🔹 Fetching page {page}...")
        resp = session.get(url)
        if resp.status_code == 404:
            break  # No more pages
        resp.raise_for_status()
        data = resp.json()
        posts = data.get("post_stream", {}).get("posts", [])
        if not posts:
            break  # No more posts
        all_posts.extend(posts)
        page += 1
        time.sleep(0.1)  # Optional: Be polite to the server

    print(f"   ✅ Total posts fetched: {len(all_posts)}")

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2)

    return all_posts

def scrape_data():
    driver, session = login_if_needed()
    try:
        topics = fetch_all_category_topics(session)
        for i, topic in enumerate(topics, 1):
            print(f"\n📌 [{i}] {topic['title']}")
            posts = fetch_posts(session, topic["id"], topic["slug"])
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()
