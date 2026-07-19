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
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, commit=False):
    db = get_db()
    cur = db.execute(query, args)
# Login Page
@app.route("/login", methods =["GET", "POST"])
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
@app.route("/signup", methods =["GET", "POST"])
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
            query_db(sql, [username, password], commit=True)
            return redirect(url_for("login", error="Success"))
    return render_template("signup.html", error=error)

# My lists Page
@app.route("/my_lists")
def my_lists():
    return render_template("my_lists.html")

# List Page (maybe temporary)
@app.route("/list")
def list():
    return render_template("list.html")

# IDEAS
def create_file(name):
    f = open(f"{name}.txt", "x")
    f.close()

def delete_file(name):
    if os.path.exists(f"{name}.txt"):
        os.remove(f"{name}.txt")
    else:
        print(f"name does not exist")
# Idea end

if __name__ == "__main__":
    app.run(debug=True)