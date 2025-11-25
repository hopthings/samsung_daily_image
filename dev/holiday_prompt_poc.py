#!/usr/bin/env python3
"""Proof of concept for holiday-themed art generation."""

import argparse
import sys
import random
from datetime import datetime
from typing import Dict, Optional, List, NamedTuple

# Import the original class
from generate_image import ImageGenerator


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


class HolidayImageGenerator(ImageGenerator):
    """Extended ImageGenerator with generic holiday awareness."""

    # Define supported holidays
    HOLIDAYS = [
        HolidayConfig(
            name="Christmas",
            start_month=12, start_day=10,
            end_month=12, end_day=26,
            subjects=[
                "festive christmas market scene",
                "cozy living room with decorated christmas tree",
                "snowy village with christmas lights",
                "elegant christmas wreath on a rustic door",
                "vintage christmas ornaments",
                "winter scene with holly and ivy",
                "festive holiday bouquet with poinsettias"
            ],
            prompt_modifier="It is the festive holiday season. Capture the magic and warmth of Christmas.",
            palette="festive palette with rich reds, greens, golds, and snowy whites"
        ),
        HolidayConfig(
            name="Halloween",
            start_month=10, start_day=25,
            end_month=10, end_day=31,
            subjects=[
                "spooky haunted house silhouette",
                "carved pumpkins on a porch",
                "misty forest with twisted trees",
                "autumn harvest with pumpkins and corn",
                "vintage halloween decorations"
            ],
            prompt_modifier="It is Halloween season. Create a mysterious and slightly spooky atmosphere.",
            palette="autumnal palette with deep oranges, blacks, purples, and shadowy greys"
        ),
        HolidayConfig(
            name="July 4th",
            start_month=7, start_day=4,
            end_month=7, end_day=4,
            subjects=[
                "fireworks over a lake",
                "summer picnic scene",
                "patriotic bunting on a porch",
                "summer evening celebration"
            ],
            prompt_modifier="It is Independence Day. Capture the celebratory spirit of summer.",
            palette="vibrant summer palette with touches of red, white, and blue"
        ),
        HolidayConfig(
            name="New Year",
            start_month=12, start_day=31,
            end_month=1, end_day=1,
            subjects=[
                "fireworks in the night sky",
                "elegant champagne toast setup",
                "festive party streamers and confetti",
                "clocks striking midnight"
            ],
            prompt_modifier="It is New Year's. Capture the excitement and hope of a new beginning.",
            palette="elegant palette with golds, silvers, blacks, and deep blues"
        )
    ]

    def __init__(self, simulated_date: Optional[str] = None):
        """Initialize with optional simulated date."""
        super().__init__()
        self.simulated_date = None
        if simulated_date:
            try:
                self.simulated_date = datetime.strptime(simulated_date, "%Y-%m-%d")
            except ValueError:
                print(f"Error parsing date: {simulated_date}. Using current date.")

    def _get_current_season_info(self) -> Dict:
        """Get information about the current date and season, including holidays."""
        if self.simulated_date:
            current_date = self.simulated_date
        else:
            current_date = datetime.now()
            
        current_month = current_date.month
        current_day = current_date.day

        # Define seasons by month
        winter = (12, 1, 2)
        spring = (3, 4, 5)
        summer = (6, 7, 8)
        fall = (9, 10, 11)

        if current_month in winter:
            season = "Winter"
        elif current_month in spring:
            season = "Spring"
        elif current_month in summer:
            season = "Summer"
        elif current_month in fall:
            season = "Autumn"
        else:
            season = "unknown"

        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        weekday_names = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]
        weekday = weekday_names[current_date.weekday()]

        if 4 <= current_day <= 20 or 24 <= current_day <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][current_day % 10 - 1]

        month_name = month_names[current_month - 1]
        formatted_date = f"{current_day}{suffix} of {month_name}"

        # Check for active holiday
        active_holiday = None
        for holiday in self.HOLIDAYS:
            if holiday.is_active(current_date):
                active_holiday = holiday
                break

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
        """Generate creative prompt with holiday awareness."""
        art_styles = self._get_art_styles()
        
        date_info = self._get_current_season_info()
        season = date_info["season"]
        weekday = date_info["weekday"]
        formatted_date = date_info["formatted_date"]
        active_holiday: Optional[HolidayConfig] = date_info.get("active_holiday")

        style = random.choice(art_styles)

        subject_examples = {
            "Winter": "snowy landscapes, winter berries, frost patterns, winter flowers",
            "Spring": "cherry blossoms, tulips, spring gardens",
            "Summer": "summer gardens, sunflowers, nature",
            "Autumn": "autumn foliage, harvest scenes, fall colors"
        }

        prompt = (
            f"Create a high-quality {style} art piece for {weekday}, "
            f"{formatted_date} in {season}. "
        )

        if active_holiday:
            prompt += f"{active_holiday.prompt_modifier} "
            subject = random.choice(active_holiday.subjects)
            prompt += f"The subject should be a {subject}. "
            
            if active_holiday.palette:
                prompt += f"Use a {active_holiday.palette}. "
        else:
            prompt += (
                f"Choose a subject relevant to this day and time of year. "
                f"Focus on a single seasonal subject like {subject_examples.get(season, 'nature')}. "
                f"Use a soft, natural {season} palette. "
            )

        prompt += (
            f"The painting should emulate the look and feel of real paint on canvas, with visible brushstrokes and layered "
            f"texture. Aim for a realistic fine art aesthetic. "
            f"Ensure 16:9 aspect ratio. "
            f"IMPORTANT: Do not include any text, words, letters, dates, signatures, or written elements anywhere in the image."
        )

        return prompt


def main():
    parser = argparse.ArgumentParser(description="Holiday Prompt POC")
    parser.add_argument("--date", help="Simulate a specific date (YYYY-MM-DD)")
    parser.add_argument("--test-prompt-only", action="store_true", help="Only print the prompt, don't generate image")
    args = parser.parse_args()

    generator = HolidayImageGenerator(simulated_date=args.date)
    
    if args.test_prompt_only:
        prompt = generator.generate_art_prompt()
        print("\n--- Generated Prompt ---")
        print(prompt)
        print("------------------------\n")
        
        # Debug info
        info = generator._get_current_season_info()
        print(f"Simulated Date: {info['formatted_date']}")
        print(f"Season: {info['season']}")
        if info['active_holiday']:
            print(f"Active Holiday: {info['active_holiday'].name}")
        else:
            print("Active Holiday: None")
    else:
        generator.generate_image()

if __name__ == "__main__":
    main()
