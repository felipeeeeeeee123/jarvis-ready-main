# JARVIS Trading Assistant

This project includes a small trading and Q&A assistant. It can fetch
information from the web, store facts locally and execute basic trading
strategies through the Alpaca API.

## Installation

1. Install **Python 3.10+**.
2. (Optional) create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env` and fill in your API keys for Alpaca and Telegram.

## Usage

Start the interactive CLI bot:
```bash
python backend/main.py
```

To run the minimal HTTP server and keep-alive process:
```bash
bash start.sh
```

## Running in VS Code

1. Open this folder in VS Code (`File -> Open Folder`).
2. Ensure the Python extension is installed and select your virtual environment
   as the interpreter.
3. Use the integrated terminal to run the commands above or create a launch
   configuration that runs `backend/main.py`.
