from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

API_KEY = "bd5e378503939ddaee76f12ad7a97608"
BASE = "https://api.openweathermap.org/data/2.5"

def wind_dir(deg):
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[round(deg / 45) % 8]

def get_weather_data(city):
    try:
        w = requests.get(f"{BASE}/weather", params={
            "q": city, "appid": API_KEY, "units": "metric"
        }).json()

        if w.get("cod") != 200:
            return None, w.get("message", "City not found")

        f = requests.get(f"{BASE}/forecast", params={
            "q": city, "appid": API_KEY, "units": "metric", "cnt": 40
        }).json()

        lat, lon = w["coord"]["lat"], w["coord"]["lon"]
        aqi_resp = requests.get(f"{BASE}/air_pollution", params={
            "lat": lat, "lon": lon, "appid": API_KEY
        }).json()

        aqi = aqi_resp["list"][0]["main"]["aqi"] if aqi_resp.get("list") else None
        aqi_labels = {1:"Good", 2:"Fair", 3:"Moderate", 4:"Poor", 5:"Very Poor"}
        aqi_colors = {1:"#34a853", 2:"#93c47d", 3:"#fbbc04", 4:"#ea8600", 5:"#d93025"}

        now = datetime.now()
        sunrise_dt = datetime.fromtimestamp(w["sys"]["sunrise"])
        sunset_dt  = datetime.fromtimestamp(w["sys"]["sunset"])

        daily = {}
        for item in f.get("list", []):
            day = datetime.fromtimestamp(item["dt"]).strftime("%A")
            date_str = datetime.fromtimestamp(item["dt"]).strftime("%b %d")
            if day not in daily:
                daily[day] = {
                    "day": day,
                    "date": date_str,
                    "hi": item["main"]["temp_max"],
                    "lo": item["main"]["temp_min"],
                    "code": item["weather"][0]["id"],
                    "desc": item["weather"][0]["description"],
                    "pop": item.get("pop", 0)
                }
            else:
                daily[day]["hi"] = max(daily[day]["hi"], item["main"]["temp_max"])
                daily[day]["lo"] = min(daily[day]["lo"], item["main"]["temp_min"])

        hourly = []
        for item in f.get("list", [])[:8]:
            dt = datetime.fromtimestamp(item["dt"])
            hourly.append({
                "time": dt.strftime("%I %p").lstrip("0"),
                "temp": round(item["main"]["temp"]),
                "code": item["weather"][0]["id"],
                "pop": round(item.get("pop", 0) * 100),
                "wind": round(item["wind"]["speed"] * 3.6, 1)
            })

        rain_1h = w.get("rain", {}).get("1h", 0)
        is_day = sunrise_dt <= now <= sunset_dt

        result = {
            "city": w["name"],
            "country": w["sys"]["country"],
            "temp": round(w["main"]["temp"]),
            "feels_like": round(w["main"]["feels_like"]),
            "temp_max": round(w["main"]["temp_max"]),
            "temp_min": round(w["main"]["temp_min"]),
            "desc": w["weather"][0]["description"].title(),
            "code": w["weather"][0]["id"],
            "humidity": w["main"]["humidity"],
            "pressure": w["main"]["pressure"],
            "wind_speed": round(w["wind"]["speed"] * 3.6, 1),
            "wind_gust": round(w["wind"].get("gust", w["wind"]["speed"]) * 3.6, 1),
            "wind_dir": wind_dir(w["wind"].get("deg", 0)),
            "visibility": round(w.get("visibility", 10000) / 1000, 1),
            "clouds": w["clouds"]["all"],
            "rain_1h": rain_1h,
            "dew_point": round(w["main"]["temp"] - (100 - w["main"]["humidity"]) / 5),
            "sunrise": sunrise_dt.strftime("%I:%M %p"),
            "sunset": sunset_dt.strftime("%I:%M %p"),
            "daylight": round((w["sys"]["sunset"] - w["sys"]["sunrise"]) / 3600, 1),
            "is_day": is_day,
            "lat": lat,
            "lon": lon,
            "timezone_offset": w["timezone"] // 3600,
            "aqi": aqi,
            "aqi_label": aqi_labels.get(aqi, "N/A"),
            "aqi_color": aqi_colors.get(aqi, "#888"),
            "pm25": round(aqi_resp["list"][0]["components"].get("pm2_5", 0), 1) if aqi_resp.get("list") else 0,
            "hourly": hourly,
            "forecast": list(daily.values())[:5],
            "updated": now.strftime("%I:%M %p")
        }
        return result, None
    except Exception as e:
        return None, str(e)

@app.route("/api/weather")
def weather():
    city = request.args.get("city", "Delhi")
    data, error = get_weather_data(city)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(data)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
