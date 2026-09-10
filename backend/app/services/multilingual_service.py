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
    "running": "running",
    "nadakka": "walking",
    "veliye": "outside",
    "veliya": "outside",
    "povoma": "can we go",
    "pogalama": "can we go",
    "kodai": "umbrella",
    "குடை": "umbrella",
    "kaalai": "morning",
    "காலை": "morning",
    "morning": "morning",
    "maalai": "evening",
    "சாயங்காலம்": "evening",
    "sayangalam": "evening",
    "evening": "evening",
    "madhiyam": "afternoon",
    "மதியம்": "afternoon",
    "afternoon": "afternoon",
    "iravu": "night",
    "இரவு": "night",
    "night": "night",
    "weekend": "weekend",
    "indha": "this",
    "இந்த": "this",
    "eppadi": "how",
    "எப்படி": "how",
    "irukkum": "will it be",
    "இருக்கும்": "will it be",
    "function": "outdoor event",
    "நிகழ்ச்சி": "outdoor event",
    "vishesham": "outdoor event",
    "vaikkalama": "can we host",
    "vivasaayam": "farming",
    "விவசாயம்": "farming",
    "spray": "spray",
    "thelikkalama": "spray",
    "marundhu": "spray",
    "meen": "marine activity",
    "மீன்": "marine activity",
    "meenpidikka": "fishing",
    "kadal": "sea",
    "கடல்": "sea",
    "payanam": "travel",
    "பயணம்": "travel",
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
    "running": "running",
    "ghoomne": "travel",
    "safar": "travel",
    "yatra": "travel",
    "bahar": "outside",
    "chata": "umbrella",
    "chaata": "umbrella",
    "छाता": "umbrella",
    "subah": "morning",
    "सुबह": "morning",
    "morning": "morning",
    "shaam": "evening",
    "शाम": "evening",
    "evening": "evening",
    "dopahar": "afternoon",
    "दोपहर": "afternoon",
    "afternoon": "afternoon",
    "raat": "night",
    "रात": "night",
    "night": "night",
    "weekend": "weekend",
    "is": "this",
    "इस": "this",
    "kaisa": "how",
    "कैसा": "how",
    "rahega": "will it be",
    "रहेगा": "will it be",
    "kheti": "farming",
    "खेती": "farming",
    "spray": "spray",
    "chhidkav": "spray",
    "छिड़काव": "spray",
    "fasal": "crops",
    "फसल": "crops",
    "machli": "fishing",
    "मछली": "fishing",
    "samundar": "sea",
    "समुद्र": "sea",
    "event": "outdoor event",
    "function": "outdoor event",
    "karyakram": "outdoor event",
    "कार्यक्रम": "outdoor event",
    "kar": "can",
    "sakta": "can",
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
            if "odalaama" in text.lower() or "ஓடலாமா" in text or "running pogalama" in text.lower():
                normalized += " can I go running"
            if "kodai venuma" in text.lower() or "குடை தேவையா" in text:
                normalized += " should I carry an umbrella"
            if "function vaikkalama" in text.lower() or "நிகழ்ச்சி வைக்கலாமா" in text:
                normalized += " suitable for an outdoor event function"
            if "weather eppadi irukkum" in text.lower() or "வானிலை எப்படி இருக்கும்" in text:
                normalized += " how is the weather"

        elif lang == "hi":
            for k, v in HINDI_KEYWORDS.items():
                normalized = re.sub(rf'\b{k}\b', v, normalized)
            if "barish hogi" in text.lower() or "बारिश होगी" in text:
                normalized += " will it rain"
            if "daudne ja" in text.lower() or "दौड़ने जा" in text or "running kar sakta" in text.lower():
                normalized += " can I go running"
            if "chata chahiye" in text.lower() or "छाता चाहिए" in text:
                normalized += " should I carry an umbrella"
            if "mausam kaisa rahega" in text.lower() or "मौसम कैसा रहेगा" in text:
                normalized += " how is the weather"

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
        risk = r.get("risk", "குறைந்த")

        if key == "current_weather":
            return f"{loc} பகுதியில் தற்போதைய வெப்பநிலை {temp}°C, வானிலை நிலை: {cond}. ஈரப்பதம் {r.get('humidity', 60)}% மற்றும் காற்றின் வேகம் {r.get('wind', 3)} மீ/வி."
        elif key == "rain_yes":
            return f"ஆம், {loc} பகுதியில் {r.get('target', 'நாளை')} மழை பெய்ய வாய்ப்பு {pop}% உள்ளது ({cond}). குடை எடுத்துச் செல்வது நல்லது."
        elif key == "rain_no":
            return f"இல்லை, {loc} பகுதியில் {r.get('target', 'நாளை')} மழை பெய்யும் வாய்ப்பு குறைவு ({pop}%). வானிலை பெரும்பாலும் {cond} ஆக இருக்கும்."
        elif key == "running_advisory":
            return f"{loc} பகுதியில் {r.get('target', 'நாளை')} காலை ஓடுவதற்கான / உடற்பயிற்சிக்கான இடர் நிலை: {risk}. {rec}"
        elif key == "farming_advisory":
            return f"{loc} பகுதி விவசாய ஆலோசனை: இடர் நிலை {risk}. {rec} (வானிலை: {temp}°C, {cond}, மழை வாய்ப்பு: {pop}%)."
        elif key == "marine_advisory":
            return f"{loc} கடல் / மீன்பிடி ஆலோசனை: இடர் நிலை {risk}. {rec} (காற்றின் வேகம்: {r.get('wind', 3)} மீ/வி)."
        elif key == "travel_advisory":
            return f"{loc} பயண ஆலோசனை: இடர் நிலை {risk}. {rec} (வானிலை நிலை: {cond})."
        elif key == "outdoor_event_advisory":
            return f"{loc} பகுதியில் வெளிப்புற நிகழ்ச்சி ஏற்பாடு செய்ய வானிலை நிலை: {risk}. {rec}"
        elif key == "general_advisory":
            return f"{loc} வானிலை ஆலோசனை: {rec} (வெப்பநிலை: {temp}°C, நிலை: {cond})."
        return f"{loc} வானிலை தகவல்: {temp}°C, {cond}."

    def _localize_hindi(self, key: str, r: Dict[str, Any]) -> str:
        loc = r.get("location", "चेन्नई")
        temp = r.get("temp", "30")
        cond = r.get("cond", "साफ मौसम")
        pop = r.get("pop", "0")
        rec = r.get("rec", "")
        risk = r.get("risk", "मध्यम")

        if key == "current_weather":
            return f"{loc} में वर्तमान तापमान {temp}°C है, मौसम की स्थिति: {cond}। आर्द्रता {r.get('humidity', 60)}% और हवा की गति {r.get('wind', 3)} मी/से है।"
        elif key == "rain_yes":
            return f"हाँ, {loc} में {r.get('target', 'कल')} बारिश होने की संभावना {pop}% है ({cond})। छाता साथ रखना उचित रहेगा।"
        elif key == "rain_no":
            return f"नहीं, {loc} में {r.get('target', 'कल')} बारिश की संभावना बहुत कम ({pop}%) है। मौसम मुख्य रूप से {cond} रहेगा।"
        elif key == "running_advisory":
            return f"{loc} में {r.get('target', 'कल')} दौड़ने / व्यायाम के लिए जोखिम स्तर: {risk}। {rec}"
        elif key == "farming_advisory":
            return f"{loc} कृषि परामर्श: जोखिम स्तर {risk}। {rec} (तापमान: {temp}°C, स्थिति: {cond}, बारिश की संभावना: {pop}%)।"
        elif key == "marine_advisory":
            return f"{loc} मत्स्य / समुद्री गतिविधि परामर्श: जोखिम स्तर {risk}। {rec} (हवा की गति: {r.get('wind', 3)} मी/से)।"
        elif key == "travel_advisory":
            return f"{loc} यात्रा परामर्श: जोखिम स्तर {risk}। {rec} (मौसम स्थिति: {cond})।"
        elif key == "outdoor_event_advisory":
            return f"{loc} में आउटडोर इवेंट परामर्श: जोखिम स्तर {risk}। {rec}"
        elif key == "general_advisory":
            return f"{loc} मौसम परामर्श: {rec} (तापमान: {temp}°C, स्थिति: {cond})।"
        return f"{loc} मौसम विवरण: {temp}°C, {cond}।"

    def _localize_english(self, key: str, r: Dict[str, Any]) -> str:
        loc = r.get("location", "Chennai")
        temp = r.get("temp", "30")
        cond = r.get("cond", "Clear")
        pop = r.get("pop", "0")
        rec = r.get("rec", "")
        risk = r.get("risk", "LOW")

        if key == "current_weather":
            return f"Current weather in {loc} is {temp}°C with {cond}. Humidity is {r.get('humidity', 60)}% and wind speed is {r.get('wind', 3)} m/s."
        elif key == "rain_yes":
            return f"Yes, there is a {pop}% probability of rain in {loc} for {r.get('target', 'tomorrow')} ({cond}). Carrying an umbrella is recommended."
        elif key == "rain_no":
            return f"No, precipitation probability is low ({pop}%) in {loc} for {r.get('target', 'tomorrow')}. Expected condition is {cond}."
        elif key == "running_advisory":
            return f"Running/exercise assessment for {loc} ({r.get('target', 'tomorrow')}): Risk is {risk}. {rec}"
        elif key == "farming_advisory":
            return f"Agricultural advisory for {loc} ({r.get('target', 'tomorrow')}): Risk is {risk}. {rec}"
        elif key == "marine_advisory":
            return f"Marine/coastal safety advisory for {loc} ({r.get('target', 'tomorrow')}): Risk is {risk}. {rec}"
        elif key == "travel_advisory":
            return f"Travel safety advisory for {loc} ({r.get('target', 'tomorrow')}): Risk is {risk}. {rec}"
        elif key == "outdoor_event_advisory":
            return f"Outdoor event assessment for {loc} ({r.get('target', 'tomorrow')}): Risk is {risk}. {rec}"
        elif key == "general_advisory":
            return f"Weather decision advisory for {loc}: {rec}"
        return f"Weather information for {loc}: {temp}°C, {cond}."


multilingual_service = MultilingualService()
