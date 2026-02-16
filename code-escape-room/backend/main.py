# SSL workaround for corporate/proxy environments - MUST be before imports
import os
os.environ['REQUESTS_CA_BUNDLE'] = ''

from fastapi import FastAPI, HTTPException
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

logger.info(f"GOOGLE_API_KEY loaded: {os.getenv('GOOGLE_API_KEY')[:20]}..." if os.getenv("GOOGLE_API_KEY") else "GOOGLE_API_KEY not found")

# Google Gemini API helper function
def gemini_api_call(prompt):
    """Call Google Gemini REST API directly"""
    api_key = os.getenv("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    # Disable SSL verification for corporate proxy
    response = requests.post(url, json=payload, headers=headers, verify=False)
    result = response.json()
    
    if "candidates" in result and len(result["candidates"]) > 0:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise Exception(f"Unexpected API response: {result}")

# Initialize model status
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        model = True
        logger.info("Google Gemini client initialized successfully")
    else:
        logger.error("Google API key not found")
        model = None
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")
    model = None

app = FastAPI()
@app.get("/")
def read_root():
    return {"message": "Welcome to the Coding Escape Room API"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # לצרכי פיתוח בלבד
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeSubmission(BaseModel):
    code: str
    task_id: int | None = None


@app.post("/analyze-code")
async def analyze_code(submission: CodeSubmission):
    try:
        print("--- קיבלתי בקשה מה-Frontend ---")
        if not model:
            print("--- שגיאה: Gemini Model לא אותחל ---")
            raise HTTPException(status_code=500, detail="Gemini model not initialized")
        
        # Create prompt for code analysis with structured output request
        prompt = f"""
בחן את הקוד הבא בהקשר של משימת שיפור קוד (Refactoring).
תן משוב לימודי, מפורט ומעודד בעברית.

קוד המשתמש:
{submission.code}

תשוב בפורמט JSON בלבד (ללא טקסט נוסף לפני או אחרי):
{{
  "score": <מספר 1-10>,
  "feedback": "<פירוט מילולי: מה עובד טוב, מה לא קריא, אילו עקרונות SOLID הופרו או יושמו>",
  "hint": "<רמז ספציפי כיצד לשפר את הקוד>",
  "is_solved": <true או false>
}}
""" # <--- הוספתי את הסגירה החסרה כאן!

        # Call Gemini API
        feedback_text = gemini_api_call(prompt)
        
        # Try to extract JSON from the response
        try:
            import json
            # ... (שאר הלוגיקה של ה-JSON נשארת אותו דבר) ...
            
        except json.JSONDecodeError:
            # ...
            pass # (לצורך הדוגמה)
        
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
    uvicorn.run(app, host="0.0.0.0", port=8000)