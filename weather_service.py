"""Weather service for fetching current weather conditions from Open-Meteo API."""

import logging
import random
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class WeatherService:
    """Service to fetch weather data from Open-Meteo."""

    # WMO Weather interpretation codes (WW)
    # https://open-meteo.com/en/docs
    WEATHER_CODES: Dict[int, str] = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }

    def __init__(self) -> None:
        """Initialize the weather service."""
        self.base_url: str = "https://api.open-meteo.com/v1/forecast"

    def get_current_weather(self, lat: float, lon: float) -> Optional[Dict[str, str]]:
        """
        Get current weather for the given coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dictionary with weather description and temperature, or None if failed.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code",
            "timezone": "auto"
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            current = data.get("current", {})
            weather_code = current.get("weather_code")
            temp = current.get("temperature_2m")
            
            description = self.WEATHER_CODES.get(weather_code, "Unknown")
            
            return {
                "condition": description,
                "temperature": f"{temp}°C",
                "code": weather_code
            }
            
        except Exception as e:
            logger.warning(f"Error fetching weather: {e}")
            return None

    def get_weather_prompt_modifier(self, weather_data: Dict[str, str]) -> str:
        """
        Get a string modifier for the art prompt based on weather.
        Randomly selects from multiple options for variety.
        """
        if not weather_data:
            return ""

        condition = weather_data["condition"].lower()
        code = weather_data.get("code", -1)

        # Map conditions to lists of artistic moods/elements for variety
        clear_modifiers: List[str] = [
            "bathed in warm sunlight, clear blue skies, natural lighting",
            "warm golden sunlight, crisp clear day, long soft shadows",
            "gentle sunshine, pale blue sky, luminous atmosphere",
            "dappled sunlight, bright and airy, peaceful mood",
            "sun-lit scene, gentle contrasts, natural colours",
        ]

        cloudy_modifiers: List[str] = [
            "soft diffused lighting, dramatic cloudy sky, atmospheric mood",
            "overcast sky, gentle even lighting, contemplative mood",
            "brooding clouds, muted tones, peaceful grey light",
            "silvery cloud cover, soft shadows, tranquil atmosphere",
            "layered clouds, filtered light, subtle colour palette",
        ]

        fog_modifiers: List[str] = [
            "misty atmosphere, ethereal fog, mysterious mood, soft edges",
            "thick morning mist, shapes emerging from haze, dreamlike quality",
            "veiled in fog, muted distant forms, intimate foreground",
            "swirling mist, ghostly atmosphere, limited visibility adding mystery",
            "soft foggy glow, silhouettes fading into grey, hushed mood",
        ]

        rain_modifiers: List[str] = [
            "rainy atmosphere, wet surfaces reflecting light, cozy rainy day vibe",
            "gentle rainfall, glistening wet textures, fresh and clean feeling",
            "rain-soaked scene, puddles reflecting sky, rich saturated colours",
            "steady drizzle, soft grey tones, peaceful melancholy",
            "rain streaming down, blurred backgrounds, intimate sheltered feeling",
        ]

        snow_modifiers: List[str] = [
            "snowy scene, winter wonderland, falling snow, soft white textures",
            "fresh snowfall, pristine white blanket, hushed winter silence",
            "snow-covered landscape, cool blue shadows on white, crisp cold air",
            "gentle snowflakes drifting, frosted surfaces, cozy winter mood",
            "deep snow, muted colours against white, peaceful winter stillness",
        ]

        thunder_modifiers: List[str] = [
            "dramatic storm lighting, dark skies, powerful atmosphere",
            "brooding thunderclouds, flashes of light, electric tension",
            "stormy drama, wind-swept scene, raw natural power",
            "dark turbulent sky, moments before the storm, charged atmosphere",
            "dramatic contrast of dark clouds and bright breaks, moody intensity",
        ]

        # Select appropriate modifier list and return random choice
        if "clear" in condition or code == 0:
            return random.choice(clear_modifiers)
        elif "cloud" in condition or code in [2, 3]:
            return random.choice(cloudy_modifiers)
        elif "fog" in condition or code in [45, 48]:
            return random.choice(fog_modifiers)
        elif "rain" in condition or "drizzle" in condition or code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
            return random.choice(rain_modifiers)
        elif "snow" in condition or code in [71, 73, 75, 77, 85, 86]:
            return random.choice(snow_modifiers)
        elif "thunder" in condition or code in [95, 96, 99]:
            return random.choice(thunder_modifiers)

        return ""
