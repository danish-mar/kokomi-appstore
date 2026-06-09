import os
import json
import sys
import uuid
from datetime import datetime

DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "finance_data.json"))

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"transactions": [], "budgets": {}}
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if "transactions" not in data:
                data["transactions"] = []
            if "budgets" not in data:
                data["budgets"] = {}
            return data
    except Exception:
        return {"transactions": [], "budgets": {}}

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def run(args):
    action = args.get("action")
    if not action:
        return {"error": "Missing action parameter"}

    data = load_data()
    transactions = data.get("transactions", [])
    budgets = data.get("budgets", {})

    if action == "add_transaction":
        t_type = args.get("type") # "income" or "expense"
        amount_raw = args.get("amount")
        category = args.get("category", "General")
        description = args.get("description", "")
        date_str = args.get("date") # "YYYY-MM-DD" or empty for today

        if not t_type or amount_raw is None:
            return {"error": "Missing 'type' or 'amount' parameters"}

        if t_type not in ("income", "expense"):
            return {"error": "'type' must be either 'income' or 'expense'"}

        try:
            amount = float(amount_raw)
            if amount <= 0:
                return {"error": "'amount' must be positive"}
        except ValueError:
            return {"error": "Invalid 'amount' format"}

        if not date_str:
            date_str = datetime.today().strftime('%Y-%m-%d')
        else:
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return {"error": "Invalid 'date' format, must be YYYY-MM-DD"}

        tx_id = f"tx_{uuid.uuid4().hex[:6]}"
        new_tx = {
            "id": tx_id,
            "type": t_type,
            "amount": amount,
            "category": category,
            "description": description,
            "date": date_str,
            "timestamp": datetime.now().isoformat()
        }
        transactions.append(new_tx)
        save_data(data)

        # Budget alert check for expenses
        alert = None
        if t_type == "expense" and category in budgets:
            limit = budgets[category]
            current_month = date_str[:7] # YYYY-MM
            month_expenses = sum(
                t["amount"] for t in transactions
                if t["type"] == "expense" and t["category"] == category and t["date"].startswith(current_month)
            )
            if month_expenses > limit:
                alert = f"⚠️ BUDGET EXCEEDED: Expenses for '{category}' this month ({month_expenses:.2f}) exceed budget limit ({limit:.2f})!"
            elif month_expenses >= limit * 0.9:
                alert = f"⚠️ BUDGET WARNING: Expenses for '{category}' this month ({month_expenses:.2f}) are nearing the limit ({limit:.2f})!"

        return {
            "success": True,
            "message": f"Added {t_type} of {amount:.2f} under {category}",
            "transaction": new_tx,
            "budget_alert": alert
        }

    elif action == "get_summary":
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        category_filter = args.get("category")

        filtered = transactions
        if start_date:
            filtered = [t for t in filtered if t["date"] >= start_date]
        if end_date:
            filtered = [t for t in filtered if t["date"] <= end_date]
        if category_filter:
            filtered = [t for t in filtered if t["category"].lower() == category_filter.lower()]

        total_income = sum(t["amount"] for t in filtered if t["type"] == "income")
        total_expense = sum(t["amount"] for t in filtered if t["type"] == "expense")
        net_savings = total_income - total_expense

        # Breakdown by category
        categories = {}
        for t in filtered:
            cat = t["category"]
            categories.setdefault(cat, {"income": 0.0, "expense": 0.0})
            categories[cat][t["type"]] += t["amount"]

        return {
            "success": True,
            "period": {
                "start": start_date or "First Transaction",
                "end": end_date or "Latest Transaction"
            },
            "summary": {
                "total_income": total_income,
                "total_expense": total_expense,
                "net_savings": net_savings
            },
            "breakdown": categories
        }

    elif action == "list_transactions":
        limit = args.get("limit", 20)
        t_type = args.get("type")
        category = args.get("category")

        filtered = transactions
        if t_type:
            filtered = [t for t in filtered if t["type"] == t_type]
        if category:
            filtered = [t for t in filtered if t["category"].lower() == category.lower()]

        # Sort by date descending
        filtered.sort(key=lambda x: x["date"], reverse=True)
        result = filtered[:limit]

        return {
            "success": True,
            "count": len(result),
            "total_records": len(filtered),
            "transactions": result
        }

    elif action == "delete_transaction":
        tx_id = args.get("id")
        if not tx_id:
            return {"error": "Missing transaction 'id' parameter"}

        initial_len = len(transactions)
        transactions = [t for t in transactions if t["id"] != tx_id]
        
        if len(transactions) == initial_len:
            return {"error": f"Transaction '{tx_id}' not found"}

        data["transactions"] = transactions
        save_data(data)
        return {"success": True, "message": f"Deleted transaction '{tx_id}'"}

    elif action == "set_budget":
        category = args.get("category")
        limit_raw = args.get("limit")

        if not category or limit_raw is None:
            return {"error": "Missing 'category' or 'limit' parameters"}

        try:
            limit = float(limit_raw)
            if limit < 0:
                return {"error": "'limit' cannot be negative"}
        except ValueError:
            return {"error": "Invalid 'limit' format"}

        budgets[category] = limit
        save_data(data)
        return {"success": True, "message": f"Set budget for '{category}' to {limit:.2f}", "budgets": budgets}

    elif action == "get_budgets":
        current_month = datetime.today().strftime('%Y-%m-%d')[:7] # YYYY-MM
        status = {}
        for cat, limit in budgets.items():
            spent = sum(
                t["amount"] for t in transactions
                if t["type"] == "expense" and t["category"] == cat and t["date"].startswith(current_month)
            )
            status[cat] = {
                "limit": limit,
                "spent": spent,
                "remaining": max(0.0, limit - spent),
                "percent_spent": (spent / limit) * 100 if limit > 0 else 0.0
            }
        return {
            "success": True,
            "month": current_month,
            "budgets": status
        }

    else:
        return {"error": f"Unknown action: {action}"}

if __name__ == "__main__":
    try:
        args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    except Exception:
        args = {}
    print(json.dumps(run(args)))
