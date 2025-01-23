import os
import uuid
import time
import json
import logging
import sys
from flask import Flask, request, jsonify, render_template
from google.cloud import storage, vision_v1 as vision
from google.api_core.exceptions import Conflict

# Logger setup
class JsonFormatter(logging.Formatter):
    def format(self, record):
        json_log_object = {
            "severity": record.levelname,
            "message": record.getMessage(),
        }
        json_log_object.update(getattr(record, "json_fields", {}))
        return json.dumps(json_log_object)

logger = logging.getLogger(__name__)
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(JsonFormatter())
logger.addHandler(sh)
logger.setLevel(logging.DEBUG)

# Flask app initialization
app = Flask(__name__)

# Google Cloud Storage and Vision API setup
BUCKET_NAME = "image-cap-bucket"
vision_client = vision.ImageAnnotatorClient()
storage_client = storage.Client()

# Retry IAM binding function
def add_bucket_iam_binding_with_retries(bucket_name, member, role, retries=5):
    bucket = storage_client.bucket(bucket_name)
    for i in range(retries):
        try:
            policy = bucket.get_iam_policy(requested_policy_version=3)
            policy.bindings.append({"role": role, "members": {member}})
            bucket.set_iam_policy(policy)
            logger.info("IAM policy updated successfully.")
            return
        except Conflict as e:
            logger.warning(f"Conflict encountered: {e}. Retrying...")
            time.sleep(2 ** i)  # Exponential backoff
    logger.error("Failed to update IAM policy after retries.")
    raise RuntimeError("Could not set IAM policy.")

# Upload file to GCP bucket
def upload_to_bucket(file, filename):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_file(file)
    logger.info(f"Uploaded {filename} to bucket.")
    return blob.public_url

# Generate image caption
def generate_caption(image_url):
    logger.debug("Generating caption for image.")
    image = vision.Image()
    image.source.image_uri = image_url

    response = vision_client.label_detection(image=image)
    labels = response.label_annotations

    if response.error.message:
        logger.error("Vision API Error")
        raise Exception(f"Vision API Error: {response.error.message}")

    top_labels = [label.description for label in labels[:3]]
    caption = f"This image likely contains: {', '.join(top_labels)}."
    logger.info(f"Generated caption: {caption}")
    return caption

# Routes
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        logger.warning("No image file provided.")
        return jsonify({"error": "No image file provided."}), 400

    image_file = request.files["image"]
    filename = f"images/{uuid.uuid4()}.jpg"
    logger.info(f"Processing file: {filename}")

    try:
        image_url = upload_to_bucket(image_file, filename)
        caption = generate_caption(image_url)
        result = {"image_url": image_url, "caption": caption}
        logger.info("Caption generation successful.", extra={"json_fields": result})
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating caption: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "OK"})

# Main
if __name__ == "__main__":
    MEMBER = "allUsers"
    ROLE = "roles/storage.objectViewer"

    try:
        add_bucket_iam_binding_with_retries(BUCKET_NAME, MEMBER, ROLE)
    except Exception as e:
        logger.error(f"Failed to set bucket permissions: {e}")
        sys.exit(1)

    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
