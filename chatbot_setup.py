import os
import json
import json5
import ast
from typing import List, Dict, Any
from dotenv import load_dotenv
import openai
import concurrent.futures

# Load env variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4.1")

# Instantiate OpenAI client
client = openai.OpenAI()

SYSTEM_PROMPT = (
    "You are an expert educator and grader in mathematics, physics, and theoretical subjects. "
    "Given a single question and its provided answer, evaluate correctness. "
    "Return valid JSON ONLY, with keys and string values enclosed in double quotes, "
    "in the form: {\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}. "
    "If valid, corrected_answer must be null. "
    "Preserve LaTeX formatting exactly."
)

def extract_json_substring(s: str) -> str:
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start:end+1]
    return s

def call_openai(question: str, answer: str) -> Dict[str, Any]:
    prompt = f"Question:\n{question}\n\nAnswer:\n{answer}"
    print(f"Calling OpenAI for question: {question[:50]}...")  # debug
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        raw = response.choices[0].message.content
        print(f"OpenAI response raw: {raw[:150]}...")  # debug
        json_text = extract_json_substring(raw)

        try:
            # Try strict JSON parse first
            result = json.loads(json_text)
        except json.JSONDecodeError:
            # fallback to json5 parse (more tolerant)
            result = json5.loads(json_text)
        print(f"Parsed result: {result}")  # debug
        return result

    except Exception as e:
        print(f"OpenAI call failed: {e}")  # debug
        return {"valid": False, "reason": f"OpenAI API error: {str(e)}", "corrected_answer": None}


def validate_record(record: Dict[str, Any]) -> Dict[str, Any]:
    question = record.get("question", "")
    answer = record.get("answer", "")
    result = call_openai(question, answer)

    new_rec = record.copy()
    if result.get("valid", False):
        new_rec["_validation"] = {"valid": True, "reason": result.get("reason")}
    else:
        if result.get("corrected_answer"):
            new_rec["answer"] = result["corrected_answer"]
            new_rec["_validation"] = {
                "valid": False,
                "reason": result.get("reason"),
                "corrected": True
            }
        else:
            new_rec["_validation"] = {
                "valid": False,
                "reason": result.get("reason"),
                "corrected": False
            }
    return new_rec

def process_records_parallel(records: List[Dict[str, Any]], max_workers: int = 5) -> List[Dict[str, Any]]:
    results = [None] * len(records)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(validate_record, rec): i for i, rec in enumerate(records)}
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()
    return results
