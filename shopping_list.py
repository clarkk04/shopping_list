from flask import Flask, g, request, render_template, redirect, url_for, session
import sqlite3
import os

# Pathing of files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'shopping_list_database.db')

app = Flask(__name__)

# Changed to static key to stay logged in after reloading
app.secret_key = "a_very_secret_shopping_list_hidden_key_2026"

# Database connection functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, commit=False, return_id=False):
    db = get_db()
    cur = get_db().execute(query, args)
    # Commits the changes in the database if argument
    if commit:
        db.commit()
    # Returns last row id if argument
    if return_id:
        last_id = cur.lastrowid
        cur.close()
        return last_id
    rv = cur.fetchall()
    cur.close()
    return rv[0] if (rv and one) else (None if one else rv)

# Verification of user login and if they own the requested list
def verify_list_ownership(list_id):
    if "user_id" not in session:
        return None
    sql = "SELECT * FROM lists where list_id = ? AND user_id = ?"
    return query_db(sql, [list_id, session["user_id"]], one=True)

# Check for errors from signup page (can change restraints in future)
def check_signup_input(username, password):
    # Checks the validation for data entry
    # If no username or password is inputted
    if username == '' or password == '':
        return "Please Enter a Username or Password"
    # If the username or password contains any spaces
    elif ' ' in username or ' ' in password:
        return "Username or Password cannot contain any spaces"
    # If the length of username is greater than 32
    elif len(username) > 32:
        return "Username is too long (Maximum 32 characters)"
    # If password has leass than 8 characters
    elif len(password) < 8:
        return "Password must be at least 8 characters long"
    return ""

# Check for error from adding items
def check_item_input(item_name, categorisation, item_quantity):
    # Checks if item name is not blank
    if not item_name:
        return "Please enter an item name"
    # Checks if item name is under 32 characters
    elif len(item_name) > 32:
        return "Item name is too long (Maximum 32 characters)"
    # Checks if categorisation is not blank
    elif not categorisation:
        return "Please enter a categorisation"
    # Checks if categorisation is under 32 characters
    elif len(categorisation) > 32:
        return "Categorisation is too long (Maximum 32 characters)"
    # Checks if item_quantity is within specified bounds
    try:
        qty = int(item_quantity)
        if qty < 1 or qty > 999:
            raise ValueError
    except (ValueError, TypeError):
        return "Quantity must be a number between 1 and 999"
    # if there is no errors returns no error value
    return ""

# Home Route
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("my_lists"))
    return redirect(url_for("login"))

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ''
    if request.method == "POST":
        # Gets user input from Login Form
        username = request.form["username"]
        password = request.form["password"]
        # Searches for user with matching login details
        sql = "SELECT * FROM user WHERE LOWER(username) = LOWER(?) AND password = ?;"
        user = query_db(sql, [username, password], one=True)
        # If the user account details match
        if user:
            # Records in user Session
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            return redirect(url_for("my_lists"))
        # Else if the values given don't match return error message
        else:
            error = "Invalid Username or Password"
    return render_template("login.html", error=error)

# Sign Up Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = ''
    if request.method == "POST":
        # Recieves user input from Signup Form
        username = request.form["username"]
        password = request.form["password"]
        # Runs function to check validity of signup details
        error = check_signup_input(username, password)
        if not error:
            # Checks whether a user with the username already exists
            sql = "SELECT * FROM user WHERE LOWER(username) = LOWER(?)"
            user = query_db(sql, [username], one=True)
            if user:
                # Returns error message when username already exists
                error = "This Username already exists"
            else:
                # Inserts signup details if no user exists
                sql = "INSERT INTO user (username, password) VALUES (?, ?)"
                query_db(sql, [username, password], commit=True)
                return redirect(url_for("login"))
    return render_template("signup.html", error=error)

# Logout route
@app.route("/logout")
def logout():
    # Clears the user session (user_id, username) and redirects to login
    session.clear()
    return redirect(url_for("login"))

