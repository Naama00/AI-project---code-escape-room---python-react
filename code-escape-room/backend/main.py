# SSL workaround for corporate/proxy environments - MUST be before imports
import os
import time
from collections import defaultdict
os.environ['REQUESTS_CA_BUNDLE'] = ''

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests
from dotenv import load_dotenv
import logging
import urllib3

# SSL workaround for corporate/proxy environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# הגדרת logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# טעינת משתני הסביבה מקובץ .env
load_dotenv()

logger.info(f"GOOGLE_CSE_ID loaded: {os.getenv('GOOGLE_CSE_ID')[:20]}..." if os.getenv("GOOGLE_CSE_ID") else "GOOGLE_CSE_ID not found")

# ========== הגדרות מגבלות ==========
MAX_CODE_LENGTH = 1000        # תווים מקסימליים בקוד
MAX_REQUESTS_PER_MINUTE = 5   # בקשות מקסימליות לדקה לכל IP
MIN_SECONDS_BETWEEN_REQUESTS = 5  # שניות מינימום בין בקשות לכל IP

# מעקב אחר בקשות לפי IP
request_timestamps = defaultdict(list)  # IP -> רשימת timestamps

def check_rate_limit(ip: str):
    """בודק אם ה-IP עבר את מגבלת הבקשות"""
    now = time.time()
    timestamps = request_timestamps[ip]
    
    # הסר timestamps ישנים (מעל דקה)
    request_timestamps[ip] = [t for t in timestamps if now - t < 60]
    timestamps = request_timestamps[ip]
    
    # בדוק מגבלת בקשות לדקה
    if len(timestamps) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"יותר מדי בקשות. מותר {MAX_REQUESTS_PER_MINUTE} בקשות לדקה."
        )
    
    # בדוק מגבלת זמן בין בקשות
    if timestamps and (now - timestamps[-1]) < MIN_SECONDS_BETWEEN_REQUESTS:
        wait = int(MIN_SECONDS_BETWEEN_REQUESTS - (now - timestamps[-1])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"המתן {wait} שניות לפני הבקשה הבאה."
        )
    
    # רשום את הבקשה הנוכחית
    request_timestamps[ip].append(now)

# ========== API Keys rotation ==========
API_KEYS = [
    os.getenv("GOOGLE_CSE_ID"),
    os.getenv("SECOND_GOOGLE_API_KEY"),
]
current_key_index = 0
model = any(API_KEYS)

def gemini_api_call(prompt):
    """Call Google Gemini REST API with automatic key rotation"""
    global current_key_index
    
    for attempt in range(len(API_KEYS)):
        api_key = API_KEYS[current_key_index]
        if not api_key:
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            continue
            
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        response = requests.post(url, json=payload, headers=headers, verify=False)
        
        if response.status_code in (429, 503):
            logger.warning(f"Key {current_key_index} returned {response.status_code}, switching to next key")
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            time.sleep(3)
            continue
        
        result = response.json()
        if "candidates" in result and len(result["candidates"]) > 0:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            raise Exception(f"Unexpected API response: {result}")
    
    raise Exception("All API keys exhausted or unavailable")

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Coding Escape Room API"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeSubmission(BaseModel):
    code: str
    task_id: int | None = None

