import os
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from discourse_content.process_data import find_similar_questions_later
from course_content.process_data import find_similar_questions_later_tds
from course_content.content_filtered import course_content, course_shrinked, other_covered
import requests
import json
import re
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = "gpt-4o-mini"

# Create FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request body model
class QueryRequest(BaseModel):
    question: str
    image: str = None  # optional base64 screenshot


# Health check endpoint
@app.get("/")
async def root():
    return {"status": "TDS Virtual TA API is running 🚀"}


def get_ocr(image_data):
    # Construct the data URL for the image
    data_url = f"data:image/webp;base64,{image_data}"

    # Prepare the headers for the API request
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    # Prepare the payload for the API request
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please extract all text from this image."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        }
                    }
                ]
            }
        ],
        "max_tokens": 200
    }

    # Send the POST request to the OpenAI API
    response = requests.post(
        "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
        headers=headers,
        data=json.dumps(payload)
    )

    # Check if the request was successful
    if response.status_code == 200:
        result = response.json()
        extracted_text = result['choices'][0]['message']['content']
        return extracted_text
    else:
        print(f"Request failed with status code {response.status_code}: {response.text}")
        return None


def compute_embedding(user_question):
    cleaned = user_question.strip()[:2000]

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "text-embedding-3-small",
        "input": [cleaned]
    }

    print(f"[INFO] Computing embedding for question: {cleaned[:60]}...")
    response = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/embeddings", headers=headers, json=payload)
    response.raise_for_status()
    embedding = response.json()["data"][0]["embedding"]

    return np.array(embedding)


def discourse_related(user_query, context):
    system_prompt = f"""
        You are a professor for the IIT Madras course 'Tools in Data Science'. A student has asked a question.
        Below are up to 3 similar questions along with their corresponding answers from past interactions.

        Your task:
        1. Carefully read the student's question and the provided similar questions and answers.
        2. If any of the similar Q&A pairs are helpful, use them to write a clear, accurate, and helpful answer to the student's question. Use same analogies or metaphors given in the answers.
        3. Indicate which of the similar questions (1, 2, or 3) was most helpful in forming your answer.
        4. If none of the provided Q&A pairs are relevant or helpful, respond with:
           {{ "answer": "error", "relevant": "error" }}

        Respond strictly in the following JSON format:
        {{
          "answer": "...",
          "relevant": n  # where n is 1, 2, or 3, or "error" if none were useful
        }}

        context = {context}
        """
    system_prompt = system_prompt.lower()
    user_query = user_query.lower()

    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GPT_MODEL,
        # "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        reply_content = result["choices"][0]["message"]["content"]

        # Attempt to extract JSON if it's inside a markdown code block
        match = re.search(r"```json\s*(.*?)\s*```", reply_content, re.DOTALL)
        if match:
            reply_content = match.group(1)

        try:
            parsed_json = json.loads(reply_content)
            return parsed_json
        except json.JSONDecodeError:
            return {
                "answer": reply_content.strip(),
                "relevant": "error"
            }
    else:
        return {
            "answer": f"API error {response.status_code}: {response.text}",
            "relevant": "error"
        }


def tds_content_related(user_query, context):
    system_prompt = f"""
    You are a professor for the IIT Madras course 'Tools in Data Science'. A student has asked a question.

    Below are up to 3 related context passages from course materials.

    Your task:
    1. Read the question and the context carefully.
    2. If any context is relevant, use it to generate a clear, accurate, and helpful answer.
    3. Specify which context (1, 2, or 3) was most helpful.
    4. If none are relevant, return:
       {{ "answer": "error", "relevant": "error" }}

    Respond *only* in this exact JSON format:
    {{
      "answer": "...",
      "relevant": n  # where n is 1, 2, 3, or "error"
    }}

    context = {context}
    """

    system_prompt = system_prompt.lower()
    user_query = user_query.lower()

    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GPT_MODEL,
        # "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        reply_content = result["choices"][0]["message"]["content"]

        # Attempt to extract JSON if it's inside a markdown code block
        match = re.search(r"```json\s*(.*?)\s*```", reply_content, re.DOTALL)
        if match:
            reply_content = match.group(1)

        try:
            parsed_json = json.loads(reply_content)
            return parsed_json
        except json.JSONDecodeError:
            return {
                "answer": reply_content.strip(),
                "relevant": "error"
            }
    else:
        return {
            "answer": f"API error {response.status_code}: {response.text}",
            "relevant": "error"
        }


