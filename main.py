import os
import uuid
from flask import Flask, request, jsonify
from google.cloud import storage, vision_v1 as vision_v1

app = Flask(__name__)

@app.route("/")
def main():
    return f"hello world!"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
