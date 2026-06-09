import os
import json
import sys
import uuid
from datetime import datetime

DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "finance_data.json"))

DEFAULT_CATEGORIES = {
    "Food": {"description": "Food, groceries, dining"},
    "Entertainment": {"description": "Games, movies, hobbies"},
    "Utilities": {"description": "Bills, phone, electricity, internet"},
    "Salary": {"description": "Regular job income, payroll"},
    "General": {"description": "Miscellaneous or uncategorized transactions"}
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"transactions": [], "budgets": {}, "categories": DEFAULT_CATEGORIES.copy()}
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if "transactions" not in data:
                data["transactions"] = []
            if "budgets" not in data:
                data["budgets"] = {}
            if "categories" not in data or not isinstance(data["categories"], dict) or not data["categories"]:
                data["categories"] = DEFAULT_CATEGORIES.copy()
            return data
    except Exception:
        return {"transactions": [], "budgets": {}, "categories": DEFAULT_CATEGORIES.copy()}

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
    categories = data.get("categories", {})

    # Helper function to clean category name
    def clean_cat_name(name):
        return name.strip() if name else ""

    if action == "add_transaction":
        t_type = args.get("type") # "income" or "expense"
        amount_raw = args.get("amount")
        category_raw = args.get("category", "General")
        category = clean_cat_name(category_raw)
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

        # Validate category exists
        if category not in categories:
            # Check case-insensitively
            matched_cat = None
            for key in categories:
                if key.lower() == category.lower():
                    matched_cat = key
                    break
            if matched_cat:
                category = matched_cat
            else:
                return {
                    "error": f"Category '{category}' does not exist. Available categories are: {list(categories.keys())}. "
                             f"Please create the category first using 'create_category' action."
                }

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
        breakdown = {}
        for t in filtered:
            cat = t["category"]
            breakdown.setdefault(cat, {"income": 0.0, "expense": 0.0})
            breakdown[cat][t["type"]] += t["amount"]

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
            "breakdown": breakdown
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

    # --- CATEGORY ACTIONS ---

    elif action == "create_category":
        category_raw = args.get("category")
        description = args.get("description", "")
        limit_raw = args.get("limit")

        if not category_raw:
            return {"error": "Missing 'category' parameter"}
        
        category = clean_cat_name(category_raw)
        if not category:
            return {"error": "Category name cannot be empty"}

        if category in categories:
            return {"error": f"Category '{category}' already exists"}

        categories[category] = {"description": description}
        
        if limit_raw is not None:
            try:
                limit = float(limit_raw)
                if limit < 0:
                    return {"error": "Budget limit cannot be negative"}
                budgets[category] = limit
            except ValueError:
                return {"error": "Invalid 'limit' format"}

        save_data(data)
        return {
            "success": True,
            "message": f"Created category '{category}'" + (f" with a budget of {limit:.2f}" if limit_raw is not None else ""),
            "categories": categories,
            "budgets": budgets
        }

    elif action == "get_categories" or action == "list_categories":
        current_month = datetime.today().strftime('%Y-%m-%d')[:7]
        result_cats = {}
        for cat, details in categories.items():
            limit = budgets.get(cat, 0.0)
            spent = sum(
                t["amount"] for t in transactions
                if t["type"] == "expense" and t["category"] == cat and t["date"].startswith(current_month)
            )
            result_cats[cat] = {
                "description": details.get("description", ""),
                "budget_limit": limit if cat in budgets else None,
                "spent_this_month": spent,
                "remaining_budget": max(0.0, limit - spent) if cat in budgets else None
            }
        return {
            "success": True,
            "categories": result_cats
        }

    elif action == "update_category":
        category_raw = args.get("category")
        new_name_raw = args.get("new_name")
        description = args.get("description")
        limit_raw = args.get("limit")

        if not category_raw:
            return {"error": "Missing 'category' parameter"}

        category = clean_cat_name(category_raw)
        if category not in categories:
            return {"error": f"Category '{category}' not found"}

        if description is not None:
            categories[category]["description"] = description

        if limit_raw is not None:
            try:
                limit = float(limit_raw)
                if limit < 0:
                    return {"error": "Budget limit cannot be negative"}
                budgets[category] = limit
            except ValueError:
                return {"error": "Invalid 'limit' format"}

        msg = f"Updated category '{category}'"
        
        if new_name_raw:
            new_name = clean_cat_name(new_name_raw)
            if not new_name:
                return {"error": "New category name cannot be empty"}
            if new_name in categories and new_name != category:
                return {"error": f"Category '{new_name}' already exists"}

            # Rename key
            categories[new_name] = categories.pop(category)
            
            # Update budgets
            if category in budgets:
                budgets[new_name] = budgets.pop(category)
                
            # Update existing transactions
            rename_count = 0
            for t in transactions:
                if t["category"] == category:
                    t["category"] = new_name
                    rename_count += 1
            
            msg = f"Renamed category '{category}' to '{new_name}' and updated {rename_count} transactions"
            category = new_name

        save_data(data)
        return {
            "success": True,
            "message": msg,
            "category": category,
            "details": categories[category],
            "budget": budgets.get(category)
        }

    elif action == "delete_category":
        category_raw = args.get("category")
        merge_to_raw = args.get("merge_to", "General")

        if not category_raw:
            return {"error": "Missing 'category' parameter"}

        category = clean_cat_name(category_raw)
        if category not in categories:
            return {"error": f"Category '{category}' not found"}

        if category == "General":
            return {"error": "Cannot delete the default 'General' category"}

        merge_to = clean_cat_name(merge_to_raw)
        if merge_to not in categories:
            return {"error": f"Merge-target category '{merge_to}' does not exist"}

        # Delete category details
        del categories[category]
        
        # Delete budget
        if category in budgets:
            del budgets[category]

        # Update matching transactions to target category
        merge_count = 0
        for t in transactions:
            if t["category"] == category:
                t["category"] = merge_to
                merge_count += 1

        save_data(data)
        return {
            "success": True,
            "message": f"Deleted category '{category}' and merged {merge_count} transactions into '{merge_to}'"
        }

    elif action == "set_budget":
        # Keep set_budget action for backward compatibility
        category = clean_cat_name(args.get("category"))
        limit_raw = args.get("limit")

        if not category or limit_raw is None:
            return {"error": "Missing 'category' or 'limit' parameters"}

        if category not in categories:
            return {"error": f"Category '{category}' does not exist. Please create it first."}

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
        # Keep get_budgets action for backward compatibility
        current_month = datetime.today().strftime('%Y-%m-%d')[:7]
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