# My lists Page
@app.route("/my_lists", methods=["GET", "POST"])
def my_lists():
    # Returns user to login page if not logged in
    if "user_id" not in session:
        return redirect(url_for("login"))
    current_user_id = session["user_id"]
    error = ''
    # Create new list
    if request.method == "POST":
        list_name = request.form.get("list_name")
        # Ensures the List has a non-blank name
        if not list_name or not list_name.strip():
            error = "List name cannot be blank"
        # Checks if the list name is too long
        elif len(list_name) > 40:
            error = "List name is too long (Maximum 40 characters)"
        # Creates List if conditions above met
        else:
            sql = "INSERT INTO lists (list_name, user_id) VALUES (?, ?)"
            list_id = query_db(sql, [list_name.strip(), current_user_id], commit=True, return_id=True)
            return redirect(url_for('list_route', list_id=list_id))
    # my_lists query
    sql = """SELECT lists.list_id, lists.list_name, 
    COUNT(list_contents.item_id) AS total_items,
    SUM(CASE WHEN list_contents.ticked = 1 THEN 1 ELSE 0 END) AS items_gotten,
    SUM(CASE WHEN list_contents.ticked = 0 THEN 1 ELSE 0 END) AS items_not_gotten
    FROM lists
    LEFT JOIN list_contents ON lists.list_id = list_contents.list_id
    WHERE lists.user_id = ?
    GROUP BY lists.list_id;"""
    results = query_db(sql, [current_user_id]) or []
    return render_template("my_lists.html", list=results, error=error)

# Table Page
@app.route("/list/<int:list_id>", methods=["GET", "POST"])
def list_route(list_id=None):
    # Uses verification function if user owns list
    current_list = verify_list_ownership(list_id)
    if not current_list:
        return redirect(url_for("my_lists"))
    current_user_id = session["user_id"]
    error = ''
    # When user is adding a new item
    if request.method == "POST":
            # Gets the ids of checked items in the list
            checked_ids = request.form.getlist("ticked_items")
            # Resets all ticks to not ticked
            sql = "UPDATE list_contents SET ticked = 0 WHERE list_id = ?"
            query_db(sql, [list_id], commit=True)
            if checked_ids:
                # Gets a string with ? marks based on how many ticked items
                placeholder = ",".join("?" for _ in checked_ids)
                updated_sql = f"UPDATE list_contents SET ticked = 1 WHERE list_id = ? AND item_id IN ({placeholder})"
                # Updates checked items based on list_id and id of checked item
                query_db(updated_sql, [list_id] + [int(i) for i in checked_ids], commit=True)
            # Processes if item creation form submitted
            if request.form.get("quantity") is not None:
                item_name = request.form.get("item_name", "").strip().title()
                categorisation = request.form.get("categorisation", "").strip().title()
                item_quantity = request.form.get("quantity")
                # Runs validator function
                error = check_item_input(item_name, categorisation, item_quantity)
                if not error:
                    sql = "SELECT item_id FROM item WHERE item_name = ?"
                    item_row = query_db(sql, [item_name], one=True)
                    if item_row:
                        # Item exists
                        item_id = item_row["item_id"]
                    else:
                        # Inserts item into item table if it doesn't exist
                        sql = "INSERT INTO item (item_name, categorisation, user_id) VALUES (?, ?, ?)"
                        item_id = query_db(sql, [item_name, categorisation, current_user_id], commit=True, return_id=True)
                    # If item is already present in list
                    sql = "SELECT * FROM list_contents WHERE item_id = ? AND list_id = ?"
                    item_already_exists = query_db(sql, [item_id, list_id], one=True)
                    if item_already_exists:
                        # If item already exists in list
                        error = "Item is already in the list"
                    else:
                        qty = int(item_quantity)
                        sql = ("INSERT INTO list_contents (list_id, item_id, quantity, ticked) VALUES (?, ?, ?, 0)")
                        query_db(sql, [list_id, item_id, qty], commit=True)
                    if not error:
                        return redirect(url_for("list_route", list_id=list_id))
    if list_id:
        # Selects values from list_contents where list_id is equal to the current list
        sql = """SELECT list_contents.item_id, item.item_name, list_contents.quantity, item.categorisation, list_contents.ticked 
                FROM list_contents
                JOIN item ON item.item_id=list_contents.item_id
                WHERE list_contents.list_id = ?;"""
        results = query_db(sql, [list_id]) or []
    else:
        results = []
    return render_template("list.html", list=results, list_id=list_id, current_list=current_list, error=error)

