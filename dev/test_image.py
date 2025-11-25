import os
import base64
from dotenv import load_dotenv
import sys
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

client = OpenAI(api_key=api_key)

print("Generating image with GPT-5...")

# Use the Responses API with GPT-5 and image_generation tool
try:
    response = client.responses.create(
        model="gpt-5",
        input="Generate an image of gray tabby cat hugging an otter with an orange scarf",
        tools=[{"type": "image_generation"}],
    )

    print("Response received!")
    print(f"Response structure: {response}")

    # Save the image to a file
    image_data = [
        output.result
        for output in response.output
        if output.type == "image_generation_call"
    ]

    if image_data:
        image_base64 = image_data[0]
        with open("otter.png", "wb") as f:
            f.write(base64.b64decode(image_base64))
        print("✓ Image saved to otter.png")
    else:
        print("✗ No image data found in response")
        print(f"Response outputs: {response.output}")

except Exception as e:
    print(f"✗ Error generating image: {e}")
    sys.exit(1)