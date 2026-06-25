from flask import Flask, g, request, render_template, redirect, url_for
import sqlite3

DATABASE = 'shopping_list_database.db'

app = Flask(__name__)

# Test username and password (Temporary)
USERNAME = "test"
PASSWORD = "password"

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

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route("/")
def home():
    sql = "SELECT * FROM user;"
    results = query_db(sql)
    return render_template("login.html",results=results, login = "signup")

# Login Page
@app.route("/", methods =["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == USERNAME and password == PASSWORD:
            return redirect(url_for("my_lists"))
        else:
            return render_template("login.html", error="Invalid username or password", login="signup")

#Sign Up Page
@app.route("/", methods =["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        cursor = DATABASE.connection.cursor(cursor.DictCursor)
        cursor.execute("SELECT * FROM user WHERE username = %s", (username))
        user = cursor.fetchone()
        if user:
            error = "Exist"
        else:
            cursor.execute("INSERT INTO user VALUES (NULL, %s, %s)", (username, password))
            DATABASE.connection.commit()
            error = "Sucess"
            return render_template("login.html", error="Invalid username or password", login="login")

# My lists Page
@app.route("/my_lists")
def my_lists():
    return render_template("my_lists.html")

# IDEAS
def create_file(name):
    f = open(f"{name}.txt", "x")
    f.close()

def delete_file(name):
    import os
    if os.path.exists(f"{name}.txt"):
        os.remove(f"{name}.txt")
    else:
        print(f"name does not exist")
# Idea end

if __name__ == "__main__":
    app.run(debug=True)