import os
import json
import sys
import uuid

DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "todo_lists.json"))

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"lists": {}}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"lists": {}}

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def find_task_recursive(tasks, task_id):
    for t in tasks:
        if t["id"] == task_id:
            return t
        found = find_task_recursive(t.get("subtasks", []), task_id)
        if found:
            return found
    return None

def remove_task_recursive(tasks, task_id):
    for i, t in enumerate(tasks):
        if t["id"] == task_id:
            return tasks.pop(i)
        removed = remove_task_recursive(t.get("subtasks", []), task_id)
        if removed:
            return removed
    return None

def run(args):
    action = args.get("action")
    if not action:
        return {"error": "Missing action parameter"}

    data = load_data()
    lists = data.get("lists", {})

    if action == "create_list":
        list_name = args.get("list_name")
        if not list_name:
            return {"error": "Missing list_name"}
        if list_name in lists:
            return {"message": f"List '{list_name}' already exists", "lists": lists}
        lists[list_name] = {"name": list_name, "tasks": []}
        save_data(data)
        return {"success": True, "message": f"List '{list_name}' created", "lists": lists}

    elif action == "get_lists":
        return {"lists": lists}

    elif action == "add_task":
        list_name = args.get("list_name")
        title = args.get("title")
        if not list_name or not title:
            return {"error": "Missing list_name or title"}
        if list_name not in lists:
            lists[list_name] = {"name": list_name, "tasks": []}

        new_task = {
            "id": f"task_{uuid.uuid4().hex[:6]}",
            "title": title,
            "description": args.get("description", ""),
            "status": "pending",
            "subtasks": []
        }

        parent_task_id = args.get("parent_task_id")
        if parent_task_id:
            parent = find_task_recursive(lists[list_name]["tasks"], parent_task_id)
            if not parent:
                return {"error": f"Parent task '{parent_task_id}' not found in list '{list_name}'"}
            if "subtasks" not in parent:
                parent["subtasks"] = []
            parent["subtasks"].append(new_task)
            message = f"Subtask '{title}' added under parent '{parent_task_id}'"
        else:
            lists[list_name]["tasks"].append(new_task)
            message = f"Task '{title}' added to list '{list_name}'"

        save_data(data)
        return {"success": True, "message": message, "task": new_task, "lists": lists}

    elif action == "update_task":
        list_name = args.get("list_name")
        task_id = args.get("task_id")
        if not list_name or not task_id:
            return {"error": "Missing list_name or task_id"}
        if list_name not in lists:
            return {"error": f"List '{list_name}' not found"}

        task = find_task_recursive(lists[list_name]["tasks"], task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found in list '{list_name}'"}

        if "status" in args:
            task["status"] = args["status"]
        if "title" in args:
            task["title"] = args["title"]
        if "description" in args:
            task["description"] = args["description"]

        save_data(data)
        return {"success": True, "message": f"Task '{task_id}' updated", "task": task, "lists": lists}

    elif action == "delete_task":
        list_name = args.get("list_name")
        task_id = args.get("task_id")
        if not list_name or not task_id:
            return {"error": "Missing list_name or task_id"}
        if list_name not in lists:
            return {"error": f"List '{list_name}' not found"}

        removed = remove_task_recursive(lists[list_name]["tasks"], task_id)
        if not removed:
            return {"error": f"Task '{task_id}' not found in list '{list_name}'"}

        save_data(data)
        return {"success": True, "message": f"Task '{task_id}' deleted", "lists": lists}

    elif action == "delete_list":
        list_name = args.get("list_name")
        if not list_name:
            return {"error": "Missing list_name"}
        if list_name not in lists:
            return {"error": f"List '{list_name}' not found"}
        del lists[list_name]
        save_data(data)
        return {"success": True, "message": f"List '{list_name}' deleted", "lists": lists}

    else:
        return {"error": f"Unknown action: {action}"}

if __name__ == "__main__":
    try:
        args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    except Exception:
        args = {}
    print(json.dumps(run(args)))
