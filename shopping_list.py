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
        #If the user exists
        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            return redirect(url_for("my_lists"))
        else:
            error = "Invalid Username or Password"
    return render_template("login.html", error=error)

#Sign Up Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = ''
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Checks the validation for data entry
        if username == '':
            error = "Please Enter a Username"
        elif password =='':
            error = "Please Enter a Password"
        elif username != username.strip() or password != password.strip():
            error = "Username or Password cannot start or end with spaces"
        elif len(username) > 32:
            error = "Username is too long (Maximum 32 characters)"
        elif len(password) < 8:
            error = "Password must be at least 8 characters long"
        else:
            # Checks whether a user with the username already exists
            sql = "SELECT * FROM user WHERE LOWER(username) = LOWER(?)"
            user = query_db(sql, [username], one=True)
            if user:
                error = "This Username already exists"
            else:
                #If no user exists
                sql = "INSERT INTO user (username, password) VALUES (?, ?)"
                query_db(sql, [username, password])
                g._database.commit()
                return redirect(url_for("login", error="Success"))
    return render_template("signup.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# My lists Page
@app.route("/my_lists", methods=["GET", "POST"])
def my_lists():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    current_user_id = session["user_id"]
    #Create new list
    if request.method == "POST":
        list_name = request.form.get("list_name")
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
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    current_user_id = session["user_id"]
    # When user is adding a new item
    if request.method == "POST":
            item_name = request.form["item_name"].title()
            catergorisation = request.form["catergorisation"].title()
            item_quantity = request.form["quantity"]
            item_ticked = 1 if request.form.get("ticked") else 0
            sql = "SELECT item_id FROM item WHERE item_name = ?"
            item_row = query_db(sql, [item_name], one=True)
            if item_row:
                # Item exists
                item_id = item_row["item_id"]
            else:
                # Inserts item into item table if it doesn't exist
                cur = db.execute("INSERT INTO item (item_name, catergorisation) VALUES (?, ?)", [item_name, catergorisation])
                db.commit()
                item_id = cur.lastrowid
                cur.close()    
            if item_quantity and item_id:
                # Adds the item into the list if there is the quantity and item_id
                sql = "INSERT INTO list_contents (list_id, item_id, quantity, ticked) VALUES (?, ?, ?, ?)"
                query_db(sql, [list_id, item_id, item_quantity, item_ticked])
                g._database.commit()
            return redirect(url_for("list_route", list_id=list_id))
    current_list = None
    if list_id:
        sql_list = "SELECT * FROM lists WHERE list_id = ? AND user_id = ?"
        current_list = query_db(sql_list, [list_id, current_user_id], one=True)
        if not current_list:
            return redirect(url_for("my_lists"))
        sql = """SELECT * FROM list_contents
                JOIN item ON item.item_id=list_contents.item_id
                WHERE list_contents.list_id = ?;"""
        results = query_db(sql, [list_id]) or []
    else:
        results = []
    return render_template("list.html", list=results, list_id=list_id, current_list=current_list)

if __name__ == "__main__":
    app.run(debug=True)