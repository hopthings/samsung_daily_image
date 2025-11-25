# Samsung Daily Image

Automatically generate and display art on your Samsung Frame TV. This application uses OpenAI's DALL-E 3 to create beautiful art images and uploads them to your Samsung Frame TV.

## Features

- Generate art images with DALL-E 3 using palette knife/impasto styles (16:9 aspect ratio)
- Weather-based art prompts that adapt to local conditions (sunny, rainy, snowy, etc.)
- Holiday-themed art generation (Christmas, Halloween, Valentine's Day, etc.)
- Image enhancement with multiple presets (sharpening, color enhancement, etc.)
- Image upscaling for optimal TV display quality
- Upload images to Samsung Frame TV with automatic size optimization
- Set images as active art on the TV with robust retry logic
- Command-line interface with extensive options
- Comprehensive logging and debugging capabilities
- Automated daily execution script with TV wake-on-LAN support
- Debug tools for troubleshooting TV connectivity issues

## Requirements

- Python 3.8+
- OpenAI API key
- Samsung Frame TV on your local network
- TV IP address

## Installation

1. Clone this repository:
```bash
git clone https://github.com/hopthings/samsung_daily_image.git
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

4. Create a `.env` file with your configuration (see `.env.example`):
```
OPENAI_API_KEY=your_openai_api_key
SAMSUNG_TV_IP=your_tv_ip_address
SAMSUNG_TV_MAC=your_tv_mac_address      # Optional: for wake-on-LAN support
WEATHER_LOCATION=51.5074,-0.1278        # Optional: lat,lon for weather-based art
```

## Usage

### Basic Commands

Generate a new image and display it:
```bash
python main.py
```

Use a custom prompt:
```bash
python main.py --prompt "A vibrant sunset over a mountain landscape with thick impasto texture"
```

Use an existing image:
```bash
python main.py --image path/to/your/image.jpg
```

### Enhancement and Processing Options

List available enhancement presets:
```bash
python main.py --list-presets
```

Use a specific enhancement preset:
```bash
python main.py --enhance upscale-sharp
```

Skip enhancement:
```bash
python main.py --enhance none
```

Skip upscaling:
```bash
python main.py --no-upscale
```

Skip uploading to TV (for testing):
```bash
python main.py --skip-upload
```

### Debugging Options

Enable debug logging:
```bash
python main.py --debug
```

Enable verbose debug logging (maximum detail):
```bash
python main.py --verbose
```

Test TV connectivity:
```bash
python debug_tv.py
```

### Automated Daily Execution

Use the included shell script for robust daily automation:
```bash
./run_daily_image.sh
```

This script includes:
- Virtual environment detection and activation
- TV connectivity testing and wake-on-LAN support
- Comprehensive logging to `daily_run.log`
- Retry logic (optional)

## Setting up as a scheduled task

### Linux/macOS (using cron)

**Recommended**: Use the included shell script for robust execution:

```bash
crontab -e
```

Add the following line to run daily at 8 AM:

```
0 8 * * * /path/to/samsung_daily_image/run_daily_image.sh
```

**Alternative**: Direct Python execution (less robust):

```
0 8 * * * cd /path/to/samsung_daily_image && /path/to/python main.py --verbose >> daily_art.log 2>&1
```

### Windows (using Task Scheduler)

1. Open Task Scheduler
2. Create a new task with a trigger for your preferred time
3. Set the action to start a program:
   - Program/script: `C:\path\to\samsung_daily_image\run_daily_image.sh` (if using WSL/Git Bash)
   - Or Program/script: `C:\path\to\python.exe`
   - Arguments: `C:\path\to\samsung_daily_image\main.py --verbose`
   - Start in: `C:\path\to\samsung_daily_image`

## Troubleshooting

### Common Issues

1. **Images upload but don't display on TV**:
   - Run `python debug_tv.py` to check TV connectivity
   - Check WebSocket connection timeouts in logs
   - Try enabling wake-on-LAN with TV MAC address

2. **Upload timeouts**:
   - Use `--verbose` flag for detailed network logging
   - Check image file size (automatically optimized to <5MB)
   - Verify TV is powered on and connected to network

3. **TV not responding**:
   - Verify IP address in `.env` file
   - Check if TV allows connections from unknown devices
   - Try manual wake-on-LAN: `wakeonlan [MAC_ADDRESS]`

### Log Files

- `daily_art.log` - Application logs from Python script
- `daily_run.log` - Shell script execution logs (includes network tests)

### Debug Commands

Check available enhancement presets:
```bash
python main.py --list-presets
```

Test image processing pipeline without uploading:
```bash
python main.py --skip-upload --verbose
```

Check TV status and connectivity:
```bash
python debug_tv.py
```

## License

MIT

## Acknowledgements

- [Samsung TV WS API](https://github.com/NickWaterton/samsung-tv-ws-api) for the Samsung TV control library
- OpenAI for the DALL-E 3 API