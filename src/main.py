import os
import shutil
import subprocess

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#Find local blender file location. TODO: if none found, prompt user to find it themselves
def find_blender():
    blender = shutil.which("blender")
    if blender:
        return blender

    candidates = [
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/usr/bin/blender",
        "/usr/local/bin/blender",
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return None

blender_path = find_blender()

print(f"blender path: {blender_path}")

#Get file from post, and then run blender headlessly
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    mtl = request.files["mtl"]
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    abs_path = os.path.abspath(path)
    file.save(path)
    mtl.save(os.path.join(UPLOAD_FOLDER, mtl.filename))

    script_path = os.path.join(os.path.dirname(__file__), "process.py")

    #Delete old progress file
    progress_path = os.path.join(UPLOAD_FOLDER, "progress.txt")
    if os.path.exists(progress_path):
        os.remove(progress_path)

    original_path = request.form.get("originalPath")
    output_dir = os.path.dirname(original_path)

    #Run a blender program headlessly
    subprocess.run([
        blender_path,
        "--background",
        "--python", script_path,
        "--", abs_path, output_dir
    ])
    png_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, file.filename.replace(".obj", "_baked.png")))
    fbx_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, file.filename.replace(".obj", "_baked.fbx")))

    return jsonify({
        "png": png_path,
        "fbx": fbx_path
    })

@app.route("/progress", methods=["GET"])
def progress():
    progress_path = os.path.join(UPLOAD_FOLDER, "progress.txt")

    try:
        with open(progress_path) as f:
            lines = f.read().splitlines()
        if len(lines) < 2:
            return jsonify({"value": 0, "message": "..."})
        return jsonify({"value": int(lines[0]), "message": lines[1]})
    except (FileNotFoundError, ValueError):
        return jsonify({"value": 0, "message": "..."})

if __name__ == "__main__":
    app.run(debug=True)