def course_related(user_query):
    system_prompt = f"""
    You are an assistant for the IIT Madras course 'Tools in Data Science' (May 2025), a 12-week, hands-on course focused on real-world data science workflows.

    Course Metadata:
    - Topics (`course_shrinked`): {course_shrinked}
      (Each item is a webpage title; if a title mentions a concept/tool, the corresponding page covers it.)
    - Related Technologies (`other_covered`): {other_covered}
    - Assessments: 7 graded assignments (best 4 count for 15%), 2 projects (20% each), remote exam (20%), final exam (25%)
    - Exams: Projects and remote exam are open-internet; final exam is in-person and closed-book
    - Grading: Combination of automated and LLM evaluation
    - Course Difficulty: High failure rate, time-intensive, unpredictable grading
    - Culture: Collaborative, open-book (except final exam)

    Rules:

    1. **Topic Matching**:
       - You must only select the topic from `course_shrinked`. Use an **exact string match** from the list.
       - If the query directly matches or clearly relates (in concept or technology) to a `course_shrinked` title, return that exact title as `"topic"`.
       - If multiple match, choose the most relevant. If none clearly match, pick the closest **verbatim** entry.
       - **You must not invent, paraphrase, summarize, or synthesize new topic names**. The topic must be exactly from `course_shrinked`.

    2. If the query is of the form “What is <topic>?” or similar, return:
       {{ "answer": "You can find the details in the course materials or official course webpage.", "topic": "<matched_topic>" }}

    3. If the query is about assessments, grading, or workload, answer based on the course metadata. Return both:
       {{ "answer": "<metadata-based answer>", "topic": "Course Page" }}

    4. If the query asks about dates or deadlines (assignments, exams, sessions, etc.), respond:
       {{ "answer": "Sorry, I don't have access to specific dates or deadlines.", "topic": "Course Page" }}

    5. If the query asks which tool, library, or technology to use in general:
       - Say the course uses multiple technologies.
       - Explicitly mention **every tool or technology referenced in the query**, even if only one is officially used in the course.
       - Do not recommend one over another. Emphasize that all mentioned are important and needed for the course.
       - Example: “This course uses a mix of tools and technologies. Since you mentioned R and Pandas, both are relevant and useful, and you are expected to learn both of them”

    6. If the query is about **a specific assignment question** (e.g., "Which tool should I use for Question 3 in Assignment 4?"):
       - Instruct the user to follow the question instructions exactly.
       - Explicitly name the technology specified in the assignment question.
       - Do not follow Rule 5 in this case.

    7. If the query is about syllabus, grading policies, exams, portals, or other logistics, generate an appropriate "answer" from course metadata and set:
       {{ "topic": "Course Page" }}

    Output format:
    - Return a **single valid JSON object**.
    - The object must include:
      - "answer": (your answer text)
      - "topic": (one of the exact entries from `course_shrinked` OR "Course Page")
    - Use only standard ASCII double quotes.
    - Do not include any text, markdown, comments, explanations, or extra formatting outside the JSON.

    STRICT CONSTRAINT:
    - The "topic" must exactly match one of the strings in `course_shrinked` (unless it is "Course Page").
    - If this rule is violated, your output is invalid.

    """

    system_prompt = system_prompt.lower()
    user_query = user_query.lower()

    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GPT_MODEL,
        # "temperature": 0.5,
        # "top_p": 1,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        reply_content = result["choices"][0]["message"]["content"]

        # Extract JSON from markdown code block if present
        json_match = re.search(r"```json\s*(.*?)\s*```", reply_content, re.DOTALL)
        if json_match:
            reply_content = json_match.group(1)

        try:
            parsed = json.loads(reply_content)
            return parsed
        except json.JSONDecodeError:
            return {"answer": reply_content.strip(), "topic": "null"}
    else:
        return {
            "answer": f"Error {response.status_code}: {response.text}",
            "topic": "null"
        }


@app.post("/api/")
async def answer_query(query: QueryRequest):
    try:
        image_data = ""
        if query.image:
            print("image found...")
            image_data = get_ocr(query.image)

        # Merge question and image data.
        data = query.question + image_data
        data_embeddings = compute_embedding(data)
        # Check discourse data for any similar question found.
        matches = find_similar_questions_later(data_embeddings)
        if matches:
            print("Using discourse context method...")
            for i in range(len(matches)):
                matches[i][0]['question'] = matches[i][0]['question'][:1500] + "....continued"
            llm_response = discourse_related(user_query=data, context=matches)
            print(llm_response)
            answer_text = llm_response["answer"]
            ques_num = llm_response["relevant"]
            if ques_num != "error":
                match, _ = matches[int(ques_num) - 1]

                return {
                    "answer": answer_text,
                    "links": [
                        {
                            "url": match['url'],
                            "text": match['answer']
                        }
                    ]
                }

        # Check discourse data for any similar question found.
        matches = find_similar_questions_later_tds(data_embeddings)
        if matches:
            print("Using TDS content context method...")
            llm_response = tds_content_related(user_query=data, context=matches)
            print(llm_response)
            answer_text = llm_response["answer"]
            ques_num = llm_response["relevant"]
            if ques_num != "error":
                match, _ = matches[int(ques_num) - 1]

                return {
                    "answer": answer_text,
                    "links": [
                        {
                            "url": match['url'],
                            "text": match['question']
                        }
                    ]
                }
        print("Using default method...")
        course_response = course_related(data)
        print(course_response)
        answer = course_response["answer"]
        topic = course_response["topic"]
        if topic in course_content:
            url = course_content[topic]
        else:
            url = "None"
        return {
            "answer": answer,
            "links": [
                {
                    "url": url,
                    "text": topic
                }
            ]
        }
    except Exception as e:
        print(f"Error: {e}")
        return {"answer": "An error occurred...", "links": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)