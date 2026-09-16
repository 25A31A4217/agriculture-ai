from flask import Flask, render_template, request
import pickle
import math
import os
import requests
from googletrans import Translator 

translator = Translator()

app = Flask(__name__)

# ==================================================
# UPLOAD FOLDER
# ==================================================

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ==================================================
# LOAD CROP MODEL
# ==================================================

with open("crop_model.pkl", "rb") as file:
    model = pickle.load(file)


# ==================================================
# CROP PREDICTION
# ==================================================

def predict_crop(values):

    distances = []

    for row in model["data"]:

        features = row[:6]
        crop = row[6]

        distance = math.sqrt(
            sum(
                (values[i] - features[i]) ** 2
                for i in range(6)
            )
        )

        distances.append((distance, crop))

    distances.sort()

    nearest = distances[:model["k"]]

    counts = {}

    for _, crop in nearest:
        counts[crop] = counts.get(crop, 0) + 1

    return max(counts, key=counts.get)


# ==================================================
# IRRIGATION ADVICE
# ==================================================

def irrigation_advice(rainfall):

    if rainfall < 10:

        return (
            "Low rainfall. Check soil moisture; "
            "irrigation may be needed."
        )

    elif rainfall < 30:

        return (
            "Moderate rainfall. Check soil moisture "
            "before irrigating."
        )

    else:

        return (
            "High recent rainfall. Extra irrigation "
            "may not be needed."
        )


# ==================================================
# FERTILIZER ADVICE
# ==================================================

def fertilizer_advice(n, p, k):

    low = []

    if n < 50:
        low.append("Nitrogen")

    if p < 40:
        low.append("Phosphorus")

    if k < 35:
        low.append("Potassium")

    if not low:

        return (
            "N, P and K are within the prototype's "
            "reference ranges. Use a soil test before "
            "applying fertilizer."
        )

    return (
        "The prototype flags: "
        + ", ".join(low)
        + ". Consider a soil test and follow local "
          "agricultural guidance before applying fertilizer."
    )


# ==================================================
# CROP CARE
# ==================================================

def crop_care(crop):

    advice = {

        "Rice":
            "Monitor water levels, weeds and crop "
            "health regularly.",

        "Wheat":
            "Monitor soil moisture and inspect leaves "
            "for disease symptoms.",

        "Maize":
            "Monitor moisture around root zones and "
            "inspect leaves for pest or disease symptoms.",

        "Cotton":
            "Monitor moisture, pests and leaf condition "
            "throughout the crop cycle."
    }

    return advice.get(
        crop,
        "Monitor soil moisture, crop growth and "
        "pest/disease symptoms."
    )


# ==================================================
# PLANT DISEASE / SYMPTOM GUIDANCE
# ==================================================

def disease_guidance(symptom):

    guidance = {

        "yellow":
            "Yellowing can have several causes, including "
            "nutrient stress, water stress or disease. "
            "Check roots, soil moisture and consult a "
            "local agriculture expert.",

        "spots":
            "Leaf spots can be caused by fungal, bacterial "
            "or other problems. Avoid guessing from symptoms "
            "alone; compare with an agricultural extension "
            "guide or expert diagnosis.",

        "wilting":
            "Wilting may be related to water stress, "
            "root problems, heat or disease. Check soil "
            "moisture and roots and seek local advice "
            "if it persists.",

        "powder":
            "A white or powdery appearance can be associated "
            "with some fungal diseases. Obtain a local "
            "diagnosis before treatment.",

        "holes":
            "Leaf holes can be caused by insects or other "
            "damage. Inspect the underside of leaves for "
            "pests and use locally approved control methods "
            "if confirmed."
    }

    return guidance.get(
        symptom,
        "Select a symptom for educational guidance."
    )


# ==================================================
# WEATHER FUNCTION
# ==================================================

