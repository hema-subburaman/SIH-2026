from typing import Dict, Any, Tuple
import re

# Comprehensive phrase patterns and keywords for Tamil, Hindi, and English
TAMIL_KEYWORDS = {
    "mazha": "rain",
    "mazhai": "rain",
    "மழை": "rain",
    "veiyil": "sun",
    "veyil": "sun",
    "வெயில்": "sun",
    "kaathu": "wind",
    "kaatru": "wind",
    "காற்று": "wind",
    "kulir": "cold",
    "குளிர்": "cold",
    "naalaikku": "tomorrow",
    "nalaiku": "tomorrow",
    "நாளை": "tomorrow",
    "innikku": "today",
    "inru": "today",
    "இன்று": "today",
    "varuma": "will it come",
    "varum": "will come",
    "odalaama": "can I run",
    "ooda": "running",
    "nadakka": "walking",
    "veliye": "outside",
    "povoma": "can we go",
    "kodai": "umbrella",
    "குடை": "umbrella",
}

HINDI_KEYWORDS = {
    "barish": "rain",
    "baarish": "rain",
    "बारिश": "rain",
    "dhup": "sun",
    "dhoop": "sun",
    "धूप": "sun",
    "hawa": "wind",
    "हवा": "wind",
    "thand": "cold",
    "ठंड": "cold",
    "garmi": "heat",
    "गर्मी": "heat",
    "kal": "tomorrow",
    "कल": "tomorrow",
    "aaj": "today",
    "आज": "today",
    "hogi": "will it happen",
    "hoga": "will it happen",
    "daud": "running",
    "doud": "running",
    "daudna": "running",
    "daudne": "running",
    "ghoomne": "travel",
    "bahar": "outside",
    "chata": "umbrella",
    "chaata": "umbrella",
    "छाता": "umbrella",
}


