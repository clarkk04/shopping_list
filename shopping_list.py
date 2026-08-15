from flask import Flask, g, request, render_template, redirect, url_for, session
import sqlite3
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'shopping_list_database.db')

app = Flask(__name__)

# Generates secure secret unique key
app.secret_key = secrets.token_hex(24)

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

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# Verification of user login and if they own the requested list
def verify_list_ownership(list_id):
    if "user_id" not in session:
        return None
    sql = "SELECT * FROM lists where list_id = ? AND user_id = ?"
    return query_db(sql, [list_id, session["user_id"]], one=True)

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
        username = request.form["username"]
        password = request.form["password"]
        sql = "SELECT * FROM user WHERE LOWER(username) = LOWER(?) AND password = ?;"
        user = query_db(sql, [username, password], one=True)
        # If the user exists
        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            return redirect(url_for("my_lists"))
        # Else if the values given don't match to the table
        else:
            error = "Invalid Username or Password"
    return render_template("login.html", error=error)

# Sign Up Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = ''
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Checks the validation for data entry
        # If no username is inputted
        if username == '':
            error = "Please Enter a Username"
        # If no signup is inputted
        elif password =='':
            error = "Please Enter a Password"
        # If username or password has unecessary spaces
        elif username != username.strip() or password != password.strip():
            error = "Username or Password cannot start or end with spaces"
        # If the length of username is greater than 32
        elif len(username) > 32:
            error = "Username is too long (Maximum 32 characters)"
        # If password has leass than 8 characters
        elif len(password) < 8:
            error = "Password must be at least 8 characters long"
        else:
            # Checks whether a user with the username already exists
            sql = "SELECT * FROM user WHERE LOWER(username) = LOWER(?)"
            user = query_db(sql, [username], one=True)
            if user:
                # Returns error message when user already exists
                error = "This Username already exists"
            else:
                # Inserts signup details if no user exists
                db = get_db()
                db.execute("INSERT INTO user (username, password) VALUES (?, ?)", [username, password])
                db.commit()
                return redirect(url_for("login"))
    return render_template("signup.html", error=error)

# Logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# My lists Page
@app.route("/my_lists", methods=["GET", "POST"])
def my_lists():
    # Returns user to login page if not logged in
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    current_user_id = session["user_id"]
    # Create new list
    if request.method == "POST":
        list_name = request.form.get("list_name")
        # Ensures the List has a name
        if list_name and list_name.strip():  
            cur = db.execute("INSERT INTO lists (list_name, user_id) VALUES (?, ?)", [list_name.strip(), current_user_id])
            db.commit()
            list_id = cur.lastrowid
            cur.close()
            return redirect(url_for('list_route', list_id=list_id))
        return redirect(url_for("my_lists"))
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
    return render_template("my_lists.html", list=results)

# Table Page
@app.route("/list/<int:list_id>", methods=["GET", "POST"])
def list_route(list_id=None):
    # Uses verification function if user owns list
    current_list = verify_list_ownership(list_id)
    if not current_list:
        return redirect(url_for("my_lists"))
    db = get_db()
    current_user_id = session["user_id"]
    # When user is adding a new item
    if request.method == "POST":
            # Save Checkbox ticks
            checked_ids = request.form.getlist("ticked_items")
            db.execute("UPDATE list_contents SET ticked = 0 WHERE list_id = ?", [list_id])
            if checked_ids:
                placeholder = ",".join("?" for _ in checked_ids)
                updated_sql = f"UPDATE list_contents SET ticked = 1 WHERE list_id = ? AND item_id IN ({placeholder})"
                db.execute(updated_sql, [list_id] + [int(i) for i in checked_ids])
            db.commit()
            item_name = request.form.get("item_name", "").strip().title()
            categorisation = request.form.get("categorisation", "").strip().title()
            item_quantity = request.form.get("quantity")
            sql = "SELECT item_id FROM item WHERE item_name = ?"
            item_row = query_db(sql, [item_name], one=True)
            if item_row:
                # Item exists
                item_id = item_row["item_id"]
            else:
                if item_name and item_name.strip() and categorisation and categorisation.strip():
                    # Inserts item into item table if it doesn't exist
                    cur = db.execute("INSERT INTO item (item_name, categorisation, user_id) VALUES (?, ?, ?)", [item_name, categorisation, current_user_id])
                    db.commit()
                    item_id = cur.lastrowid
                    cur.close()
                else:
                    # redirects user if item_name or categorisation is not valid
                    return redirect(url_for('list_route', list_id=list_id))
            # If item is already present in list
            sql = "SELECT * FROM list_contents WHERE item_id = ? AND list_id = ?"
            item_already_exists = query_db(sql, [item_id, list_id], one=True)    
            if item_quantity and item_id:
                if not item_already_exists:
                    # Adds the item into the list if there is the quantity and item_id
                    db.execute(
                        "INSERT INTO list_contents (list_id, item_id, quantity, ticked) VALUES (?, ?, ?, 0)", 
                        [list_id, item_id, item_quantity]
                        )
                else:
                    db.execute(
                        "UPDATE list_contents SET quantity = ? WHERE list_id = ? AND item_id = ?",
                        [item_quantity, list_id, item_id]
                    )
                db.commit()
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
    return render_template("list.html", list=results, list_id=list_id, current_list=current_list)

