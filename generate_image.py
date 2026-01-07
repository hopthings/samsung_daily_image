#!/usr/bin/env python3
"""Generate art images using OpenAI's DALL-E 3 model."""

import os
import sys
import argparse
import requests
import json
from typing import Optional, Dict, List, NamedTuple
from dotenv import load_dotenv
from datetime import datetime
import random
from weather_service import WeatherService

# Use SystemRandom for better randomness on embedded systems (Pi)
# This reads from /dev/urandom for each call instead of Mersenne Twister
secure_random = random.SystemRandom()


class HolidayConfig(NamedTuple):
    """Configuration for a holiday season."""
    name: str
    start_month: int
    start_day: int
    end_month: int
    end_day: int
    subjects: List[str]
    prompt_modifier: str
    palette: Optional[str] = None

    def is_active(self, date: datetime) -> bool:
        """Check if the given date falls within this holiday season."""
        # Handle year wrap-around (e.g. Dec 30 to Jan 2)
        if self.start_month > self.end_month:
            # It wraps around the year
            if date.month > self.start_month:
                return date.day >= self.start_day
            elif date.month == self.start_month:
                return date.day >= self.start_day
            elif date.month < self.end_month:
                return True
            elif date.month == self.end_month:
                return date.day <= self.end_day
            return False
        else:
            # Standard range within same year
            if date.month < self.start_month or date.month > self.end_month:
                return False
            if date.month == self.start_month and date.day < self.start_day:
                return False
            if date.month == self.end_month and date.day > self.end_day:
                return False
            return True


