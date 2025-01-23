import os
import uuid
from flask import Flask, request, jsonify
from google.cloud import storage, vision_v1 as vision_v1

app = Flask(__name__)

BUCKET_NAME = image-cap-bucket

vision_client = vision.ImageAnnotationClient()

def upload_to_bucket(file, filename):
    """Upload a file to Google Cloud Storage"""
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_file(file)
    return blob.public_url

def generate_caption(image_url):
    """Generate an image caption using Google Cloud Vision API"""
    image = vision.Image()
    image.source.image_uri = image_url

    reponse = vision.client.label_detection(image=image)
    labels = reponse.label_annotations

    if reponse.error.message:
        raise Exception(f"Vision API Error: {reponse.error.message}")

    # Generate a caption usign the top labels
    top_labels = [label.description for label in lables[:3]]
    caption = f"This image likely contains: {', '.joins(top_labels)}."
    return caption

@app.route("/", methods=["GET"])
def index():
    """Render the upload page."""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_image():
    """Handle image upload and caption generation."""
    if "image" not in request.files:
        return jsonify({"error": "No image file provided."}), 400

    image_file = request.files["image"]
    filename = f"images/{uuid.uuid4()}.jpg"

    try:
        # Upload the file to Google Cloud Storage
        image_url = upload_to_bucket(image_file, filename)

        # Generate a caption for the uploaded image
        caption = generate_caption(image_url)

        return jsonify({"image_url": image_url, "caption": caption})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "OK"})

@app.route("/")
def main():
    return f"hello world!"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