# Item Dictionary
@app.route("/item_dictionary", methods=["GET", "POST"])
def item_dictionary():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    current_user_id = session["user_id"]
    # When user is adding a new item
    if request.method == "POST":
        item_name = request.form.get("item_name", "").strip().title()
        categorisation = request.form.get("categorisation", "").strip().title()
        sql = "SELECT item_id FROM item WHERE item_name = ? AND user_id = ?"
        item_exists = query_db(sql, [item_name, current_user_id], one=True)
        if item_exists:
            # Item exists
            item_id = item_exists["item_id"]
        else:
            if item_name and item_name.strip() and categorisation and categorisation.strip():
                # Inserts item into item table if it doesn't exist
                cur = db.execute("INSERT INTO item (item_name, categorisation, user_id) VALUES (?, ?, ?)", [item_name, categorisation, current_user_id])
                db.commit()
                cur.close()
    sql = "SELECT * FROM item WHERE user_id = ? ORDER BY LOWER(categorisation) ASC, LOWER(item_name) ASC;"
    results = query_db(sql, [current_user_id]) or []
    return render_template("item_dictionary.html", item_dictionary=results)
            
           
# Unified Deletion Route for Lists, List Items, and Dictionary Catalog Items
@app.route("/delete/<string:target_type>/<int:target_id>", methods=["POST"])
@app.route("/delete/<string:target_type>/<int:list_id>/<int:item_id>", methods=["POST"])
def unified_delete(target_type, target_id=None, list_id=None, item_id=None):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    current_user_id = session["user_id"]
    # List Deletion
    if target_type == "list" and target_id is not None:
        list_owned = verify_list_ownership(target_id)
        if list_owned:
            db.execute("DELETE FROM list_contents WHERE list_id = ?", [target_id])
            db.execute("DELETE FROM lists WHERE list_id = ?", [target_id])
            db.commit()
        return redirect(url_for("my_lists"))
    # Item Deletion from list
    elif target_type == "item":
        list_owned = verify_list_ownership(list_id)
        if list_owned:
            db.execute("DELETE FROM list_contents WHERE list_id = ? AND item_id = ?", [list_id, item_id])
            db.commit()
            return redirect(url_for("list_route", list_id=list_id))
    # Item Deletion from private dictionary
    elif target_type == "dictionary" and target_id:
        sql = "SELECT * FROM item WHERE item_id = ? AND user_id = ?"
        item_owned = query_db(sql, [target_id, current_user_id], one=True)
        if item_owned:
            db.execute("DELETE FROM list_contents WHERE item_id = ?", [target_id])
            db.execute("DELETE FROM item WHERE item_id = ? AND user_id = ?", [target_id, current_user_id])
            db.commit()
        return redirect(url_for("item_dictionary"))
    return redirect(url_for("my_lists"))

if __name__ == "__main__":
    app.run(debug=True)