@app.post("/analyze-code")
async def analyze_code(submission: CodeSubmission, request: Request):
    # בדיקת rate limit לפי IP
    client_ip = request.client.host
    check_rate_limit(client_ip)

    # בדיקת אורך קוד
    if len(submission.code.strip()) == 0:
        raise HTTPException(status_code=400, detail="הקוד ריק.")
    
    if len(submission.code) > MAX_CODE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"הקוד ארוך מדי. מקסימום {MAX_CODE_LENGTH} תווים."
        )

    try:
        print("--- קיבלתי בקשה מה-Frontend ---")
        if not model:
            print("--- שגיאה: Gemini Model לא אותחל ---")
            raise HTTPException(status_code=500, detail="Gemini model not initialized")
        
        prompt = f"""
אתה מנהל משחק לימודי. בחן את הקוד הבא בהקשר של משימת שיפור קוד (Refactoring).
המטרה: להחזיר משוב לימודי, מפורט מאוד, ומעודד בעברית.
התמקד בביצועים, קריאות, ועקרונות SOLID.

קוד המשתמש:
{submission.code}

---
הוראות נוקשות:
1. אל תחזיר את הכותרת של המשימה כמשוב.
2. התייחס ספציפית למה שהמשתמש כתב בקוד לעומת מה שהיה צריך לכתוב.
---

תשוב בפורמט JSON בלבד (ללא טקסט נוסף לפני או אחרי), והנה דוגמה למבנה הרצוי:
{{
  "score": 85,
  "feedback": "הקוד שלך נכון מבחינה לוגית, אך השתמשת במשתנה בוליאני מיותר. ניתן להחזיר את התוצאה ישירות.",
  "hint": "בדוק האם תוכל להחזיר את הביטוי (num % 2 == 0) ללא שימוש ב-if או משתנה נוסף.",
  "is_solved": false
}}
"""
        feedback_text = gemini_api_call(prompt)
        
        feedback_data = {
            "score": 0,
            "feedback": "לא ניתן היה לנתח את התשובה מה-AI.",
            "hint": "נסה לשלוח את הקוד שוב.",
            "is_solved": False
        }
        
        try:
            import json
            if "```json" in feedback_text:
                json_start = feedback_text.find("```json") + 7
                json_end = feedback_text.find("```", json_start)
                json_str = feedback_text[json_start:json_end].strip()
            elif "```" in feedback_text:
                json_start = feedback_text.find("```") + 3
                json_end = feedback_text.find("```", json_start)
                json_str = feedback_text[json_start:json_end].strip()
            else:
                json_str = feedback_text
            
            parsed_data = json.loads(json_str)
            feedback_data.update(parsed_data)
            
        except json.JSONDecodeError:
            print("--- שגיאה: לא ניתן לפענח JSON ---")
            feedback_data["feedback"] = feedback_text
        
        return {
            "status": "success",
            "feedback": feedback_data
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
TASKS = {
    1: {
        "title": "חישוב מע\"מ מבלבל",
        "description": "שנו את שמות הפונקציה והפרמטרים כדי להבין שמדובר בחישוב מע\"מ (17%) על מוצר.",
        "bad_code": "def f(a, b):\n    return a + b * 0.17"
    },
    2: {
        "title": "עקרון ה-DRY",
        "description": "שנו את הפונקציה כך שתקבל פרמטרים ותבצע את החישוב בלי לחזור על קוד ה-print.",
        "bad_code": "def calc():\n    print(\"Sum:\", 10+20)\n    print(\"Sum:\", 30+40)"
    },
    3: {
        "title": "הסתרת מספרים קסם",
        "description": "הפוך את מספרי ה'קסם' 0.08 ו-40 לקבועים בעלי שמות משמעותיים.",
        "bad_code": "def calculate_salary(base, hours):\n    tax = base * 0.08\n    bonus = hours * 40\n    return base - tax + bonus"
    },
    4: {
        "title": "List Comprehension",
        "description": "החלף את הלולאה המסורבלת בעלייה יעילה עם list comprehension.",
        "bad_code": "numbers = [1, 2, 3, 4, 5]\nsquares = []\nfor n in numbers:\n    squares.append(n * n)"
    },
    5: {
        "title": "תיאור פונקציה חסר",
        "description": "הוסף docstring המסביר מה הפונקציה עושה, מה הפרמטרים וזה החוזר.",
        "bad_code": "def process(data):\n    return [x.upper() for x in data if len(x) > 3]"
    },
    6: {
        "title": "משתני גלובליים בעיתיים",
        "description": "החלף את משתני הגלובליים בפרמטרים שנשלחים לפונקציה.",
        "bad_code": "counter = 0\ndef increment():\n    global counter\n    counter += 1\n    return counter"
    },
    7: {
        "title": "טיפול בשגיאות",
        "description": "הוסף טיפול בשגיאות לפונקציה שעלולה להיכשל עם קלט לא תקין.",
        "bad_code": "def divide(a, b):\n    return a / b"
    },
    8: {
        "title": "אפס לולאות מיותרות",
        "description": "הסר את הלולאה המיותרת וחשב ישירות.",
        "bad_code": "def get_sum(n):\n    total = 0\n    for i in range(1, n+1):\n        total = total + i\n    return total"
    },
    9: {
        "title": "Boolean מיותר",
        "description": "בטל את המשתנה הבוליאני המיותר והחזר ישירות את התוצאה.",
        "bad_code": "def is_even(num):\n    result = (num % 2 == 0)\n    return result"
    },
    10: {
        "title": "Type Hints",
        "description": "הוסף type hints לפונקציה כדי שהקוד יהיה ברור יותר.",
        "bad_code": "def greet(name):\n    return f'Hello, {name}!'"
    }
}

@app.get("/get-task/{task_id}")
def get_task(task_id: int):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)