def get_weather(city):

    geo_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
    )

    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
    )

    # Find city

    geo = requests.get(
        geo_url,
        params={
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        },
        timeout=10
    )

    geo.raise_for_status()

    results = geo.json().get("results", [])

    if not results:

        raise ValueError("City not found.")

    place = results[0]

    latitude = place["latitude"]
    longitude = place["longitude"]

    # Get weather

    weather = requests.get(
        weather_url,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current":
                "temperature_2m,"
                "relative_humidity_2m,"
                "precipitation",

            "daily":
                "precipitation_sum,"
                "temperature_2m_max,"
                "temperature_2m_min",

            "forecast_days": 3,

            "timezone": "auto"
        },
        timeout=10
    )

    weather.raise_for_status()

    data = weather.json()

    current = data["current"]

    daily = data["daily"]

    next3_rain = sum(
        daily.get("precipitation_sum", []) or []
    )

    return {

        "place":
            f'{place["name"]}, '
            f'{place.get("country", "")}',

        "temperature":
            current["temperature_2m"],

        "humidity":
            current["relative_humidity_2m"],

        "precipitation":
            current["precipitation"],

        "next3_rain":
            next3_rain
    }


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/", methods=["GET", "POST"])
def home():
    
    lang = request.form.get("lang", "en")
    
    return render_template("index.html", lang=lang)


# ==================================================
# CROP RECOMMENDATION
# ==================================================

@app.route("/recommend", methods=["POST"])
def recommend():

    try:

        temperature = float(
            request.form["temperature"]
        )

        humidity = float(
            request.form["humidity"]
        )

        ph = float(
            request.form["ph"]
        )

        nitrogen = float(
            request.form["nitrogen"]
        )

        phosphorus = float(
            request.form["phosphorus"]
        )

        potassium = float(
            request.form["potassium"]
        )

        rainfall = float(
            request.form["rainfall"]
        )

        # Model input order:
        # N, P, K, Temperature, Humidity, pH

        values = [
            nitrogen,
            phosphorus,
            potassium,
            temperature,
            humidity,
            ph
        ]

        crop = predict_crop(values)

        return render_template(

            "result.html",

            crop=crop,

            temperature=temperature,

            humidity=humidity,

            ph=ph,

            nitrogen=nitrogen,

            phosphorus=phosphorus,

            potassium=potassium,

            rainfall=rainfall,

            irrigation=
                irrigation_advice(rainfall),

            fertilizer=
                fertilizer_advice(
                    nitrogen,
                    phosphorus,
                    potassium
                ),

            crop_advice=
                crop_care(crop)
        )

    except (ValueError, KeyError):

        return render_template(
            "index.html",
            error="Please enter valid numeric values."
        )


# ==================================================
# WEATHER
# ==================================================

@app.route("/weather", methods=["POST"])
def weather():
    city = request.form.get("city")
    lang = request.form.get("lang", "en")
    
    # OpenWeatherMap డెమో API కీ (ప్రాజెక్ట్ టెస్టింగ్ కోసం ఇది పనిచేస్తుంది)
    api_key = "b6907d289e10d714a6e88b30761fae22" 
    url = f"http://openweathermap.org{city}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url).json()
        temp = response["main"]["temp"]
        humidity = response["main"]["humidity"]
        desc = response["weather"]["description"]
        
        if lang == "te":
            weather_report = f"{city} లో ఉష్ణోగ్రత: {temp}°C, తేమ: {humidity}%, వాతావరణం: {desc}"
        else:
            weather_report = f"Weather in {city}: Temperature: {temp}°C, Humidity: {humidity}%, Description: {desc}"
    except:
        if lang == "te":
            weather_report = "నగరం పేరు కనుగొనబడలేదు లేదా నెట్‌వర్క్ ఎర్రర్ వచ్చింది."
        else:
            weather_report = "City not found or API error occurred."
            
    return render_template("index.html", weather_text=weather_report, lang=lang)

    try:

        data = get_weather(city)

        return render_template(
            "index.html",
            weather=data
        )

    except Exception:

        return render_template(
            "index.html",
            weather_error=(
                "Could not get weather. "
                "Check the city name and internet connection."
            )
        )


# ==================================================
# PLANT HEALTH
# ==================================================

