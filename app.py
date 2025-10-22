import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient, ContentSettings
from werkzeug.utils import secure_filename

from pathlib import Path
from dotenv import load_dotenv

# Point directly to the .env file in your project folder
env_path = Path("/Users/Anh/Desktop/DS 2022/case07/.env")
load_dotenv(dotenv_path=env_path, override=True)

# Load configuration
STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")
IMAGES_CONTAINER = os.getenv("IMAGES_CONTAINER", "lanternfly-images")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# Initialize Azure Blob client
if AZURE_STORAGE_CONNECTION_STRING:
    bsc = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
elif STORAGE_ACCOUNT_URL:
    bsc = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL)
else:
    raise RuntimeError("Missing Azure Storage credentials.")

cc = bsc.get_container_client(IMAGES_CONTAINER)

# Ensure container exists and is public-read
try:
    cc.create_container(public_access="container")
except Exception:
    pass  # likely already exists

app = Flask(__name__)

# ---- Routes ----

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/v1/upload")
def upload():
    if "file" not in request.files:
        return jsonify(ok=False, error="No file field found"), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify(ok=False, error="No file selected"), 400

    filename = secure_filename(f.filename)
    if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return jsonify(ok=False, error="Only image files are allowed"), 400

    blob_name = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}-{filename}"
    try:
        blob_client = cc.get_blob_client(blob_name)
        blob_client.upload_blob(
            f.read(),
            overwrite=True,
            content_settings=ContentSettings(content_type=f.mimetype)
        )
        return jsonify(ok=True, url=blob_client.url)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.get("/api/v1/gallery")
def gallery():
    try:
        urls = [f"{cc.url}/{b.name}" for b in cc.list_blobs()]
        urls.sort(reverse=True)
        return jsonify(ok=True, gallery=urls)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.get("/health")
def health():
    return jsonify(ok=True, status="healthy"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)