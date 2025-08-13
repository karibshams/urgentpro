import os
import json
import json5
import unicodedata
from typing import List, Dict, Any
from dotenv import load_dotenv
import openai
import concurrent.futures

# Load env variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4.1")

client = openai.OpenAI()

# Key maps for supported languages
KEY_MAPS = {
    "English": {"question": "question", "answer": "answer", "question_type": "Question Type", "language": "Language"},
    "Chinese": {"question": "问题", "answer": "答案", "question_type": "问题类型", "language": "语言"},
    "Spanish": {"question": "pregunta", "answer": "respuesta", "question_type": "tipo de pregunta", "language": "idioma"},
    "Arabic": {"question": "السؤال", "answer": "الإجابة", "question_type": "نوع السؤال", "language": "اللغة"},
    "Hindi": {"question": "प्रश्न", "answer": "उत्तर", "question_type": "प्रश्न प्रकार", "language": "भाषा"},
    "Russian": {"question": "Вопрос", "answer": "Ответ", "question_type": "Тип вопроса", "language": "Язык"},
    "German": {"question": "Frage", "answer": "Antwort", "question_type": "Fragetyp", "language": "Sprache"},
    "French": {"question": "question", "answer": "réponse", "question_type": "type de question", "language": "langue"}
}

# Extra possible variants for keys across languages
FALLBACK_KEYS = {
    "question": ["question","pregunta","问题","вопрос","frage","السؤال","प्रश्न","вопрос","questão","въпрос"],
    "answer": ["answer","Answer","respuesta","答案","ответ","Ответ","réponse","الإجابة","الاجابة","إجابة","اجابة","उत्तर"],
    "question_type": ["question type","tipo de pregunta","问题类型","тип вопроса","fragetyp","نوع السؤال","प्रश्न प्रकार","type de question"],
    "language": ["language","idioma","语言","язык","sprache","اللغة","भाषा","langue"]
}

def normalize_key(key: str) -> str:
    return unicodedata.normalize("NFKC", key.strip().lower())

def get_key_map_for_language(language: str) -> Dict[str, str]:
    lang = language.strip().title()
    return KEY_MAPS.get(lang, KEY_MAPS["English"])

def map_record_fields(record: Dict[str, Any], key_map: Dict[str, str]) -> Dict[str, Any]:
    normalized_record = {normalize_key(k): v for k, v in record.items()}
    mapped = {}
    for eng_key, local_key in key_map.items():
        val = normalized_record.get(normalize_key(local_key), "")
        if not val:
            for alt_key in FALLBACK_KEYS.get(eng_key, []):
                if normalize_key(alt_key) in normalized_record:
                    val = normalized_record[normalize_key(alt_key)]
                    break
        mapped[eng_key] = val
    return mapped

def get_system_prompt(question_type: str) -> str:
    base = (
        "You are an expert educator, grader, and language expert specializing in mathematics, physics, and theoretical subjects. "
        "Your task is to evaluate the correctness of a given question and its provided answer in any language, including but not limited to English, Spanish, French, Chinese, Arabic, Russian, Hindi, and others. "
        "Follow these steps precisely, regardless of the language:\n"
        "1. Assess the provided answer for accuracy based on the given question. Ensure to check for logical consistency, correctness in mathematical or scientific reasoning, and clarity in the language used.\n"
        "2. If the answer is incorrect or lacks completeness, provide a detailed correction. Make sure to preserve the technical rigor and conceptual clarity while correcting.\n"
        "3. Identify any ambiguous language or missing information in the answer. If the question involves mathematical or scientific formulas, preserve and correct them with exact LaTeX formatting.\n"
        "4. If needed, clarify the wording of the answer to ensure it is precise and unambiguous, without altering the meaning or changing the core content.\n"
        "5. Consider linguistic nuances in different languages and ensure that translations or explanations respect the integrity of the original content. Adapt your reasoning style to the conventions and standards of each language used in the question and answer.\n"
        "6. If the answer includes any mathematical or scientific symbols, LaTeX expressions, or formulas, preserve them exactly and correct only when necessary.\n"
        "Return valid JSON ONLY, in the following format:\n"
        "{\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}\n"
        "- \"valid\": True if the answer is correct, False if it's not.\n"
        "- \"reason\": Provide a clear explanation of why the answer is correct or incorrect. Be as specific as possible, pointing out any errors in logic, calculation, or phrasing.\n"
        "- \"corrected_answer\": Provide the corrected answer if the original answer was wrong. If the answer was correct, this should be null.\n"
        "Ensure that your reasoning is clear, concise, and well-structured. If corrections are needed, provide a complete and accurate solution. Always preserve the original intent and meaning of the answer while making corrections."
    )


    qt = question_type.lower()
    if qt in ("explanation", "exp"): return base + " The answer should be a detailed explanation."
    elif qt in ("short answer", "short"): return base + " The answer should be concise and precise."
    elif qt in ("multiple choice", "mcq"): return base + " The answer must be one of the provided options. Verify correctness."
    elif qt in ("true/false", "truefalse"): return base + " The answer must be either 'True' or 'False'."
    else: return base + " The answer type is unspecified; check for correctness generally."