@app.route('/disease', methods=['GET', 'POST'])
def disease():
    if request.method == 'POST':
        symptom = request.form.get('symptom')
        lang = request.form.get('lang', 'en')
        
        # కింద ఉన్న ఇఫ్-ఎల్స్ కండిషన్ల ప్రకారం రిజల్ట్ వస్తుంది
        result = disease_guidance(symptom)
        
        if lang == "te":
            # ఒకవేళ భాష తెలుగు అయితే తెలుగు గైడెన్స్ ఇక్కడ మారుతుంది
            pass # (మీ పాత ఇఫ్ కండిషన్స్ ఏవైనా ఉంటే ఇక్కడ ఉంచండి)
            
        return render_template('disease.html', result=result, lang=lang)
        
    # వెబ్‌సైట్ లింక్ క్లిక్ చేసి (GET ద్వారా) వస్తే, కింద ఉన్న ఈ ఒక్క లైన్ చాలు
    return render_template('disease.html')
    
    # కింద వెబ్‌సైట్ లింక్ క్లిక్ చేసి (GET ద్వారా) వస్తే, ఈ లైన్ ఖాళీ పేజీని ఓపెన్ చేస్తుంది
    return render_template('disease.html')
    symptom = request.form.get("symptom")
    lang = request.form.get("lang", "en")
    
    # పైన మనం రాసిన ఫంక్షన్ నుండి ఇంగ్లీష్ ఆన్సర్ వస్తుంది
    result = disease_guidance(symptom)
    
    # ఒకవేళ రైతు తెలుగు సెలెక్ట్ చేసి ఉంటే, ఆన్సర్ ని తెలుగులోకి మార్చడం
    if lang == "te":
        if symptom == "Yellow leaves":
            result = "నైట్రోజన్ లోపం కావచ్చు. యూరియా ఎరువును పొలానికి వాడండి."
        elif symptom == "Brown spots":
            result = "శిలీంద్ర తెగులు (Fungal Infection). కాపర్ ఆక్సిక్లోరైడ్ మందును ఆకులపై చల్లండి."
        elif symptom == "White powdery patches":
            result = "బూజు తెగులు (Powdery Mildew). నీటిలో కరిగే గంధకం (Sulfur) వాడండి."
        elif symptom == "Wilting stem":
            result = "వేరు కుళ్ళు తెగులు కావచ్చు. తగినంత నీరు అందించి, కార్బండిజం ఉపయోగించండి."

    return render_template("disease.html", result=result, lang=lang)

@app.route("/predict_fertilizer", methods=["POST"])
def predict_fertilizer():
    nitrogen = float(request.form.get("nitrogen"))
    phosphorous = float(request.form.get("phosphorous"))
    potassium = float(request.form.get("potassium"))
    
    if nitrogen > 50:
       fertilizer_result = "Urea (High Nitrogen needed)"
    elif phosphorous > 50:
       fertilizer_result = "DAP (Diammonium Phosphate)"
    else:
       fertilizer_result = "NPK Complex Fertilizer (Balanced)" 
    
    translated = translator.translate(fertilizer_result, src='en', dest='te')
    telugu_result = translated.text

    return render_template(
        "index.html", 
        prediction_text=f"Recommended Fertilizer: {fertilizer_result}",
        prediction_telugu=f"సిఫార్సు చేసిన ఎరువు: {telugu_result}"
    )
    return render_template("index.html", prediction_text=f"Recommended Fertilizer: {fertilizer_result}" ) 
        
# ==================================================
# FARMER ASSISTANT
# ==================================================

