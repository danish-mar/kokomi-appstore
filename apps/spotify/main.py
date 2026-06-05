import json
import sys

def run(args):
    action = args.get("action", "status")
    track = args.get("track", "")
    
    if action == "play":
        return {
            "success": True,
            "status": "playing",
            "track": track or "River Flows in You",
            "artist": "Yiruma",
            "volume": 75
        }
    elif action == "pause":
        return {
            "success": True,
            "status": "paused",
            "track": "River Flows in You",
            "artist": "Yiruma"
        }
    
    # Default status
    return {
        "status": "paused",
        "device": "MacBook Pro",
        "active": True
    }

if __name__ == "__main__":
    try:
        args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    except Exception:
        args = {}
    print(json.dumps(run(args)))
