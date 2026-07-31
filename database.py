import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    dbname=os.getenv("DB_NAME")
)

cur = conn.cursor()

# Inserts transactions from goal edits
def insert_goal_transaction(user_id, category_id, amount, description):

    cur.execute("""
        INSERT INTO transactions
        (user_id,category_id,type,amount,description,transaction_date)
        VALUES(%s, %s, %s, %s, %s, %s)""", (
        user_id,
        category_id,
        "income",
        amount,
        description,
        date.today()
    ))

    conn.commit()
# Transactions Queries:

def get_transactions():
    cur.execute("select * from transactions ORDER BY transaction_date DESC;")
    transactions = cur.fetchall()
    return transactions

def insert_transaction(user_id, category_id, transaction_type, amount, description, transaction_date):
    cur.execute("""INSERT INTO transactions
        (user_id, category_id, type, amount, description, transaction_date)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        user_id,
        category_id,
        transaction_type,
        amount,
        description,
        transaction_date
    ))

    conn.commit()

def transactions_per_user(user_id):
    cur.execute("""SELECT 
                t.id,t.category_id, t.type, t.amount,
                t.description, t.transaction_date, c.category_name
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.user_id = %s ORDER BY t.transaction_date DESC
            """, (user_id,))
    user_transactions = cur.fetchall()
    return user_transactions

def get_transactions_by_category(user_id, category_id):

    cur.execute("""SELECT t.id, c.category_name, t.type,
            t.amount, t.description, t.transaction_date
            FROM transactions t JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = %s AND t.category_id = %s
            ORDER BY t.transaction_date DESC""", (user_id, category_id))

    return cur.fetchall()

    # NB: (user_id) is a tuple.

    # if you're using Flask sessions, you call it like:
    # transactions = transactions_per_user(session["user_id"])
    # so that each user only sees their own transactions.

def get_transaction_summary(user_id):
    cur.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount END), 0) AS total_expenses,
            COUNT(*) AS transaction_count
        FROM transactions WHERE user_id = %s
        AND DATE_TRUNC('month', transaction_date) = DATE_TRUNC('month', CURRENT_DATE);
    """, (user_id,))

    result = cur.fetchone()

    total_income = float(result[0])
    total_expenses = float(result[1])
    transaction_count = result[2]
    net_savings = total_income - total_expenses

    return {
        "income": total_income,
        "expenses": total_expenses,
        "net_savings": net_savings,
        "transaction_count": transaction_count
    }

# COALESCE(SUM(amount), 0) returns "0" instead of "null"

def update_transaction_db(transaction_id, user_id, category_id, transaction_type,
                          amount, description, transaction_date):
    cur.execute(""" UPDATE transactions
        SET category_id = %s, type = %s, amount = %s, description = %s, transaction_date = %s
        WHERE id = %s AND user_id = %s;
    """, (category_id, transaction_type, amount, description,
        transaction_date, transaction_id, user_id))

    conn.commit()

def delete_transaction(transaction_id,user_id):
    cur.execute("DELETE FROM transactions WHERE id=%s AND user_id=%s;",(transaction_id,user_id))
    conn.commit()


def get_transaction_statistics(user_id):
    stats = {}

    # Highest spending category (expenses only)
    cur.execute("""
        SELECT c.category_name FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s AND t.type = 'expense'
        GROUP BY c.category_name ORDER BY SUM(t.amount) DESC LIMIT 1;
    """, (user_id,))

    result = cur.fetchone()
    stats["highest_category"] = result[0] if result else "N/A"

    # Highest income category
    cur.execute("""
        SELECT c.category_name FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s AND t.type = 'income'
        GROUP BY c.category_name ORDER BY SUM(t.amount) DESC LIMIT 1;
    """, (user_id,))

    result = cur.fetchone()
    stats["highest_income_category"] = result[0] if result else "N/A"

    # Largest single transaction
    cur.execute("SELECT MAX(amount) FROM transactions WHERE user_id = %s;", (user_id,))

    result = cur.fetchone()
    stats["largest_transaction"] = float(result[0]) if result and result[0] else 0

    # Most frequently used category
    cur.execute("""
        SELECT c.category_name FROM transactions t
        JOIN categories c ON t.category_id = c.id WHERE t.user_id = %s
        GROUP BY c.category_name ORDER BY COUNT(*) DESC LIMIT 1;
    """, (user_id,))

    result = cur.fetchone()
    stats["most_used_category"] = result[0] if result else "N/A"

    return stats

# Budgets Queries:

def get_budgets():
    cur.execute("select * from budgets ORDER BY month DESC;")
    budgets = cur.fetchall()
    return budgets