class MultilingualService:
    """
    Multilingual Intelligence Service for Indian Languages.
    Supports English, Tamil (தமிழ்), and Hindi (हिन्दी).
    Performs script & phonetic language detection, query translation, and localized response synthesis.
    """

    def detect_language(self, text: str) -> str:
        """Detects whether text is in Tamil, Hindi, or English (handles native script and Romanized phonetics)."""
        # 1. Unicode script detection
        # Tamil Unicode Block: U+0B80 to U+0BFF
        if re.search(r'[\u0B80-\u0BFF]', text):
            return "ta"
        
        # Devanagari (Hindi) Unicode Block: U+0900 to U+097F
        if re.search(r'[\u0900-\u097F]', text):
            return "hi"

        # 2. Romanized transliteration keyword scoring
        lower = text.lower()
        words = re.findall(r'\b\w+\b', lower)

        ta_score = sum(1 for w in words if w in TAMIL_KEYWORDS)
        hi_score = sum(1 for w in words if w in HINDI_KEYWORDS)

        if ta_score > hi_score and ta_score > 0:
            return "ta"
        if hi_score > ta_score and hi_score > 0:
            return "hi"

        return "en"

    def translate_to_english_intent(self, text: str, lang: str) -> str:
        """Normalizes Romanized or native Tamil/Hindi queries into English semantic representations."""
        if lang == "en":
            return text

        normalized = text.lower()
        
        if lang == "ta":
            for k, v in TAMIL_KEYWORDS.items():
                normalized = re.sub(rf'\b{k}\b', v, normalized)
            # Standard Tamil phonetic phrases
            if "mazha varuma" in text.lower() or "மழை வருமா" in text:
                normalized += " will it rain tomorrow"
            if "odalaama" in text.lower() or "ஓடலாமா" in text:
                normalized += " can I go running"
            if "kodai venuma" in text.lower() or "குடை தேவையா" in text:
                normalized += " should I carry an umbrella"

        elif lang == "hi":
            for k, v in HINDI_KEYWORDS.items():
                normalized = re.sub(rf'\b{k}\b', v, normalized)
            if "barish hogi" in text.lower() or "बारिश होगी" in text:
                normalized += " will it rain"
            if "daudne ja" in text.lower() or "दौड़ने जा" in text:
                normalized += " can I go running"
            if "chata chahiye" in text.lower() or "छाता चाहिए" in text:
                normalized += " should I carry an umbrella"

        return normalized

    def localize_response(
        self,
        lang: str,
        template_key: str,
        replacements: Dict[str, Any]
    ) -> str:
        """Generates natural language response in target language."""
        if lang == "ta":
            return self._localize_tamil(template_key, replacements)
        elif lang == "hi":
            return self._localize_hindi(template_key, replacements)
        else:
            return self._localize_english(template_key, replacements)

    def _localize_tamil(self, key: str, r: Dict[str, Any]) -> str:
        loc = r.get("location", "சென்னை")
        temp = r.get("temp", "30")
        cond = r.get("cond", "தெளிவான வானிலை")
        pop = r.get("pop", "0")
        rec = r.get("rec", "")

        if key == "current_weather":
            return f"{loc} பகுதியில் தற்போதைய வெப்பநிலை {temp}°C, வானிலை நிலை: {cond}. ஈரப்பதம் {r.get('humidity', 60)}% மற்றும் காற்றின் வேகம் {r.get('wind', 3)} மீ/வி."
        elif key == "rain_yes":
            return f"ஆம், {loc} பகுதியில் {r.get('target', 'நாளை')} மழை பெய்ய வாய்ப்பு {pop}% உள்ளது ({cond}). குடை எடுத்துச் செல்வது நல்லது."
        elif key == "rain_no":
            return f"இல்லை, {loc} பகுதியில் {r.get('target', 'நாளை')} மழை பெய்யும் வாய்ப்பு குறைவு ({pop}%). வானிலை பெரும்பாலும் {cond} ஆக இருக்கும்."
        elif key == "running_advisory":
            risk = r.get("risk", "குறைந்த")
            return f"{loc} பகுதியில் உடற்பயிற்சி / ஓடுவதற்கு ஆபத்து நிலை: {risk}. {rec}"
        elif key == "general_advisory":
            return f"{loc} வானிலை ஆலோசனை: {rec} (வெப்பநிலை: {temp}°C, நிலை: {cond})."
        return f"{loc} வானிலை தகவல்: {temp}°C, {cond}."

    def _localize_hindi(self, key: str, r: Dict[str, Any]) -> str:
        loc = r.get("location", "चेन्नई")
        temp = r.get("temp", "30")
        cond = r.get("cond", "साफ मौसम")
        pop = r.get("pop", "0")
        rec = r.get("rec", "")

        if key == "current_weather":
            return f"{loc} में वर्तमान तापमान {temp}°C है, मौसम की स्थिति: {cond}। आर्द्रता {r.get('humidity', 60)}% और हवा की गति {r.get('wind', 3)} मी/से है।"
        elif key == "rain_yes":
            return f"हाँ, {loc} में {r.get('target', 'कल')} बारिश होने की संभावना {pop}% है ({cond})। छाता साथ रखना उचित रहेगा।"
        elif key == "rain_no":
            return f"नहीं, {loc} में {r.get('target', 'कल')} बारिश की संभावना बहुत कम ({pop}%) है। मौसम मुख्य रूप से {cond} रहेगा।"
        elif key == "running_advisory":
            risk = r.get("risk", "मध्यम")
            return f"{loc} में दौड़ने / व्यायाम के लिए जोखिम स्तर: {risk}। {rec}"
        elif key == "general_advisory":
            return f"{loc} मौसम परामर्श: {rec} (तापमान: {temp}°C, स्थिति: {cond})।"
        return f"{loc} मौसम विवरण: {temp}°C, {cond}।"

    def _localize_english(self, key: str, r: Dict[str, Any]) -> str:
        loc = r.get("location", "Chennai")
        temp = r.get("temp", "30")
        cond = r.get("cond", "Clear")
        pop = r.get("pop", "0")
        rec = r.get("rec", "")

        if key == "current_weather":
            return f"Current weather in {loc} is {temp}°C with {cond}. Humidity is {r.get('humidity', 60)}% and wind speed is {r.get('wind', 3)} m/s."
        elif key == "rain_yes":
            return f"Yes, there is a {pop}% probability of rain in {loc} for {r.get('target', 'tomorrow')} ({cond}). Carrying an umbrella is recommended."
        elif key == "rain_no":
            return f"No, precipitation probability is low ({pop}%) in {loc} for {r.get('target', 'tomorrow')}. Expected condition is {cond}."
        elif key == "running_advisory":
            return f"Outdoor activity assessment for {loc}: Risk is {r.get('risk', 'LOW')}. {rec}"
        elif key == "general_advisory":
            return f"Weather decision advisory for {loc}: {rec}"
        return f"Weather information for {loc}: {temp}°C, {cond}."


multilingual_service = MultilingualService()
