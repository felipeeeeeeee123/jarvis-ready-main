from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive() -> Thread:
    """Start the keep-alive server in a background thread."""
    t = Thread(target=run)
    t.daemon = True
    t.start()
    return t


if __name__ == "__main__":
    thread = keep_alive()
    thread.join()
