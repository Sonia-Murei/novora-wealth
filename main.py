from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import (
    check_user_exists,
    create_user,
    get_transactions,
    get_budgets,
    insert_goal_transaction,
    transactions_per_user,
    insert_transaction,
    get_one_budget_usage,
    get_all_budget_usage,
    budgets_per_user,
    get_budget_by_category,
    insert_budgets,
    insert_goals,
    fetch_goal,
    get_user_goals,
    update_goal_progress,
    update_goal_details,
    search_goals,
    get_categories,
    get_savings_category
)
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

    print(session)

    # user_id = session["user_id"] -> Keeps track of which user is currently logged in
    user_id = session["user_id"]

    budgets = get_all_budget_usage(user_id)
    goals = get_user_goals(user_id)
    transactions = transactions_per_user(user_id)

    return render_template("dashboard.html", budgets=budgets, goals=goals, transactions=transactions)


@app.route('/transactions')
@login_required
def transactions():
    transactions_data = get_transactions()
    categories = get_categories()
    return render_template("transactions.html", transactions_data=transactions_data, categories=categories)


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


@app.route('/budgets')
@login_required
def budgets():
    print(session)
    user_id = session["user_id"]

    budgets_data = get_all_budget_usage(user_id)
    return render_template("budgets.html", budgets_data=budgets_data)


@app.route("/add_budget", methods=["POST"])
@login_required
def add_budget():

    user_id = session["user_id"]

    category_id = request.form["category_id"]
    limit_amount = request.form["limit_amount"]
    month = request.form["month"]

    insert_budgets(
        user_id,
        category_id,
        limit_amount,
        month
    )

    return redirect(url_for("budgets"))


@app.route("/goals")
@login_required
def goals():

    user_id = session["user_id"]

    search = request.args.get("search", "").strip()

    if search:
        goals = search_goals(user_id, search)
    else:
        goals = get_user_goals(user_id)

    goals_with_progress = []

    active_goals = 0
    completed_goals = 0

    total_saved = 0
    total_target = 0

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

        goals_with_progress.append({
            "id": goal_id,
            "goal_name": goal_name,
            "target_amount": target_amount,
            "saved_amount": saved_amount,
            "deadline": deadline,
            "progress": progress
        })

        total_saved += saved_amount
        total_target += target_amount

        if progress >= 100:
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

# for when I eventually add an "Add Savings" button:
@app.route("/update_goal_progress", methods=["POST"])
@login_required
def update_goal_progress():

    goal_id = request.form["goal_id"]
    amount = request.form["amount"]

    update_goal_progress(goal_id, amount)

    return redirect(url_for("goals"))


@app.route("/reports")
def reports():

    user_id = session["user_id"]

    all_budget_data = get_all_budget_usage(user_id)

    return render_template("reports.html", all_budget_data=all_budget_data
                           )


@app.route('/logout')
def logout():
    session.pop('email', None)
    flash("Logged out successfully", 'success')
    return redirect(url_for('login'))


app.run(debug=True)
