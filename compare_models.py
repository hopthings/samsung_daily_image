#!/usr/bin/env python3
"""Compare DALL-E 3 vs gpt-image-1 for art generation."""

import os
import requests
from dotenv import load_dotenv
import sys
from openai import OpenAI
from datetime import datetime

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

client = OpenAI(api_key=api_key)

# Test prompt - using a similar style to your current art generation
test_prompt = (
    "Create a high-quality palette knife painting art piece for a Samsung Frame TV. "
    "Focus on a autumn landscape with warm fall colors. "
    "Use a soft, natural autumn palette with subtle, muted tones—avoid overly vibrant "
    "or saturated colours. The painting should emulate the look and feel of real paint "
    "on canvas, with visible brushstrokes and layered texture. Aim for a realistic fine "
    "art aesthetic, evoking the softness of traditional oil or acrylic painting. "
    "Ensure 16:9 aspect ratio. Create fine art with texture and depth. "
    "IMPORTANT: Do not include any text, words, letters, dates, signatures, or written "
    "elements anywhere in the image."
)


def generate_with_dalle3() -> str:
    """Generate image with DALL-E 3."""
    print("\n" + "=" * 60)
    print("Testing DALL-E 3 (Current Model)")
    print("=" * 60)

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=test_prompt,
            n=1,
            size="1792x1024",  # 16:9 aspect ratio
            quality="hd",
            style="natural",
        )

        image_url = response.data[0].url
        print(f"✓ Image generated successfully")

        # Download the image
        image_response = requests.get(image_url, timeout=30)
        image_response.raise_for_status()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dalle3_test_{timestamp}.png"

        with open(filename, "wb") as f:
            f.write(image_response.content)

        print(f"✓ Image saved to: {filename}")
        print(f"  Size: {len(image_response.content) / 1024 / 1024:.2f} MB")
        return filename

    except Exception as e:
        print(f"✗ Error: {e}")
        return ""


def generate_with_gpt_image1() -> str:
    """Generate image with gpt-image-1."""
    print("\n" + "=" * 60)
    print("Testing gpt-image-1 (New Model)")
    print("=" * 60)

    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=test_prompt,
            n=1,
            size="1024x1024",  # Will try 16:9 if supported
            quality="high",  # Options: 'low', 'medium', 'high', 'auto'
        )

        image_url = response.data[0].url
        print(f"✓ Image generated successfully")

        # Download the image
        image_response = requests.get(image_url, timeout=30)
        image_response.raise_for_status()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gpt_image1_test_{timestamp}.png"

        with open(filename, "wb") as f:
            f.write(image_response.content)

        print(f"✓ Image saved to: {filename}")
        print(f"  Size: {len(image_response.content) / 1024 / 1024:.2f} MB")
        return filename

    except Exception as e:
        print(f"✗ Error: {e}")
        if "verified" in str(e).lower():
            print("\nℹ  To use gpt-image-1, verify your organization at:")
            print("   https://platform.openai.com/settings/organization/general")
        return ""


def main() -> None:
    """Main function to compare both models."""
    print("\n🎨 AI Image Generation Model Comparison")
    print("Testing palette knife art generation for Samsung Frame TV\n")

    dalle3_file = generate_with_dalle3()
    gpt_image1_file = generate_with_gpt_image1()

    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)

    if dalle3_file:
        print(f"✓ DALL-E 3:     {dalle3_file}")
    else:
        print("✗ DALL-E 3:     Failed")

    if gpt_image1_file:
        print(f"✓ gpt-image-1:  {gpt_image1_file}")
    else:
        print("✗ gpt-image-1:  Failed")

    print("\nCompare the images to see which model produces better")
    print("palette knife/impasto textures for your Frame TV!")


if __name__ == "__main__":
    main()
