from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import (
    check_user_exists,
    create_user,
    get_transaction_summary,
    update_transaction_db,
    delete_transaction,
    get_transaction_statistics,
    get_budgets,
    insert_goal_transaction,
    transactions_per_user,
    insert_transaction,
    get_transactions_by_category,
    get_one_budget_usage,
    get_all_budget_usage,
    search_budgets,
    update_budget,
    delete_budget,
    budgets_per_user,
    get_budget_by_category,
    insert_budgets,
    insert_goals,
    fetch_goal,
    get_user_goals,
    update_goal_progress,
    update_goal_details,
    delete_goal,
    search_goals,
    get_categories,
    get_savings_category,
    get_monthly_category_summary
)
from datetime import datetime, date
from flask_bcrypt import Bcrypt
from functools import wraps
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

bcrypt = Bcrypt(app)

app.secret_key = os.getenv("SECRET_KEY")


@app.route('/')
def home():
    return render_template("index.html")


def login_required(f):
    @wraps(f)
    def protected(*args, **kwargs):

        if 'email' not in session or 'user_id' not in session:
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return protected


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone_number = request.form['phone']
        password = request.form['password']

        existing_user = check_user_exists(email)
        if not existing_user:
            hashed_password = bcrypt.generate_password_hash(
                password).decode('utf-8')
            new_user = (full_name, email, phone_number, hashed_password)
            create_user(new_user)
            flash("User created successfully", 'success')
            return redirect(url_for('login'))
        else:
            flash("User already exists,please login instead", 'danger')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        registered_user = check_user_exists(email)
        if not registered_user:
            flash("User doesn't exist,please register", 'danger')
        else:
            if bcrypt.check_password_hash(registered_user[-2], password):
                session['email'] = email
                session['user_id'] = registered_user[0]
                flash("Login successful", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect password,try again", 'danger')

    return render_template('login.html')


@app.route("/dashboard")
@login_required
def dashboard():

    user_id = session["user_id"]

    # -------------------------------
    # Get Data
    # -------------------------------

    budgets = get_all_budget_usage(user_id)
    goals = get_user_goals(user_id)
    transactions = transactions_per_user(user_id)

    statistics = get_transaction_statistics(user_id)
    summary = get_transaction_summary(user_id)
    monthly_summary = get_monthly_category_summary(user_id)

    # -------------------------------
    # Overview Cards
    # -------------------------------

    transaction_count = len(transactions)

    highest_category = statistics["highest_category"]

    # -------------------------------
    # Budget Summary
    # -------------------------------

    budget_list = []

    total_limit = 0
    total_spent = 0
    budgets_on_track = 0

    for budget in budgets:

        limit_amount = float(budget[4])
        spent = float(budget[5])
        remaining = float(budget[6])

        if limit_amount > 0:
            percentage = round((spent / limit_amount) * 100)
        else:
            percentage = 0

        if spent <= limit_amount:
            budgets_on_track += 1

        total_limit += limit_amount
        total_spent += spent

        budget_list.append({
            "category": budget[2],
            "limit": limit_amount,
            "spent": spent,
            "remaining": remaining,
            "percentage": percentage
        })

    total_budgets = len(budget_list)

    if total_limit > 0:
        budget_usage = round((total_spent / total_limit) * 100)
    else:
        budget_usage = 0

    # -------------------------------
    # Goal Summary
    # -------------------------------
    completed_goals = 0
    active_goals = 0
    overdue_goals = 0

    today = date.today()

    next_goal = None

    for goal in goals:

        target = float(goal[2])
        saved = float(goal[3])
        deadline = goal[4]

        if saved >= target:

            completed_goals += 1

        elif deadline < today:

            overdue_goals += 1

        else:

            active_goals += 1

            # Find the closest upcoming active goal
            if next_goal is None:
                next_goal = goal

    total_goals = len(goals)

    completion_percentage = (
        round((completed_goals / total_goals) * 100)
        if total_goals > 0 else 0
    )

    # -------------------------------
    # Income vs Expenses Chart
    # -------------------------------

    chart_months = [datetime.now().strftime("%B")]

    monthly_income_chart = [float(summary["income"])]
    monthly_expense_chart = [float(summary["expenses"])]

    # -------------------------------
    # Spending by Category Chart
    # -------------------------------

    categories = []
    category_totals = []

    for row in monthly_summary:

        categories.append(row[0])
        category_totals.append(float(row[1]))

    # -------------------------------
    # Recent Transactions
    # -------------------------------

    recent_transactions = transactions[:5]
    

    # -------------------------------
    # Render Template
    # -------------------------------

    return render_template(

        "dashboard.html",

        current_month=datetime.now().strftime("%B %Y"),

        transaction_count=transaction_count,

        budget_usage=budget_usage,
        budgets_on_track=budgets_on_track,
        total_budgets=total_budgets,

        completed_goals=completed_goals,
        active_goals=active_goals,
        overdue_goals=overdue_goals,
        total_goals=total_goals,
        completion_percentage=completion_percentage,
        next_goal=next_goal,

        highest_category=highest_category,

        budgets=budget_list,

        recent_transactions=recent_transactions,

        chart_months=chart_months,
        monthly_income_chart=monthly_income_chart,
        monthly_expense_chart=monthly_expense_chart,

        categories=categories,
        category_totals=category_totals

    )


@app.route('/transactions')
@login_required
def transactions():
    user_id = session["user_id"]

    category_id = request.args.get("category_id")

    statistics = get_transaction_statistics(user_id)


    if category_id:
        transactions = get_transactions_by_category(user_id, category_id)
    else:
        transactions = transactions_per_user(user_id)


    categories = get_categories()

    

    # For the summary cards
    summary = get_transaction_summary(user_id)

    # For the progress bars
    monthly_summary = get_monthly_category_summary(user_id)
    total_spent = sum(row[1] for row in monthly_summary)

    category_summary = []

    for category, amount in monthly_summary:
        percentage = round((amount / total_spent) * 100) if total_spent else 0
        category_summary.append((category, amount, percentage))

    return render_template("transactions.html", transactions=transactions,categories=categories, category_summary=category_summary,
        current_month=datetime.now().strftime("%B"),monthly_income=summary["income"],
        monthly_expenses=summary["expenses"], net_savings=summary["net_savings"],
        transaction_count=summary["transaction_count"],highest_category=statistics["highest_category"],
        highest_income_category=statistics["highest_income_category"],largest_transaction=statistics["largest_transaction"],
        most_used_category=statistics["most_used_category"])


@app.route("/add_transaction", methods=['GET', 'POST'])
@login_required
def add_transactions():
    user_id = session["user_id"]
    if request.method == 'POST':

        category_id = request.form["category_id"]
        transaction_type = request.form["type"]
        amount = request.form["amount"]
        description = request.form["description"]
        transaction_date = request.form["transaction_date"]

        insert_transaction(
            user_id,
            category_id,
            transaction_type,
            amount,
            description,
            transaction_date
        )

    return redirect(url_for("transactions"))

@app.route("/update_transaction", methods=["POST"])
@login_required
def update_transaction():
    user_id = session["user_id"]

    transaction_id = request.form["transaction_id"]
    category_id = request.form["category_id"]
    transaction_type = request.form["type"]
    amount = request.form["amount"]
    description = request.form["description"]
    transaction_date = request.form["transaction_date"]

    update_transaction_db(
        transaction_id,
        user_id,
        category_id,
        transaction_type,
        amount,
        description,
        transaction_date
    )

    return redirect(url_for("transactions"))


@app.route("/delete_transaction/<int:transaction_id>", methods=["POST"])
@login_required
def delete_transaction_route(transaction_id):

    delete_transaction(transaction_id, session["user_id"])

    flash("Transaction deleted successfully!", "success")

    return redirect(url_for("transactions"))



@app.route("/budgets")
@login_required
def budgets():

    user_id = session["user_id"]

    search = request.args.get("search", "").strip()

    # Categories for the Add Budget modal
    categories = get_categories()

    # Budget usage for all categories
    if search:
        budgets = search_budgets(user_id, search)
    else:
        budgets = get_all_budget_usage(user_id)

    budget_data = []

    total_budget = 0
    total_spent = 0
    over_budget = 0

    largest_category = "N/A"
    largest_spent = 0

    for budget in budgets:

        (
            budget_id,
            category_id,
            category_name,
            month,
            limit_amount,
            spent,
            remaining
        ) = budget

        # Calculate progress percentage
        progress = (spent / limit_amount * 100) if limit_amount else 0

        # Determine status and colour
        if progress < 80:
            status = "On Track"
            color = "success"

        elif progress < 100:
            status = "Almost Over Budget"
            color = "warning"

        else:
            status = "Over Budget"
            color = "danger"
            over_budget += 1

        # Track largest spending category
        if spent > largest_spent:
            largest_spent = spent
            largest_category = category_name

        total_budget += limit_amount
        total_spent += spent

        budget_data.append({

            "id": budget_id,
            "category_id": category_id,
            "category": category_name,
            "month": month,
            "limit": limit_amount,
            "spent": spent,
            "remaining": remaining,

            # Cap the progress bar at 100%
            "progress": min(progress, 100),

            # Display the real percentage
            "actual_progress": progress,

            "status": status,
            "color": color

        })

    total_remaining = total_budget - total_spent

    return render_template("budgets.html",budgets=budget_data,categories=categories,
        total_budget=total_budget,total_spent=total_spent,total_remaining=total_remaining,
        over_budget=over_budget,largest_category=largest_category)



@app.route("/add_budget", methods=["POST"])
@login_required
def add_budget():

    user_id = session["user_id"]

    category_id = request.form["category_id"]
    limit_amount = request.form["limit_amount"]
    month = request.form["month"]

    month = month + "-01"   

    insert_budgets(
        user_id,
        category_id,
        limit_amount,
        month
    )

    return redirect(url_for("budgets"))


@app.route("/update_budget/<int:budget_id>", methods=["POST"])
@login_required
def update_budget_route(budget_id):

    limit_amount = request.form["limit_amount"]

    update_budget(
        budget_id,
        limit_amount
    )

    flash("Budget updated successfully!", "success")

    return redirect(url_for("budgets"))


@app.route("/delete_budget/<int:budget_id>", methods=["POST"])
@login_required
def delete_budget_route(budget_id):

    delete_budget(budget_id)

    flash("Budget deleted successfully!", "success")

    return redirect(url_for("budgets"))


@app.route("/goals")
@login_required
def goals():

    user_id = session["user_id"]

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status")

    if search:
        goals = search_goals(user_id, search)
    else:
        goals = get_user_goals(user_id)

    goals_with_progress = []

    active_goals = 0
    completed_goals = 0

    total_saved = 0
    total_target = 0

    today = date.today()
    for goal in goals:

        goal_id = goal[0]
        goal_name = goal[1]
        target_amount = float(goal[2])
        saved_amount = float(goal[3])
        deadline = goal[4]

        if target_amount > 0:
            progress = round((saved_amount / target_amount) * 100)
        else:
            progress = 0

        # Determine goal status
        if saved_amount >= target_amount:
            status = "Completed"

        elif deadline < today:
            status = "Overdue"

        elif (deadline - today).days <= 30:
            status = "Due Soon"

        else:
            status = "Active"

        goal_data ={
            "id": goal_id,
            "goal_name": goal_name,
            "target_amount": target_amount,
            "saved_amount": saved_amount,
            "deadline": deadline,
            "progress": progress,
            "status": status
        }

        if status_filter is None or status == status_filter:
            goals_with_progress.append(goal_data)

        total_saved += saved_amount
        total_target += target_amount

        if status == "Completed":
            completed_goals += 1
        else:
            active_goals += 1
            
    # Overall progress across ALL goals
    if total_target > 0:
        overall_progress = round((total_saved / total_target) * 100)
    else:
        overall_progress = 0

    return render_template(
        "goals.html",
        goals=goals_with_progress,
        active_goals=active_goals,
        completed_goals=completed_goals,
        total_saved=total_saved,
        overall_progress=overall_progress
    )

@app.route("/add_goal", methods=["POST"])
@login_required
def add_goal():
    user_id = session["user_id"]

    goal_name = request.form["goal_name"]
    target_amount = request.form["target_amount"]
    saved_amount = request.form["saved_amount"]
    deadline = request.form["deadline"]

    values = (
        user_id,
        goal_name,
        target_amount,
        saved_amount,
        deadline
    )

    insert_goals(values)

    return redirect(url_for("goals"))

# For editing goal details.
@app.route("/update_goal/<int:goal_id>", methods=["POST"])
@login_required
def update_goal(goal_id):

    user_id = session["user_id"]

    goal_name = request.form["goal_name"]
    target_amount = float(request.form["target_amount"])
    saved_amount = float(request.form["saved_amount"])
    deadline = request.form["deadline"]

    # Retrieve the goal before updating it
    goal = fetch_goal(goal_id)

    old_goal_name = goal[0]
    old_saved_amount = float(goal[1])

    # Calculate how much the saved amount changed
    difference = saved_amount - old_saved_amount

    # Update the goal
    values = (
        goal_name,
        target_amount,
        saved_amount,
        deadline,
        goal_id
    )

    update_goal_details(values)

    # If money was added, record it as a transaction
    if difference > 0:

        savings_category = get_savings_category()

        if savings_category is not None:

            insert_goal_transaction(
                user_id,
                savings_category,
                difference,
                f"Goal Contribution - {goal_name}"
            )

    return redirect(url_for("goals"))

@app.route("/delete_goal/<int:goal_id>", methods=["POST"])
@login_required
def delete_goal_route(goal_id):

    delete_goal(goal_id, session["user_id"])

    flash("Goal deleted successfully!", "success")

    return redirect(url_for("goals"))

# for when I eventually add an "Add Savings" button:
@app.route("/update_goal_progress", methods=["POST"])
@login_required
def update_goal_progress():

    goal_id = request.form["goal_id"]
    amount = request.form["amount"]

    update_goal_progress(goal_id, amount)

    return redirect(url_for("goals"))



@app.route('/logout')
def logout():
    session.pop('email', None)
    flash("Logged out successfully", 'success')
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