# Item Dictionary
@app.route("/item_dictionary", methods=["GET", "POST"])
def item_dictionary():
    # Rdirects User if not logged in
    if "user_id" not in session:
        return redirect(url_for("login"))
    current_user_id = session["user_id"]
    error = ''
    # When user is adding a new item
    if request.method == "POST":
        # Gets rid of unecessary spaces and adds capitalisation for consistency
        item_name = request.form.get("item_name", "").strip().title()
        categorisation = request.form.get("categorisation", "").strip().title()
        # Checks Validity of Item with dummy quantity
        error = check_item_input(item_name, categorisation, 1)
        if not error:
            sql = "SELECT item_id FROM item WHERE item_name = ? AND user_id = ?"
            item_exists = query_db(sql, [item_name, current_user_id], one=True)
            # Inserts item into item table if it doesn't exist
            if not item_exists:
                sql = "INSERT INTO item (item_name, categorisation, user_id) VALUES (?, ?, ?)"
                query_db(sql, [item_name, categorisation, current_user_id], commit=True)
                return redirect(url_for('item_dictionary'))
            else:
                error = "This item already exists in your dictionary"
    # Fixed Ordering of categorisation and item name
    sql = "SELECT * FROM item WHERE user_id = ? ORDER BY LOWER(categorisation) ASC, LOWER(item_name) ASC;"
    results = query_db(sql, [current_user_id]) or []
    return render_template("item_dictionary.html", item_dictionary=results, error=error)
            
           
# Unified Deletion Route for Lists, List Items, and Dictionary Catalog Items
@app.route("/delete/<string:target_type>/<int:target_id>", methods=["POST"])
@app.route("/delete/<string:target_type>/<int:list_id>/<int:item_id>", methods=["POST"])
def unified_delete(target_type, target_id=None, list_id=None, item_id=None):
    if "user_id" not in session:
        return redirect(url_for("login"))
    current_user_id = session["user_id"]
    # List Deletion
    if target_type == "list" and target_id is not None:
        # Checks if user owns the list
        list_owned = verify_list_ownership(target_id)
        if list_owned:
            # Deletes all items in the list and deletes the list itself
            query_db("DELETE FROM list_contents WHERE list_id = ?", [target_id], commit=True)
            query_db("DELETE FROM lists WHERE list_id = ?", [target_id], commit=True)
        return redirect(url_for("my_lists"))
    # Item Deletion from list
    elif target_type == "item":
        # Checks if user owns the list
        list_owned = verify_list_ownership(list_id)
        if list_owned:
            # Deletes item from singular list
            sql="DELETE FROM list_contents WHERE list_id = ? AND item_id = ?"
            query_db(sql, [list_id, item_id], commit=True)
            return redirect(url_for("list_route", list_id=list_id))
    # Item Deletion from private dictionary
    elif target_type == "dictionary" and target_id:
        # Checks if user_id matches with the item up for deletion
        sql = "SELECT * FROM item WHERE item_id = ? AND user_id = ?"
        item_owned = query_db(sql, [target_id, current_user_id], one=True)
        if item_owned:
            # Deletes item from all lists and item_dictionary with matching user_id
            query_db("DELETE FROM list_contents WHERE item_id = ?", [target_id], commit=True)
            query_db("DELETE FROM item WHERE item_id = ? AND user_id = ?", [target_id, current_user_id], commit=True)
        return redirect(url_for("item_dictionary"))
    return redirect(url_for("my_lists"))

if __name__ == "__main__":
    app.run(debug=True)