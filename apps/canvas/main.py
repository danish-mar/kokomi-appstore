import os
import sys
import json
import urllib.parse
import requests

# We locate the data/uploads directory relative to the file.
# The app will run in data/apps/canvas/main.py.
# So:
# os.path.dirname(__file__) -> data/apps/canvas
# .. -> data/apps
# ../.. -> data
# ../../uploads -> data/uploads
UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))

def run(args):
    action = args.get("action")
    if not action:
        return {"error": "Missing action parameter"}

    os.makedirs(UPLOADS_DIR, exist_ok=True)

    if action == "save_diagram":
        name = args.get("name")
        code = args.get("code")
        should_render = args.get("render", True)

        if not name or not code:
            return {"error": "Missing name or code parameter"}

        # sanitize name to prevent path traversal
        safe_name = "".join([c for c in name if c.isalnum() or c in ("-", "_")]).strip()
        if not safe_name:
            return {"error": "Invalid diagram name"}

        mermaid_filename = f"canvas-{safe_name}.mermaid"
        mermaid_path = os.path.join(UPLOADS_DIR, mermaid_filename)

        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write(code)

        result = {
            "success": True,
            "message": f"Successfully saved Mermaid diagram source to {mermaid_filename}",
            "name": safe_name,
            "mermaid_path": f"/uploads/{mermaid_filename}"
        }

        if should_render:
            try:
                encoded_code = urllib.parse.quote(code)
                # quickchart.io endpoint
                url = f"https://quickchart.io/mermaid?graph={encoded_code}"
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    image_filename = f"canvas-{safe_name}.png"
                    image_path = os.path.join(UPLOADS_DIR, image_filename)
                    with open(image_path, "wb") as f:
                        f.write(resp.content)
                    result["image_path"] = f"/uploads/{image_filename}"
                    result["image_url"] = f"/uploads/{image_filename}"
                    result["message"] += f" and rendered image to {image_filename}"
                else:
                    result["warning"] = f"Failed to render diagram image. HTTP Status: {resp.status_code}"
            except Exception as e:
                result["warning"] = f"Failed to render diagram image: {str(e)}"

        return result

    elif action == "read_diagram":
        name = args.get("name")
        if not name:
            return {"error": "Missing name parameter"}

        safe_name = "".join([c for c in name if c.isalnum() or c in ("-", "_")]).strip()
        mermaid_filename = f"canvas-{safe_name}.mermaid"
        mermaid_path = os.path.join(UPLOADS_DIR, mermaid_filename)

        if not os.path.exists(mermaid_path):
            return {"error": f"Diagram '{safe_name}' not found"}

        with open(mermaid_path, "r", encoding="utf-8") as f:
            code = f.read()

        image_filename = f"canvas-{safe_name}.png"
        image_path = os.path.join(UPLOADS_DIR, image_filename)
        has_image = os.path.exists(image_path)

        return {
            "success": True,
            "name": safe_name,
            "code": code,
            "mermaid_path": f"/uploads/{mermaid_filename}",
            "image_path": f"/uploads/{image_filename}" if has_image else None
        }

    elif action == "list_diagrams":
        diagrams = []
        if os.path.exists(UPLOADS_DIR):
            for filename in os.listdir(UPLOADS_DIR):
                if filename.startswith("canvas-") and filename.endswith(".mermaid"):
                    name = filename[len("canvas-"):-len(".mermaid")]
                    image_filename = f"canvas-{name}.png"
                    has_image = os.path.exists(os.path.join(UPLOADS_DIR, image_filename))
                    diagrams.append({
                        "name": name,
                        "mermaid_path": f"/uploads/{filename}",
                        "image_path": f"/uploads/{image_filename}" if has_image else None
                    })
        return {
            "success": True,
            "diagrams": diagrams
        }

    elif action == "delete_diagram":
        name = args.get("name")
        if not name:
            return {"error": "Missing name parameter"}

        safe_name = "".join([c for c in name if c.isalnum() or c in ("-", "_")]).strip()
        mermaid_filename = f"canvas-{safe_name}.mermaid"
        image_filename = f"canvas-{safe_name}.png"

        mermaid_path = os.path.join(UPLOADS_DIR, mermaid_filename)
        image_path = os.path.join(UPLOADS_DIR, image_filename)

        deleted = []
        if os.path.exists(mermaid_path):
            os.remove(mermaid_path)
            deleted.append(mermaid_filename)
        if os.path.exists(image_path):
            os.remove(image_path)
            deleted.append(image_filename)

        if deleted:
            return {
                "success": True,
                "message": f"Successfully deleted: {', '.join(deleted)}"
            }
        else:
            return {
                "success": False,
                "message": "No files found to delete"
            }

    else:
        return {"error": f"Unknown action: {action}"}

if __name__ == "__main__":
    try:
        args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    except Exception:
        args = {}
    print(json.dumps(run(args)))
