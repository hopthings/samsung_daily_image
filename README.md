# Samsung Daily Image

Automatically generate and display art on your Samsung Frame TV. This application uses OpenAI's DALL-E 3 to create beautiful art images and uploads them to your Samsung Frame TV.

## Features

- Generate art images with DALL-E 3 using palette knife/impasto styles
- Upload images to Samsung Frame TV
- Set images as active art on the TV
- Command-line interface with options for custom prompts and existing images
- Detailed logging

## Requirements

- Python 3.8+
- OpenAI API key
- Samsung Frame TV on your local network
- TV IP address

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/samsung_daily_image.git
cd samsung_daily_image
```

2. Set up a Python virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```
OPENAI_API_KEY=your_openai_api_key
SAMSUNG_TV_IP=your_tv_ip_address
```

## Usage

### Generate a new image and display it

```bash
python main.py
```

### Use a custom prompt

```bash
python main.py --prompt "A vibrant sunset over a mountain landscape with thick impasto texture"
```

### Use an existing image

```bash
python main.py --image path/to/your/image.jpg
```

### Enable debug logging

```bash
python main.py --debug
```

## Setting up as a scheduled task

### Linux/macOS (using cron)

To run the script daily at 8 AM:

```bash
crontab -e
```

Add the following line:

```
0 8 * * * cd /path/to/samsung_daily_image && /path/to/python main.py >> daily_art.log 2>&1
```

### Windows (using Task Scheduler)

1. Open Task Scheduler
2. Create a new task with a trigger for your preferred time
3. Set the action to start a program:
   - Program/script: `C:\path\to\python.exe`
   - Arguments: `C:\path\to\samsung_daily_image\main.py`
   - Start in: `C:\path\to\samsung_daily_image`

## License

MIT

## Acknowledgements

- [Samsung TV WS API](https://github.com/NickWaterton/samsung-tv-ws-api) for the Samsung TV control library
- OpenAI for the DALL-E 3 API