def insert_budgets(user_id, category_id, limit_amount, month):
    try:
        cur.execute("""INSERT INTO budgets
            (user_id,category_id,limit_amount,month) 
            values(%s, %s, %s, %s)
        """,(
            user_id, 
            category_id, 
            limit_amount, 
            month
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(e)
        raise

def budgets_per_user(user_id):
    cur.execute("""
        SELECT
        b.id, c.category_name, b.limit_amount, b.month, b.created_at
        FROM budgets b JOIN categories c ON b.category_id = c.id
        WHERE b.user_id = %s ORDER BY b.month DESC
    """, (user_id,))

    user_budget = cur.fetchall()
    return user_budget


def get_budget_by_category(user_id, category_id, month):
    cur.execute("""
        SELECT id, limit_amount, month
        FROM budgets WHERE user_id = %s
        AND category_id = %s AND month = %s
    """, (user_id, category_id, month))

    category_budget = cur.fetchone()
    return category_budget

# returns the budget that a user has set for a specific category in a specific month.(hence .fetchone())
# useful when creating a budget because it lets you prevent duplicate budgets:
# i.e
# if get_budget_by_category(user_id, category_id, month):
    # flash("Budget already exists for this category and month.")


# **********************************************************************************************

def get_one_budget_usage(user_id, category_id, month):
    cur.execute("""
        SELECT b.limit_amount, COALESCE(SUM(t.amount), 0) AS spent
        FROM budgets b LEFT JOIN transactions t
            ON b.category_id = t.category_id
            AND b.user_id = t.user_id AND t.type = 'expense'
            AND DATE_TRUNC('month', t.transaction_date)
                = DATE_TRUNC('month', b.month)
        WHERE b.user_id = %s AND b.category_id = %s AND b.month = %s
        GROUP BY b.limit_amount
    """, (user_id, category_id, month))

    result = cur.fetchone()

    if result:
        limit_amount, spent = result

        remaining = limit_amount - spent

        progress = (spent / limit_amount * 100) if limit_amount > 0 else 0

        if progress < 80:
            status = "On Track"
        elif progress < 100:
            status = "Almost Over Budget"
        else:
            status = "Over Budget"

        return {
            "budget": limit_amount,
            "spent": spent,
            "remaining": remaining,
            "progress": progress,
            "status": status
        }

    return None #Returns when a user never created a budget for a specified category


        # Query Breakdown:

# b.limit_amount -> Gets the budget amount
# COALESCE says:"If the result is NULL, use 0 instead." -> Used incase no expenses have been recorded yet to prevent returning "NULL".
# SUM(t.amount) -> Adds all matching expense transactions:
# LEFT JOIN gives the budget even if there are no matching transactions.
    # NB:
    # If you used "INNER JOIN" a budget with zero expenses wouldn't appear at all.
# ON b.category_id = t.category_id -> matches transactions belonging to the same category.eg food
# AND b.user_id = t.user_id -> Prevents mixing of user's transactions.
# AND t.type = 'expense' -> Only counts "expenses" and ignores income.
# DATE_TRUNC -> Removes the day portion.
    # So:
    # DATE_TRUNC('month', t.transaction_date)
    # and
    # DATE_TRUNC('month', b.month)
    # can be compared to see whether they're in the same month.


        # Use this function when:

# Viewing a specific budget
# Editing a budget
# Checking whether a category is over budget after adding an expense
# Showing details on a single budget page

# or:

def get_all_budget_usage(user_id):
    cur.execute("""
        SELECT
        b.id, b.category_id, c.category_name,b.month, b.limit_amount,
        COALESCE(SUM(t.amount), 0) AS spent,
        b.limit_amount - COALESCE(SUM(t.amount), 0) AS remaining
        FROM budgets b JOIN categories c ON b.category_id = c.id
        LEFT JOIN transactions t
            ON b.category_id = t.category_id
            AND b.user_id = t.user_id
            AND t.type = 'expense'
            AND DATE_TRUNC('month', t.transaction_date)
                = DATE_TRUNC('month', b.month)
        WHERE b.user_id = %s
        GROUP BY b.id, b.category_id, c.category_name,b.month, b.limit_amount
        ORDER BY c.category_name
    """, (user_id,))

    return cur.fetchall()

# returns usage for ALL budgets belonging to a user.

        # What changes is:
# The WHERE clause (single budget vs all budgets).
# The GROUP BY clause (one row vs many rows).
# The SELECT clause (more columns for the dashboard).

        # Expected Output:
# [
#     (1, 'Food', 10000, 5500, 4500),
#     (2, 'Transport', 5000, 3000, 2000),
#     (3, 'Entertainment', 3000, 3500, -500)
# ]
# shows each budget's id, category, limit, spent amount, and remaining balance.

        # Use this function when:
# Building a dashboard
# Showing a list of all budgets
# Creating charts and reports
# Displaying a budget overview page


def search_budgets(user_id, search):

    cur.execute("""
        SELECT
            b.id,
            b.category_id,
            c.category_name,
            b.month,
            b.limit_amount,
            COALESCE(SUM(t.amount),0) AS spent,
            b.limit_amount - COALESCE(SUM(t.amount),0) AS remaining

        FROM budgets b

        JOIN categories c
            ON b.category_id = c.id

        LEFT JOIN transactions t
            ON b.category_id = t.category_id
            AND b.user_id = t.user_id
            AND t.type='expense'
            AND DATE_TRUNC('month',t.transaction_date)
                = DATE_TRUNC('month',b.month)

        WHERE

            b.user_id = %s

            AND

            LOWER(c.category_name)
            LIKE LOWER(%s)

        GROUP BY
            b.id,
            b.category_id,
            c.category_name,
            b.month,
            b.limit_amount

        ORDER BY c.category_name

    """, (user_id, f"%{search}%"))

    return cur.fetchall()

def update_budget(budget_id, limit_amount):

    cur.execute("""
        UPDATE budgets
        SET limit_amount = %s
        WHERE id = %s
    """, (limit_amount, budget_id))

    conn.commit()

def delete_budget(budget_id):

    cur.execute("""
        DELETE FROM budgets
        WHERE id = %s
    """, (budget_id,))

    conn.commit()

# Goals Queries:

def get_goals():
    cur.execute("select * from goals;")
    goals = cur.fetchall()
    return goals

def fetch_goal(goal_id):
    cur.execute("""
        SELECT goal_name, saved_amount
        FROM goals
        WHERE id = %s
    """, (goal_id,))

    return cur.fetchone()

def insert_goals(values):
    try:
        cur.execute("""
            INSERT INTO goals(
                user_id,
                goal_name,
                target_amount,
                saved_amount,
                deadline)
            VALUES (%s, %s, %s, %s, %s)
        """, values)

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(e)
        raise

# This ensures that if an insert fails, the transaction is rolled back 
# and future queries will work normally.

def get_user_goals(user_id):
    cur.execute("""
        SELECT id, goal_name, target_amount, saved_amount, deadline
        FROM goals WHERE user_id = %s ORDER BY deadline ASC
""", (user_id,))
    
    user_goals = cur.fetchall()
    return user_goals

#"ORDER BY deadline ASC" shows the goals with the nearest deadline first.

def update_goal_progress(goal_id, amount):
    cur.execute("""
        UPDATE goals SET saved_amount = LEAST(saved_amount + %s,target_amount) WHERE id = %s
    """, (amount, goal_id))

    conn.commit()

# For adding savings to an existing goal:
def update_goal_details(values):

    cur.execute("""
        UPDATE goals SET goal_name = %s, target_amount = %s,
        saved_amount = %s, deadline = %s WHERE id = %s
    """, values)

    conn.commit()

def delete_goal(goal_id, user_id):
    cur.execute("DELETE FROM goals WHERE id = %s AND user_id = %s", (goal_id, user_id))

    conn.commit()

# LEAST -> Prevents the saved amount from exceeding the target amount.

def get_goal_progress(goal_id):
    cur.execute("""
        SELECT goal_name, target_amount, saved_amount,
        ROUND((saved_amount / target_amount) * 100, 2)
        FROM goals WHERE id = %s
    """, (goal_id,))

    goal_progress = cur.fetchone()
    return goal_progress

# ROUND((saved_amount / target_amount) * 100, 2) -> returns a goal's completion percentage
# NB: Use it to power a progress bar later.


# Categories Queries:

def get_categories():
    cur.execute("select * from categories")
    categories = cur.fetchall()
    return  categories

        # Use to:
# Include dropdowns when adding transactions.
# Group spending.
# Create reports.

# Users Queries:
def check_user_exists(email):
    cur.execute("select * from users where email = %s",(email,))
    user = cur.fetchone()
    return user

def create_user(user_details):
    cur.execute("insert into users(full_name,email,phone_number,password)values(%s,%s,%s,%s)",user_details)
    conn.commit()

# Search query
def search_goals(user_id, search):

    cur.execute("""SELECT id, goal_name, target_amount, saved_amount, deadline
        FROM goals WHERE user_id = %s AND LOWER(goal_name) LIKE LOWER(%s)
        ORDER BY deadline ASC
    """, (user_id, f"%{search}%"))

    return cur.fetchall()

def get_savings_category():

    cur.execute("SELECT id FROM categories WHERE category_name = 'Savings'")

    result = cur.fetchone()

    if result:
        return result[0]

    return None

def get_monthly_category_summary(user_id):
    cur.execute("""SELECT c.category_name, SUM(t.amount)
    FROM transactions t JOIN categories c ON t.category_id = c.id
    WHERE t.user_id = %s AND t.type = 'expense'
        AND DATE_TRUNC('month', t.transaction_date) =
            DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY c.category_name ORDER BY SUM(t.amount) DESC;""", (user_id,))

    summary = cur.fetchall()
    return summary