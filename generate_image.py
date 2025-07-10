#!/usr/bin/env python3
"""Generate art images using OpenAI's DALL-E 3 model."""

import os
import sys
import argparse
import requests
import json
from typing import Optional, Dict, List
from dotenv import load_dotenv
from datetime import datetime
import random


class ImageGenerator:
    """Class to handle image generation with OpenAI's API."""

    def __init__(self) -> None:
        """Initialize the generator with API key from environment."""
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("Error: OPENAI_API_KEY not found in .env file")
            sys.exit(1)

        self.image_dir = "generated_images"
        os.makedirs(self.image_dir, exist_ok=True)

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

    def _get_current_season_info(self) -> Dict[str, str]:
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

        # Format date information
        date_info = {
            "day": str(current_day),
            "day_with_suffix": f"{current_day}{suffix}",
            "month": str(current_month),
            "month_name": month_names[current_month - 1],
            "weekday": weekday,
            "formatted_date": formatted_date,
            "season": season
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

        # Choose a random art style
        style = random.choice(art_styles)

        # Example subjects for the LLM to use as guidance
        subject_examples = {
            "Winter": "snowy landscapes, winter berries, frost patterns, winter flowers, winter bouquets, winter flowers in a vase", # options: fields of heather or winter jasmine
            "Spring": "cherry blossoms, tulips, spring gardens, spring bouquets, wild flowers, spring flowers in a vase", # options: fields of daffodils or bluebells
            "Summer": "summer gardens, sunflowers, nature, summer bouquets, summer wild flowers, summer flowers in a vase, poppies in a meadow, lavender fields", # options: fields of daisies or zinnias
            "Autumn": "autumn foliage, harvest scenes, fall colors, fall flowers, autumn leaves, autumnal bouquets, autumn flowers in a vase" # options: fields of asters or goldenrod
        }

        # Optional: Special date check could be implemented here
        # For example, holidays or special events
        # This would be a good place to add holiday-specific themes
        # Create detailed context-aware prompt for DALL-E
        prompt = (
            f"Create a high-quality {style} art piece for {weekday}, "
            f"{formatted_date} in {season}. Choose a subject relevant to "
            f"this day and time of year. Focus on a single seasonal subject that evokes this time of year. "
            f"This could be something like {subject_examples[season]}, "
            f"or something more unexpected but still seasonally appropriate. Feel free to interpret the theme creatively based on the time of year. "
            f"Use a soft, natural {season} palette with subtle, muted tones—avoid overly vibrant or saturated colours. "
            f"The painting should emulate the look and feel of real paint on canvas, with visible brushstrokes and layered "
            f"texture. Aim for a realistic fine art aesthetic, evoking the softness of traditional oil or acrylic painting. "
            f"Ensure 16:9 aspect ratio. Create fine art with texture and depth. "
            f"IMPORTANT: Do not include any text, words, letters, dates, signatures, or written elements anywhere in the image. "
            f"This should be a pure visual artwork without any textual content whatsoever. "
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
                print(f"Response: {e.response.text}")
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

    generator = ImageGenerator()
    image_path = generator.generate_image(args.prompt)

    if image_path:
        print(f"Image generation successful: {image_path}")
    else:
        print("Image generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
