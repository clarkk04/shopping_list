from flask import Flask, g, request, render_template, redirect, url_for
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'shopping_list_database.db')

app = Flask(__name__)

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
    return redirect(url_for("login"))

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ''
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        sql = "SELECT * FROM user WHERE username = ? AND password = ?;"
        user = query_db(sql, [username, password], one=True)
        if user:
            return redirect(url_for("my_lists"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error)

#Sign Up Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = ''
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        sql = "SELECT * FROM user WHERE username = ?"
        user = query_db(sql, [username])
        if user:
            error="Exist"
        else:
            sql = "INSERT INTO user (username, password) VALUES (?, ?)"
            query_db(sql, [username, password])
            g._database.commit()
            return redirect(url_for("login", error="Success"))
    return render_template("signup.html", error=error)

# My lists Page
@app.route("/my_lists", methods=["GET", "POST"])
def my_lists():
    sql = """SELECT * FROM lists
     INNER JOIN list_contents ON user_id=user_id;"""
    results = query_db(sql)
    return render_template("my_lists.html", list=results)

# Table Page
@app.route("/list", methods=["GET", "POST"])
def list():
    if request.method == "POST":
            item_name = request.form["item_name"]
            catergorisation = request.form["catergorisation"]
            item_quantity = request.form["quantity"]
            sql = "SELECT item_id FROM item WHERE item_name = ?"
            item_row = query_db(sql, [item_name], one=True)
            if item_row:
                # Item exists
                item_id = item_row["item_id"]
            else:
                db = get_db()
                cur = db.execute("INSERT INTO item (item_name, catergorisation) VALUES (?, ?)", [item_name, catergorisation])
                item_id = cur.lastrowid
                cur.close()
            sql = "SELECT item_id FROM item WHERE item_name = ?"    
            if item_quantity and item_id:
                sql = "INSERT INTO list_contents (item_id, quantity) VALUES (?, ?)"
                query_db(sql, [item_id, item_quantity])
                g._database.commit()
            return redirect(url_for("list"))
    sql = """SELECT * FROM list_contents
            JOIN item ON item.item_id=list_contents.item_id;"""
    results = query_db(sql)
    return render_template("list.html", list=results)

if __name__ == "__main__":
    app.run(debug=True)