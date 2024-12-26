import logging
from flask import Flask, render_template, request, redirect, url_for, session
import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    filename='weather_app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()
api_key = os.getenv('OPENWEATHER')

app = Flask(__name__)
app.secret_key = 'math_racer'  # Replace with a secure secret key

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/weather', methods=['POST'])
def get_weather():
    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    if not lat or not lon:
        return render_template('index.html', error='Invalid coordinates.')

    # Fetch forecast data (includes current and forecast weather)
    forecast_url = 'http://api.openweathermap.org/data/2.5/forecast'
    forecast_params = {
        'lat': lat,
        'lon': lon,
        'appid': api_key,
        'units': 'metric'
    }
    forecast_response = requests.get(forecast_url, params=forecast_params)

    if forecast_response.status_code != 200:
        return render_template('index.html', error='Failed to fetch weather data.')

    forecast_data = forecast_response.json()

    # Process data
    try:
        # Extract the current weather from the first entry in the forecast list
        current_weather_entry = forecast_data['list'][0]
        current_time = datetime.fromtimestamp(current_weather_entry['dt']).strftime('%H:%M:%S')
        current_date = datetime.fromtimestamp(current_weather_entry['dt']).strftime('%Y-%m-%d')
        current_day = datetime.fromtimestamp(current_weather_entry['dt']).strftime('%A')
        location = forecast_data.get('city', {}).get('name', 'Unknown')

        sun_rise = datetime.fromtimestamp(forecast_data['city']['sunrise']).strftime('%H:%M:%S')
        sun_set = datetime.fromtimestamp(forecast_data['city']['sunset']).strftime('%H:%M:%S')
        # print(sun_rise, sun_set)

        weather = {
            'time': current_time,
            'date': current_date,
            'day': current_day,
            'location': location,
            'icon': current_weather_entry['weather'][0]['icon'] if 'weather' in current_weather_entry else '',
            'description': current_weather_entry['weather'][0]['description'].title() if 'weather' in current_weather_entry else 'N/A',
            'temp': current_weather_entry['main']['temp'],
            'feels_like': current_weather_entry['main']['feels_like'],
            'sunrise': sun_rise,
            'sunset': sun_set,
        }

        # Log weather information
        logging.info(
            f"Weather lookup - Coordinates: ({lat}, {lon}), Temperature: {weather['temp']}°C, Description: {weather['description']}"
        )

        # Process the next 4 days' forecasts
        forecasts = {}
        current_date_obj = datetime.now()
        for entry in forecast_data.get('list', []):
            forecast_time = datetime.fromtimestamp(entry['dt'])
            forecast_date = forecast_time.date()

            if forecast_date > current_date_obj.date() and forecast_date not in forecasts:
                # Select the forecast closest to 12:00 PM
                target_time = datetime.combine(forecast_date, datetime.min.time()) + timedelta(hours=12)
                time_diff = abs((forecast_time - target_time).total_seconds())
                if 'closest' not in forecasts or time_diff < forecasts['closest'][0]:
                    forecasts[forecast_date] = {
                        'day': forecast_time.strftime('%A'),
                        'icon': entry['weather'][0]['icon'] if 'weather' in entry else '',
                        'description': entry['weather'][0]['description'].title() if 'weather' in entry else 'N/A',
                        'temp': entry['main']['temp']
                    }
                    forecasts['closest'] = (time_diff, forecast_time)

            if len(forecasts) - 1 >= 4:
                break

        # Remove the 'closest' key used for tracking
        forecasts.pop('closest', None)

        # Get the next 4 days
        forecast_list = list(forecasts.values())[:4]
    except (TypeError, ValueError, KeyError):
        return render_template('index.html', error='Error processing weather data.')

    # Store weather data in session
    session['weather'] = weather
    session['forecast'] = forecast_list

    return redirect(url_for('weather_result'))

@app.route('/weather_result', methods=['GET'])
def weather_result():
    weather = session.get('weather')
    forecast = session.get('forecast')

    if not weather or not forecast:
        return redirect(url_for('index'))

    return render_template('weather.html', weather=weather, forecast=forecast)

if __name__ == '__main__':
    app.run(debug=True)