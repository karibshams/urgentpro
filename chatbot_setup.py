import os
import json
import json5
import ast
import re
from typing import List, Dict, Any
from dotenv import load_dotenv
import openai
import concurrent.futures

# Load env variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o")

# Language-specific system prompts
SYSTEM_PROMPTS = {
    "en": (
        "You are an expert educator and grader in mathematics, physics, and theoretical subjects. "
        "Given a single question and its provided answer, evaluate correctness. "
        "Return valid JSON ONLY, with keys and string values enclosed in double quotes, "
        "in the form: {\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}. "
        "If valid, corrected_answer must be null. "
        "Preserve LaTeX formatting exactly. Respond in English."
    ),
    "zh": (
        "您是数学、物理和理论学科的专家教育者和评分员。"
        "给定一个问题和其提供的答案，评估其正确性。"
        "仅返回有效的JSON格式，键和字符串值用双引号括起来，"
        "格式为：{\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}。"
        "如果有效，corrected_answer必须为null。"
        "准确保留LaTeX格式。请用中文回答。"
    ),
    "es": (
        "Eres un educador experto y calificador en matemáticas, física y materias teóricas. "
        "Dada una pregunta y su respuesta proporcionada, evalúa la corrección. "
        "Devuelve SOLO JSON válido, con claves y valores de cadena entre comillas dobles, "
        "en la forma: {\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}. "
        "Si es válido, corrected_answer debe ser null. "
        "Conserva exactamente el formato LaTeX. Responde en español."
    ),
    "ar": (
        "أنت خبير تعليمي ومقيم في الرياضيات والفيزياء والمواد النظرية. "
        "بناءً على سؤال واحد وإجابته المقدمة، قيم صحتها. "
        "أرجع JSON صالح فقط، مع مفاتيح وقيم نصية محاطة بعلامات اقتباس مزدوجة، "
        "بالشكل: {\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}. "
        "إذا كانت صالحة، فإن corrected_answer يجب أن يكون null. "
        "احتفظ بتنسيق LaTeX بالضبط. أجب باللغة العربية."
    ),
    "hi": (
        "आप गणित, भौतिकी और सैद्धांतिक विषयों के विशेषज्ञ शिक्षक और ग्रेडर हैं। "
        "एक प्रश्न और उसके दिए गए उत्तर को देखते हुए, सही होने का मूल्यांकन करें। "
        "केवल वैध JSON वापस करें, कुंजियों और स्ट्रिंग मानों को दोहरे उद्धरण चिह्नों में संलग्न करके, "
        "इस रूप में: {\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}. "
        "यदि वैध है, तो corrected_answer null होना चाहिए। "
        "LaTeX स्वरूपण को बिल्कुल संरक्षित करें। हिंदी में उत्तर दें।"
    ),
    "ru": (
        "Вы являетесь экспертом-педагогом и оценщиком в области математики, физики и теоретических предметов. "
        "Учитывая вопрос и предоставленный ответ, оцените правильность. "
        "Верните ТОЛЬКО действительный JSON, с ключами и строковыми значениями в двойных кавычках, "
        "в форме: {\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}. "
        "Если действителен, corrected_answer должен быть null. "
        "Точно сохраните форматирование LaTeX. Отвечайте на русском языке."
    ),
    "de": (
        "Sie sind ein Experte und Bewerter in Mathematik, Physik und theoretischen Fächern. "
        "Bewerten Sie bei einer gegebenen Frage und ihrer bereitgestellten Antwort die Korrektheit. "
        "Geben Sie NUR gültiges JSON zurück, mit Schlüsseln und Zeichenkettenwerten in doppelten Anführungszeichen, "
        "in der Form: {\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}. "
        "Wenn gültig, muss corrected_answer null sein. "
        "Bewahren Sie die LaTeX-Formatierung exakt. Antworten Sie auf Deutsch."
    ),
    "fr": (
        "Vous êtes un éducateur expert et évaluateur en mathématiques, physique et matières théoriques. "
        "Étant donné une question et sa réponse fournie, évaluez l'exactitude. "
        "Retournez UNIQUEMENT du JSON valide, avec des clés et des valeurs de chaîne entre guillemets doubles, "
        "sous la forme: {\"valid\": bool, \"reason\": str, \"corrected_answer\": str or null}. "
        "Si valide, corrected_answer doit être null. "
        "Préservez exactement le formatage LaTeX. Répondez en français."
    )
}

