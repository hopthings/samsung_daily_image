#!/usr/bin/env python3
"""
POC for generating images using Gemini 3 Pro Image (Imagen 3) via Google Gen AI SDK.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from generate_image import ImageGenerator

def generate_image_gemini():
    """Generate an image using Gemini 3 Pro Image (Imagen 3)."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file")
        sys.exit(1)

    # Configure the SDK
    genai.configure(api_key=api_key)

    # Get the prompt from the existing logic
    print("Generating prompt using existing logic...")
    generator = ImageGenerator()
    prompt = generator.generate_art_prompt()
    print(f"Generated Prompt: {prompt}")

    # List of models to try
    model_names = [
        "models/gemini-3-pro-image-preview",
        "gemini-3-pro-image-preview",
        "models/nano-banana-pro-preview", # User suggestion
    ]

    for model_name in model_names:
        print(f"Attempting to use model: {model_name}")
        try:
            model = genai.GenerativeModel(model_name)
            print(f"Successfully initialized GenerativeModel for: {model_name}")
            
            print(f"Requesting content generation (image) with {model_name}...")
            # Note: For image generation models via generate_content, the prompt is just the text.
            # We need to see if it returns an image part.
            response = model.generate_content(prompt)
            
            print("Response received.")
            # Check if response contains images
            # Usually response.parts would contain the image if it's a multimodal response
            
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        print("Found inline data (image?)")
                        print(f"Data type: {type(part.inline_data.data)}")
                        
                        # In some SDK versions, this is already bytes.
                        # In others, it might be a base64 string.
                        img_data = part.inline_data.data
                        
                        # If it's a string, try to decode it.
                        if isinstance(img_data, str):
                             import base64
                             print("Data is string, attempting base64 decode...")
                             img_data = base64.b64decode(img_data)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_dir = "generated_images"
                        os.makedirs(output_dir, exist_ok=True)
                        
                        filename = f"gemini_art_{timestamp}.jpeg" # Assuming jpeg
                        filepath = os.path.join(output_dir, filename)
                        
                        with open(filepath, "wb") as f:
                            f.write(img_data)
                        print(f"Success! Image saved to: {filepath}")
                        
                        # Save prompt
                        prompt_path = os.path.join(output_dir, f"gemini_art_{timestamp}_prompt.txt")
                        with open(prompt_path, "w") as f:
                            f.write(prompt)
                        return
                    else:
                        print(f"Part type: {type(part)}")
                        print(part)
            else:
                print("Response has no parts.")
                print(response)

        except Exception as e:
            print(f"Failed with model {model_name}: {e}")
            continue

    print("All model attempts failed.")

if __name__ == "__main__":
    generate_image_gemini()