def extract_json_substring(s: str) -> str:
    start = s.find("{")
    end = s.rfind("}")
    return s[start:end+1] if start != -1 and end != -1 and end > start else s

def call_openai(question: str, answer: str, question_type: str) -> Dict[str, Any]:
    system_prompt = get_system_prompt(question_type)
    prompt = f"Question:\n{question}\n\nAnswer:\n{answer}"
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.65,
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":prompt}],
            max_tokens=1000
        )
        raw = response.choices[0].message.content
        json_text = extract_json_substring(raw)
        try: result = json.loads(json_text)
        except json.JSONDecodeError: result = json5.loads(json_text)
        return result
    except Exception as e:
        return {"valid": False, "reason": f"OpenAI API error: {str(e)}", "corrected_answer": None}

def validate_record(record: Dict[str, Any]) -> Dict[str, Any]:
    lang = "English"
    normalized_record = {normalize_key(k): v for k, v in record.items()}
    for possible_lang_key in FALLBACK_KEYS["language"]:
        if normalize_key(possible_lang_key) in normalized_record:
            lang = normalized_record[normalize_key(possible_lang_key)]
            break

    key_map = get_key_map_for_language(lang)
    mapped = map_record_fields(record, key_map)
    question = mapped.get("question", "")
    answer = mapped.get("answer", "")
    question_type = mapped.get("question_type", "unspecified")

    result = call_openai(question, answer, question_type)
    new_rec = record.copy()
    if result.get("valid", False):
        new_rec["_validation"] = {"valid": True, "reason": result.get("reason")}
    else:
        if result.get("corrected_answer"):
            new_rec[key_map["answer"]] = result["corrected_answer"]
            new_rec["_validation"] = {"valid": False,"reason": result.get("reason"),"corrected": True}
        else:
            new_rec["_validation"] = {"valid": False,"reason": result.get("reason"),"corrected": False}
    return new_rec

def process_records_parallel(records: List[Dict[str, Any]], max_workers: int = 5) -> List[Dict[str, Any]]:
    results = [None]*len(records)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(validate_record, rec): i for i, rec in enumerate(records)}
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()
    return results

def gpt_translate_text(text_record: Dict[str, Any], target_language: str = "English") -> Dict[str, Any]:
    """
    Translate all keys and values of a JSON record to the target language (default English).
    Preserves JSON structure and returns a valid dict.
    """
    # Convert the record to JSON string for GPT prompt
    record_str = json.dumps(text_record, ensure_ascii=False)
    prompt = (
        f"Translate this JSON to {target_language}, converting both keys and values. "
        f"Preserve JSON structure exactly. Return valid JSON only.\n{record_str}"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        raw = response.choices[0].message.content
        json_text = extract_json_substring(raw)
        try:
            translated = json.loads(json_text)
        except json.JSONDecodeError:
            translated = json5.loads(json_text)
        return translated
    except Exception as e:
        # Fallback: return original record if translation fails
        print(f"Translation failed: {e}")
        return text_record

