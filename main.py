from flask import Flask, render_template,request,redirect,url_for,flash,session
from database import (
    check_user_exists, 
    create_user,
    get_transactions,
    get_budgets,
    transactions_per_user, 
    insert_transaction,
    get_one_budget_usage,
    get_all_budget_usage,
    budgets_per_user,
    get_budget_by_category,
    insert_budgets,
    get_goals,
    get_user_goals,
    update_goal_progress,
    get_categories
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
    def protected(*args,**kwargs):

        if 'email' not in session or 'user_id' not in session:
            return redirect(url_for('login'))
        
        return f(*args,**kwargs)
    return protected

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone_number = request.form['phone']
        password = request.form['password']

        existing_user = check_user_exists(email)
        if not existing_user:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = (full_name,email,phone_number,hashed_password)
            create_user(new_user)
            flash("User created successfully",'success')
            return redirect(url_for('login'))
        else:
            flash("User already exists,please login instead",'danger')
        
    return render_template('register.html')


@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        registered_user = check_user_exists(email)
        if not registered_user:
            flash("User doesn't exist,please register",'danger')
        else:
            if bcrypt.check_password_hash(registered_user[-2],password):
                session['email'] = email
                session['user_id'] = registered_user[0]
                flash("Login successful",'success')
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect password,try again",'danger')
    
    return render_template('login.html')

@app.route("/dashboard")
@login_required
def dashboard():

    print(session)

    user_id = session["user_id"] #user_id = session["user_id"] -> Keeps track of which user is currently logged in

    budgets = get_all_budget_usage(user_id)
    goals = get_user_goals(user_id)
    transactions = transactions_per_user(user_id)

    return render_template("dashboard.html", budgets = budgets, goals = goals, transactions = transactions)

@app.route('/transactions')
@login_required
def transactions():
    transactions_data = get_transactions()
    categories = get_categories()
    return render_template("transactions.html", transactions_data = transactions_data, categories = categories)

@app.route("/add_transaction", methods=['GET','POST'])
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

    budgets_data =  get_all_budget_usage(user_id)
    return render_template("budgets.html", budgets_data = budgets_data)

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

@app.route('/goals')
@login_required
def goals():
    user_id = session["user_id"]

    goals_data = get_user_goals(user_id)
    return render_template("goals.html", goals_data = goals_data)

@app.route("/add_goal", methods=['GET','POST'])
@login_required
def update_goal(goal_id):
    if request.method == 'POST':

        goal_id = request.form["goal_id"]
        amount = request.form["amount"]

        update_goal_progress(goal_id, amount)

    return redirect(url_for("goals"))

@app.route("/reports")
def reports():

    user_id = session["user_id"]

    all_budget_data = get_all_budget_usage(user_id)

    return render_template("reports.html",all_budget_data = all_budget_data
    )

@app.route('/logout')
def logout():
    session.pop('email',None)
    flash("Logged out successfully",'success')
    return redirect(url_for('login'))


app.run(debug=True)