def detect_language(data: List[Dict[str, Any]]) -> str:
    """
    Detect language from the JSON data by analyzing text content
    """
    # Combine all text from questions and answers
    text_sample = ""
    for record in data[:3]:  # Check first 3 records for efficiency
        question = record.get("question", "")
        answer = record.get("answer", "")
        text_sample += f"{question} {answer} "
    
    text_sample = text_sample[:500]  # Limit sample size
    
    # Simple language detection patterns
    language_patterns = {
        "zh": r'[\u4e00-\u9fff]',  # Chinese characters
        "ar": r'[\u0600-\u06ff]',  # Arabic characters
        "hi": r'[\u0900-\u097f]',  # Hindi/Devanagari characters
        "ru": r'[\u0400-\u04ff]',  # Cyrillic characters
    }
    
    # Check for non-Latin scripts first
    for lang, pattern in language_patterns.items():
        if re.search(pattern, text_sample):
            return lang
    
    # For Latin-based languages, use keyword detection
    spanish_keywords = ['pregunta', 'respuesta', 'matemáticas', 'física', 'problema']
    german_keywords = ['frage', 'antwort', 'mathematik', 'physik', 'problem']
    french_keywords = ['question', 'réponse', 'mathématiques', 'physique', 'problème']
    
    text_lower = text_sample.lower()
    
    if any(word in text_lower for word in spanish_keywords):
        return "es"
    elif any(word in text_lower for word in german_keywords):
        return "de"
    elif any(word in text_lower for word in french_keywords):
        return "fr"
    
    # Default to English
    return "en"

def extract_json_substring(s: str) -> str:
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start:end+1]
    return s

def call_openai(question: str, answer: str, target_language: str = "en") -> Dict[str, Any]:
    # Get the appropriate system prompt for the target language
    system_prompt = SYSTEM_PROMPTS.get(target_language, SYSTEM_PROMPTS["en"])
    
    prompt = f"Question:\n{question}\n\nAnswer:\n{answer}"
    print(f"Calling OpenAI for question in {target_language}: {question[:50]}...")  # debug
    
    try:
        response = openai.ChatCompletion.create(
            model=MODEL_NAME,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
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
        error_message = f"OpenAI API error: {str(e)}"
        
        # Translate error message if needed
        if target_language != "en":
            error_translations = {
                "zh": f"OpenAI API 错误: {str(e)}",
                "es": f"Error de API de OpenAI: {str(e)}",
                "ar": f"خطأ في API OpenAI: {str(e)}",
                "hi": f"OpenAI API त्रुटि: {str(e)}",
                "ru": f"Ошибка API OpenAI: {str(e)}",
                "de": f"OpenAI API Fehler: {str(e)}",
                "fr": f"Erreur API OpenAI: {str(e)}"
            }
            error_message = error_translations.get(target_language, error_message)
        
        return {"valid": False, "reason": error_message, "corrected_answer": None}


def validate_record(record: Dict[str, Any], target_language: str = "en") -> Dict[str, Any]:
    question = record.get("question", "")
    answer = record.get("answer", "")
    result = call_openai(question, answer, target_language)

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

def process_records_parallel(records: List[Dict[str, Any]], max_workers: int = 5, target_language: str = "en") -> List[Dict[str, Any]]:
    results = [None] * len(records)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(validate_record, rec, target_language): i for i, rec in enumerate(records)}
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()
    return results