class ImageGenerator:
    """Class to handle image generation with OpenAI's API."""

    # Define supported holidays
    HOLIDAYS = [
        HolidayConfig(
            name="Christmas",
            start_month=12, start_day=10,
            end_month=12, end_day=26,
            subjects=[
                "abstract palette knife Christmas tree in rich green tones",
                "abstract palette knife Christmas tree with minimal ornaments",
                "stylised triangular Christmas tree made from layered impasto strokes",
                "Christmas tree formed from geometric palette-knife blocks",
                "Christmas tree built from overlapping textured paint shapes",
                "single red Christmas tree on a muted green textured background",
                "multicoloured abstract Christmas tree with thick palette-knife paint",
                "Christmas tree silhouette emerging from a heavily textured background",
                "Christmas tree made of sweeping palette-knife arcs",
                "Christmas tree with falling paint-flake snow in impasto style",
                "close-up holly branch with glossy red berries in thick impasto paint",
                "single holly leaf cluster with strong textured brushstrokes",
                "minimal winter composition featuring a holly sprig and berries",
                "ivy branch in winter tones painted with heavy texture",
                "winter berries arranged in a simple, abstract still-life",
                "single ornament resting on snowy textured ground in impasto style",
                "hanging ornaments suggested as floating abstract shapes",
                "abstract baubles surrounding a soft Christmas tree silhouette",
                "single bright star motif above a faint textured tree shape",
                "snowy evergreen tree painted in simple bold shapes",
                "frost-textured winter landscape with a single tree focal point",
                "snow-covered Christmas tree rendered in blocky palette-knife strokes",
                "winter night sky with a single glowing star in textured paint",
                "red, green, and white colour-field composition suggesting a tree form",
                "circular abstract holly wreath shape created with thick palette-knife strokes"
            ],
            prompt_modifier="It is the festive holiday season. Capture the magic and warmth of Christmas.",
            palette="festive palette with rich reds, greens, golds, and snowy whites"
        ),
        HolidayConfig(
            name="New Year",
            start_month=12, start_day=31,
            end_month=1, end_day=1,
            subjects=[
                "abstract gold and silver palette-knife strokes suggesting fireworks in a midnight sky",
                "minimalist city skyline with abstract fireworks above (no readable signage)",
                "single champagne glass rendered in thick impasto strokes with soft highlights",
                "pair of champagne flutes with gentle reflections in textured paint",
                "abstract clock face approaching midnight without any numbers or text",
                "bokeh-style circles of light built from layered palette-knife texture",
                "gold and deep blue colour-field composition suggesting a celebration",
                "silver confetti as scattered textured paint shapes on a dark background",
                "abstract starbursts of light in midnight blue and gold",
                "minimalist horizon with distant fireworks suggested through colour only",

                "single luminous candle or sparkler glow suggested with thick impasto texture",
                "close-up of sparkling bubbles rising in champagne, abstracted into textured dots",
                "abstract ribbon curls and streamers as flowing palette-knife paint arcs",
                "a simple party hat silhouette suggested through bold textured shapes (no text)",
                "midnight skyline with a single bright burst reflected on water in heavy texture",
                "abstract burst pattern radiating from a central point like a quiet firework bloom",
                "soft aurora-like bands of colour in deep blues and greens with knife-texture",
                "cluster of warm fairy-light or string-light orbs as thick paint dabs on dark",
                "a quiet still-life of a bottle and two glasses in minimalist impasto (no labels)",
                "top-down composition of scattered confetti and a single glass rim as abstract shapes",

                "abstract crescent moon with subtle fireworks haze suggested by textured strokes",
                "single golden starburst against a near-black background with thick impasto ridges",
                "city street at night suggested by blurred light trails and reflections, purely abstract",
                "a simple bridge or waterfront silhouette with fireworks glow diffused in texture",
                "abstract festive garland curve in gold and silver paint over deep navy",
                "close-up of metallic foil texture translated into chunky palette-knife blocks",
                "minimalist cluster of balloons suggested as soft textured spheres (no strings required)",
                "fireworks smoke clouds abstracted into layered greys and blues with knife marks",
                "celebration sparkle pattern: scattered bright flecks over a dark, textured ground",
                "single doorway of light in darkness suggesting ‘new beginnings’ through colour only",

                "abstract sunrise gradient after midnight: deep blue to warm gold with heavy texture",
                "quiet winter night landscape with distant fireworks glow on the horizon",
                "reflected fireworks on a calm river or harbour as broken impasto reflections",
                "abstract spiral composition suggesting a countdown motion, without numerals",
                "minimalist still-life of a clock silhouette and a glass, rendered as textured shapes",
                "a single branch with tiny twinkling light-like highlights, abstract and celebratory",
                "geometric mosaic of gold, silver, and navy blocks like confetti tiles in thick paint",
                "abstract burst of light behind soft cloud-like texture, suggesting celebration",
                "simple wreath-like circular form in metallic tones, purely abstract (no text)",
                "softly glowing window-like rectangles suggesting city buildings at night, abstracted",
            ],
            prompt_modifier="It is New Year's. Capture the excitement and hope of a new beginning.",
            palette="elegant palette with golds, silvers, blacks, and deep blues"
        ),
        HolidayConfig(
            name="Halloween",
            start_month=10, start_day=25,
            end_month=10, end_day=31,
            subjects=[
                "single carved pumpkin with dramatic side lighting in thick textured paint",
                "row of simple pumpkins against a dark, abstract background",
                "silhouette of a twisted tree against a moody twilight sky",
                "abstract moonlit sky with the suggestion of flying bats in bold brushstrokes",
                "crow perched on a branch painted in expressive impasto strokes",
                "cluster of autumn leaves in deep oranges and purples on a dark ground",
                "misty path through a forest suggested with soft textured strokes",
                "simple haunted house silhouette with softly glowing windows against the night sky",
                "still-life of small pumpkins and gourds in dramatic, textured lighting",
                "abstract swirl of autumn colours hinting at a Halloween night atmosphere"
            ],
            prompt_modifier="It is Halloween season. Create a mysterious and slightly spooky atmosphere.",
            palette="autumnal palette with deep oranges, blacks, purples, and shadowy greys"
        ),
        HolidayConfig(
            name="July 4th",
            start_month=7, start_day=4,
            end_month=7, end_day=4,
            subjects=[
                "abstract red, white, and blue brushstrokes suggesting distant fireworks",
                "simple star motif in textured red, white, and blue paint",
                "calm summer lake at sunset with soft impasto reflections",
                "single sailboat silhouette on a warm evening horizon",
                "rustic wooden plank texture with subtle Americana colours",
                "soft abstract sky with gentle bursts of colour suggesting fireworks",
                "minimalist landscape with wide blue sky and warm golden field",
                "close-up of a single colour-block pattern inspired by red, white, and blue",
                "abstract celebratory confetti pattern in red, white, and blue tones",
                "glowing summer twilight gradient rendered in layered palette-knife strokes"
            ],
            prompt_modifier="It is Independence Day. Capture the celebratory spirit of summer.",
            palette="vibrant summer palette with touches of red, white, and blue"
        ),
        HolidayConfig(
            name="Valentine's Day",
            start_month=2, start_day=14,
            end_month=2, end_day=14,
            subjects=[
                "single abstract heart shape formed with bold palette-knife strokes",
                "pair of overlapping hearts in thick impasto texture",
                "soft pink and red colour-field composition suggesting a romantic theme",
                "single rose rendered in expressive palette-knife style",
                "minimalist still-life of two roses with heavy textured paint",
                "abstract swirling red and pink strokes suggesting affection",
                "simple silhouette of two entwined stems painted with thick texture",
                "romantic candle glow suggested through warm textured brushstrokes",
                "soft abstract gradient in warm pinks and reds with visible texture",
                "delicate heart motif emerging from layered impasto paint"
            ],
            prompt_modifier="It is Valentine's season. Capture the mood of warmth, romance, and softness.",
            palette="romantic palette with warm reds, soft pinks, creams, and gentle highlights"
        )
    ]

    def __init__(self) -> None:
        """Initialize the generator with API key from environment.

        Raises:
            ValueError: If OPENAI_API_KEY is not found in environment.
        """
        load_dotenv()
        self.api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        self.image_dir: str = "generated_images"
        os.makedirs(self.image_dir, exist_ok=True)
        self.weather_service: WeatherService = WeatherService()

    def _get_art_styles(self) -> List[str]:
        """Get art styles that work with the impasto/palette knife style.

        Returns:
            List of art styles compatible with Samsung Frame TV display
        """
        # Art styles as per CLAUDE.md guidelines (palette knife/impasto)
        art_styles = [
            "palette knife painting",
            "impasto technique",
            "textured painting",
            "oil painting with heavy texture",
            "thick paint application",
            "textured abstract art",
            "modern impressionism with palette knife",
            "contemporary impasto landscape",
            "bold and textured color field painting"
        ]
        return art_styles

    def _get_current_season_info(self) -> Dict:
        """Get information about the current date and season.

        Returns:
            Dictionary with current date information
        """
        current_date = datetime.now()
        current_month = current_date.month
        current_day = current_date.day

        # Define seasons by month
        winter = (12, 1, 2)  # December to February
        spring = (3, 4, 5)   # March to May
        summer = (6, 7, 8)   # June to August
        fall = (9, 10, 11)   # September to November

        # Get the season name
        if current_month in winter:
            season = "Winter"
        elif current_month in spring:
            season = "Spring"
        elif current_month in summer:
            season = "Summer"
        elif current_month in fall:
            season = "Autumn"
        else:
            season = "unknown"  # Should not happen

        # Month names
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        # Day of week
        weekday_names = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]
        weekday = weekday_names[current_date.weekday()]

        # Date ordinal suffix (1st, 2nd, 3rd, 4th, etc)
        if 4 <= current_day <= 20 or 24 <= current_day <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][current_day % 10 - 1]

        # Formatted date (e.g., "1st of April", "25th of December")
        month_name = month_names[current_month - 1]
        formatted_date = f"{current_day}{suffix} of {month_name}"

        # Check for active holiday
        active_holiday = None
        for holiday in self.HOLIDAYS:
            if holiday.is_active(current_date):
                active_holiday = holiday
                break

        # Format date information
        date_info = {
            "day": str(current_day),
            "day_with_suffix": f"{current_day}{suffix}",
            "month": str(current_month),
            "month_name": month_names[current_month - 1],
            "weekday": weekday,
            "formatted_date": formatted_date,
            "season": season,
            "active_holiday": active_holiday
        }
        return date_info

    def generate_art_prompt(self) -> str:
        """Generate creative prompt for art based on current date."""
        # Get art styles (palette knife/impasto as per guidelines)
        art_styles = self._get_art_styles()

        # Get current date information
        date_info = self._get_current_season_info()
        season = date_info["season"]
        weekday = date_info["weekday"]
        formatted_date = date_info["formatted_date"]
        active_holiday: Optional[HolidayConfig] = date_info.get("active_holiday")

        # Get Weather
        weather_location = os.getenv("WEATHER_LOCATION")
        lat = None
        lon = None

        if weather_location:
            try:
                lat_str, lon_str = weather_location.split(",")
                lat = float(lat_str.strip())
                lon = float(lon_str.strip())
            except ValueError:
                print(f"Error parsing WEATHER_LOCATION: {weather_location}")

        weather_modifier = ""
        weather_desc = "unknown weather"
        
        if lat is not None and lon is not None:
            print(f"Fetching weather for {lat}, {lon}...")
            weather = self.weather_service.get_current_weather(lat, lon)
            if weather:
                weather_desc = weather['condition']
                weather_modifier = self.weather_service.get_weather_prompt_modifier(weather)
                print(f"Current weather: {weather_desc} ({weather['temperature']})")
            else:
                print("Could not fetch weather data.")
        else:
            print("WEATHER_LOCATION not set in .env (format: lat,lon), skipping weather.")

        # Choose a random art style
        style = secure_random.choice(art_styles)

        # Choose scene type: indoor or outdoor (ensures no mixed compositions)
        # Weighted 60% outdoor, 40% indoor
        scene_type = "outdoor" if secure_random.random() < 0.6 else "indoor"
        print(f"Selected scene type: {scene_type}")

        # Create detailed context-aware prompt for DALL-E
        prompt = (
            f"Create a high-quality {style} art piece for {weekday}, "
            f"{formatted_date} in {season}. "
        )

        if active_holiday:
            # Holiday-specific prompts (weather shown directly)
            if weather_modifier:
                prompt += f"The scene should reflect the current weather: {weather_desc}. Incorporate {weather_modifier}. "
            prompt += f"{active_holiday.prompt_modifier} "
            subject = secure_random.choice(active_holiday.subjects)
            prompt += f"The subject should be a {subject}. "

            if active_holiday.palette:
                prompt += f"Use a {active_holiday.palette}. "
        else:
            # Non-holiday: use indoor/outdoor scene type logic
            if scene_type == "indoor":
                # Randomly decide whether to hint at weather through a window
                show_window_weather = secure_random.choice([True, False])

                if weather_modifier and show_window_weather:
                    # Indoor weather: subtle, through window or lighting only
                    prompt += (
                        f"The scene should subtly hint at the weather outside via a distant window view "
                        f"or implied by lighting and colour temperature. "
                        f"Do not bring outdoor weather effects into the interior space. "
                    )
                    window_guidance = (
                        f"If a window is shown, it must be simple and unobtrusive. "
                        f"Do not show balconies, terraces, railings, exterior ground, or snow touching indoor objects. "
                    )
                else:
                    # Pure indoor scene, no exterior reference
                    window_guidance = (
                        f"Do not include any windows, doors, or views to the outside. "
                        f"Focus entirely on the indoor still-life composition. "
                    )

                # Variety knobs for indoor still-life scenes (keep uncluttered and Frame-friendly)
                indoor_subjects_by_season = {
                    "Spring": [
                        "delicate spring blooms in soft morning light",
                        "a nest with pale eggs on weathered wood",
                        "fresh wildflowers with gentle diffused light",
                        "spring bulbs and ceramic in cool window light",
                        "cherry blossom branches with soft shadows",
                        "tender green shoots in simple earthenware",
                        "pastel blooms and linen in airy light",
                        "spring garden clippings in natural light",
                    ],
                    "Summer": [
                        "sun-drenched still-life with summer produce",
                        "garden flowers in warm afternoon light",
                        "citrus and glass with bright reflections",
                        "ripe stone fruit in golden hour glow",
                        "summer bouquet with dramatic shadows",
                        "fresh herbs and terracotta in sunlight",
                        "berries and pewter in dappled light",
                        "summer harvest on a rustic surface",
                        "wildflowers and vintage vessels",
                        "seashells and driftwood in warm light",
                    ],
                    "Autumn": [
                        "harvest still-life with gourds and copper",
                        "wine and ripe fruit with dramatic chiaroscuro",
                        "autumn foraging finds on weathered wood",
                        "fallen leaves and aged pottery",
                        "apples and brass in warm lamplight",
                        "dried grasses and seed pods in muted tones",
                        "wild mushrooms and moss on dark wood",
                        "persimmons and dark cloth with rich shadows",
                        "autumn branches and berries in fading light",
                        "chestnuts and copper in candlelight",
                    ],
                    "Winter": [
                        "candles and deep shadows in warm lamplight",
                        "winter citrus and brass vessels",
                        "dried flowers and aged pottery in soft light",
                        "pomegranate and dark velvet",
                        "evergreen sprigs and candlelight",
                        "frosted glass and winter berries",
                        "pine cones and weathered wood in firelight",
                        "dried hydrangeas in muted winter tones",
                        "warm bread and ceramic in soft interior light",
                        "amaryllis and antique silver",
                    ],
                }

                # Composition / viewpoint variety to avoid same-looking indoor images
                indoor_compositions = [
                    "close-up still-life with one strong focal object",
                    "simple tabletop arrangement with two to three objects maximum",
                    "minimalist composition with large areas of negative space",
                    "top-down view of a small arrangement on a table",
                    "side-lit composition with dramatic shadows",
                    "soft, diffused light and gentle tonal transitions",
                ]

                # Pick subject + composition with secure randomness
                season_subjects = indoor_subjects_by_season.get(season, indoor_subjects_by_season["Autumn"])
                indoor_subject = secure_random.choice(season_subjects)
                indoor_composition = secure_random.choice(indoor_compositions)

                prompt += (
                    f"Create an intimate indoor still-life scene. "
                    f"The entire scene must be set inside a room. "
                    f"Choose a {indoor_composition}. "
                    f"The subject should be {indoor_subject}. "
                    f"Limit the scene to a small number of objects and avoid clutter or busy interiors. "
                    f"All objects must sit on clearly indoor surfaces like tables, shelves, or counters. "
                    f"{window_guidance}"
                    f"Keep the composition clearly and unmistakably indoors. "
                    f"Use a natural {season.lower()} palette with balanced, harmonious tones—avoid overly vibrant or saturated colours. "
                )
            else:
                # Outdoor weather: shown directly in the landscape
                if weather_modifier:
                    prompt += (
                        f"The scene should directly show the current weather: {weather_desc}. "
                        f"Incorporate {weather_modifier} naturally into the outdoor scene. "
                    )

                # Season-specific inspiration (loose guidance, not prescriptive)
                seasonal_inspiration = {
                    "Spring": "blossoms, fresh growth, wildflowers, soft morning light, new leaves, birdsong atmosphere",
                    "Summer": "warm golden light, meadows, coastal scenes, full bloom, lazy afternoons, long shadows",
                    "Autumn": "golden and russet tones, fallen leaves, misty mornings, harvest time, berries, bare branches",
                    "Winter": "frost, bare trees, holly, snow, cold light, quiet stillness, ice, evergreens",
                }

                inspiration = seasonal_inspiration.get(season, seasonal_inspiration["Autumn"])

                prompt += (
                    f"Create an outdoor {season.lower()} nature scene. "
                    f"Draw inspiration from: {inspiration}. "
                    f"This could be a wide landscape, a close-up detail, or an abstract composition - vary the approach. "
                    f"Do not include any vases, pots, planters, bowls, tables, furniture, rugs, balconies, or window sills. "
                    f"Do not include still-life arrangements or man-made containers of any kind. "
                    f"The scene must be clearly and unmistakably outdoors. "
                    f"Use a natural {season.lower()} palette with balanced, harmonious tones—avoid overly vibrant or saturated colours. "
                )

        prompt += (
            f"STYLE: Use visible palette knife strokes and thick impasto texture throughout. "
            f"The artwork should have the tactile quality of oil paint applied with a knife. "
            f"COLOUR: Use muted, naturalistic colour values typical of traditional oil painting. "
            f"Colours should have the slightly greyed, earthy quality of real pigments—avoid "
            f"oversaturated, digitally-enhanced, or neon-bright tones. Keep the palette restrained "
            f"and harmonious, as in gallery-quality oil paintings. "
        )

        prompt += (
            f"CRITICAL RULES: "
            f"(1) FULL BLEED - the artwork must extend to all four edges with no borders, frames, canvas edges, "
            f"vignettes, or margins visible. The scene continues beyond the image boundaries. "
            f"(2) NOT A META-IMAGE - do not depict a painting, canvas, easel, art supplies, brushes, or reference photos. "
            f"The image IS the artwork, not a picture OF an artwork. "
            f"(3) NO TEXT - no words, letters, signatures, or watermarks. "
            f"(4) 16:9 aspect ratio. "
        )

        return prompt

    def generate_image(self, prompt: Optional[str] = None) -> Optional[str]:
        """Generate an image using DALL-E 3 via OpenAI API.

        Args:
            prompt: Optional custom prompt. If not provided, a prompt will be
                   generated.

        Returns:
            Path to the downloaded image if successful, None otherwise.
        """
        if not prompt:
            prompt = self.generate_art_prompt()

        print(f"Generating image with prompt: {prompt}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1792x1024",  # 16:9 aspect ratio
            "quality": "hd",
            "style": "natural"
        }

        try:
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )
            response.raise_for_status()

            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                image_url = data["data"][0]["url"]
                return self._download_image(image_url, prompt)
            else:
                print("Error: Unexpected response format")
                print(data)
                return None

        except requests.exceptions.RequestException as e:
            print(f"Error generating image: {e}")
            if hasattr(e, 'response') and e.response is not None:
                # Only log status code to avoid exposing credentials
                print(f"Response status code: {e.response.status_code}")
                try:
                    error_data = e.response.json()
                    # Only log safe error message fields, not full response
                    if 'error' in error_data and 'message' in error_data['error']:
                        print(f"Error message: {error_data['error']['message']}")
                except (ValueError, KeyError):
                    print("Error response could not be parsed")
            return None

    def _download_image(self, url: str, prompt: str) -> Optional[str]:
        """Download the generated image.

        Args:
            url: The URL of the image to download.
            prompt: The prompt used to generate the image.

        Returns:
            Path to the downloaded image if successful, None otherwise.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"art_{timestamp}.jpeg"
            filepath = os.path.join(self.image_dir, filename)

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(response.content)

            # Save prompt alongside image
            prompt_file = os.path.join(
                self.image_dir, f"art_{timestamp}_prompt.txt"
            )
            with open(prompt_file, "w") as f:
                f.write(prompt)

            print(f"Image saved to {filepath}")
            return filepath

        except requests.exceptions.RequestException as e:
            print(f"Error downloading image: {e}")
            return None


def main() -> None:
    """Main function to parse arguments and generate images."""
    parser = argparse.ArgumentParser(description="Generate art using DALL-E 3")
    parser.add_argument(
        "--prompt", "-p",
        help="Custom prompt for image generation. If not provided, "
             "a prompt will be generated."
    )

    args = parser.parse_args()

    try:
        generator = ImageGenerator()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    image_path = generator.generate_image(args.prompt)

    if image_path:
        print(f"Image generation successful: {image_path}")
    else:
        print("Image generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
