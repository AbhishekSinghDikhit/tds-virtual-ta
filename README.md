# TDS Virtual Teaching Assistant API
Welcome to the TDS Virtual TA project! This is a powerful, modern API designed to answer questions for the IIT Madras "Tools in Data Science" (TDS) course. It combines web scraping, LLM-powered semantic embeddings, and similarity search to deliver smart, context-aware, and course-aligned answers.

---
### 🚀 Live Demo
- API Endpoint: https://tds-virtual-ta-uq32.onrender.com/api/

---

## 🚀 Features
- FastAPI server for interactive API endpoints
- Semantic similarity search over:
  - Historical student Q&A (from the IITM Discourse forum)
  - Official TDS course content (scraped automatically!)
- Leverages OpenAI's powerful embeddings and models (GPT-4o, etc.)
- Supports screenshot/image question OCR and text extraction
- Smart, context-driven answer construction using few-shot LLM prompting
- Links to the official TDS content or historical posts for transparency
- Easily extensible and well-structured for research, bots, or education tools

---

## 🗂️ Project Structure
```.
├── main.py                      # FastAPI server and core orchestration
├── config.py                    # Configuration (dates, paths, env)
├── fetch_process_data.py        # Data pipeline for scraping and embedding
├── discourse_content/
│   ├── scrape_data.py           # Automation for fetching forum Q&A
│   ├── filter_data.py           # Clean/structure forum data (plus OCR)
│   └── process_data.py          # Embedding, similarity, and query search
├── course_content/
│   ├── scrape_data.py           # Scrapes course website
│   ├── content_filtered.py      # Filtered content mapping and metadata
│   └── process_data.py          # Embedding, similarity, and query search          # 
└── requirements.txt             # Requirements necessary to run FASTAPI server.
```

---

## ⚡️ How It Works
### 1. Data Collection
- Crawls the course's Discourse forum for hundreds of Q&A pairs.
- Scrapes and processes the official TDS course handbook/notes.
- Applies OCR extraction to images/screenshots in posts if present.
### 2. Semantic Embedding
- Uses OpenAI models to convert questions/answers and course content into vector embeddings.
- Caches and manages all embeddings for efficiency.
### 3. Question Answering Flow
- Accepts user questions (and optional screenshots).
- Computes embedding for the input.
- <b>Tries to match with:</b>
  - Historical forum Q&A (highest semantic similarity)
  - Official TDS course content (passage-level similarity)
  - If no relevant match, applies custom rules for topic lookup using course metadata.
### 4. LLM-Powered Answer Synthesis
- LLM is prompted using the most-relevant context(s) and generates a JSON-structured answer.
- Output always links to the most-relevant sources.

---

## 🏗️ Setup & Usage
### 1. Clone & Install
```shell
git clone https://github.com/AbhishekSinghDikhit/tds-virtual-ta.git
cd tds-virtual-ta
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```
You need Python 3.9+

### 2. Environment Setup
- Create a <b>.env</b> file in the root directory with:
```text
OPENAI_API_KEY=your-openai-api-key-here
```

### 3. Scraping, Filtering, and Embedding (First Time/Data Update)
Run data pipeline scripts as needed. Example:

```shell
pip install -r requirements.txt  # installs necessary requirements for parsing the data.
python fetch_process_data.py       # Scrapes, filter, and process data.
```

One can also comment and uncomment data pipeline from ```fetch_process_data.py``` depending on where to fetch, filter, and process data from.

If data is already cached once, one have to delete the files in ```cache``` folder from ```course_content``` and ```discourse_content```.

<b>WARNING: </b> Don't delete any directory from cache folder, just delete the files from them.

### 4. Start the FastAPI Server
```shell
python main.py
```
By default, runs at ``` http://0.0.0.0:8000```.

### 5. API Usage Example
<b>Healthcheck

GET ```/```</b>

```json
{ "status": "TDS Virtual TA API is running 🚀" }
```
<b>Ask a Question

POST ```/api/```</b>

```json
{
  "question": "How do I use Docker in this course?",
  "image": null
}
```
<b>Response:</b>

```json
{
  "answer": "You should refer to the Docker page in the course content.",
  "links": [
    { "url": "https://tds.s-anand.net/#/docker", "text": "docker" }
  ]
}
```
For assignment screenshots: <b>send the image as base64 in ```"image"```.</b>

---