app.route("/chat", methods=["POST"])
def chat():
    message = request.form.get(
        "message",
        ""
    ).lower().strip()


    # -------------------------------
    # WATER / IRRIGATION
    # -------------------------------

    if (
        "water" in message
        or "irrigation" in message
    ):

        answer = (
            "💧 Irrigation Advice: "
            "Check the soil moisture before watering. "
            "If there has been enough recent rainfall, "
            "extra irrigation may not be needed."
        )


    # -------------------------------
    # FERTILIZER
    # -------------------------------

    elif "fertilizer" in message:

        answer = (
            "🧪 Fertilizer Advice: "
            "Fertilizer requirements depend on soil "
            "nutrients. A soil test is recommended "
            "before applying fertilizer."
        )

        answer = (
            "🌾 Rice Advice: "
            "Monitor water levels, weeds and crop "
            "health regularly."
        )


    # -------------------------------
    # MAIZE
    # -------------------------------

    elif "maize" in message:

        answer = (
            "🌽 Maize Advice: "
            "Monitor soil moisture and check the "
            "leaves regularly for pests or disease "
            "symptoms."
        )


    # -------------------------------
    # WHEAT
    # -------------------------------

    elif "wheat" in message:

        answer = (
            "🌾 Wheat Advice: "
            "Monitor soil moisture and inspect the "
            "leaves regularly for disease symptoms."
        )


    # -------------------------------
    # COTTON
    # -------------------------------

    elif "cotton" in message:

        answer = (
            "🌱 Cotton Advice: "
            "Monitor soil moisture, pests and leaf "
            "condition regularly."
        )


    # -------------------------------
    # WEATHER
    # -------------------------------

    elif "weather" in message:

        answer = (
            "🌦️ Weather Advice: "
            "Use the Live Weather section and enter "
            "your city to check current weather."
        )


    # -------------------------------
    # DISEASE
    # -------------------------------

    elif (
        "disease" in message
        or "leaf" in message
        or "leaves" in message
    ):

        answer = (
            "🍃 Plant Health Advice: "
            "Describe the visible symptom or use "
            "the Plant Health Assistant. A visible "
            "symptom alone cannot confirm a disease."
        )


    # -------------------------------
    # GREETING
    # -------------------------------

    elif (
        "hello" in message
        or "hi" in message
        or "hey" in message
    ):

        answer = (
            "🤖 Hello Farmer! 🌱 "
            "I can help with crop recommendation, "
            "irrigation, fertilizer, weather and "
            "plant health."
        )


    # -------------------------------
    # DEFAULT
    # -------------------------------

    else:

        answer = (
            "🤖 I can help with:\n"
            "🌱 Crop recommendation\n"
            "💧 Irrigation\n"
            "🧪 Fertilizer guidance\n"
            "🌦️ Weather\n"
            "🍃 Plant health"
        )


    return render_template(
        "index.html",
        chat_answer=answer
    )


# ==================================================
# RUN APPLICATION
# ==================================================

@app.route("/chat", methods=["POST"])
def chat():
    # Fetch values from form
    user_message = request.form.get("message", "").lower()
    lang = request.form.get("lang", "en")
    
    # Simple logic
    if "irrigate" in user_message or "water" in user_message or "నీరు" in user_message:
        if lang == "te":
            reply = "మీ నేల తేమను బట్టి ఉదయం లేదా సాయంత్రం వేళల్లో నీరు పెట్టడం మంచిది."
        else:
            reply = "It is best to irrigate in the early morning or evening based on soil moisture."
            
    elif "fertilizer" in user_message or "manure" in user_message or "ఎరువు" in user_message:
        if lang == "te":
            reply = "పంట నాటిన 2-3 వారాల తర్వాత మొదటి విడతగా నైట్రోజన్ ఎరువులను వేయడం మంచిది."
        else:
            reply = "It is recommended to apply the first dose of nitrogen fertilizer 2-3 weeks after planting."
            
    else:
        if lang == "te":
            reply = "క్షమించండి, మీ ప్రశ్నకు సరైన సమాధానం కనుగొనలేకపోయాము. దయచేసి నీటి పారుదల లేదా ఎరువుల గురించి అడగండి."
        else:
            reply = "Sorry, I couldn't find a specific answer to that. Please ask about irrigation or fertilizers."

    return render_template("index.html", response=reply, lang=lang)

@app.route("/weather", methods=["POST"])
def  weather_predict():
    city = request.form.get("city")
    lang = request.form.get("lang", "en")
    
    # OpenWeatherMap API key (టెస్టింగ్ కోసం ఒక డెమో API కీ లేదా మీ కీ వాడండి)
    api_key = "YOUR_API_KEY_HERE" 
    url = f"http://openweathermap.org{city}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url).json()
        temp = response["main"]["temp"]
        humidity = response["main"]["humidity"]
        desc = response["weather"][0]["description"]
        
        if lang == "te":
            weather_report = f"{city} లో ఉష్ణోగ్రత: {temp}°C, తేమ: {humidity}%, వాతావరణం: {desc}"
        else:
            weather_report = f"Weather in {city}: Temperature: {temp}°C, Humidity: {humidity}%, Description: {desc}"
    except:
        if lang == "te":
            weather_report = "నగరం పేరు కనుగొనబడలేదు లేదా API ఎర్రర్ వచ్చింది."
        else:
            weather_report = "City not found or API error occurred."
            
    return render_template("index.html", weather_text=weather_report, lang=lang)
if __name__ == "__main__":
    app.run(debug=True)
   