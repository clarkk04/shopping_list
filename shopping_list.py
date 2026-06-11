from flask import Flask, g, render_template
import sqlite3

DATABASE = 'shopping_list_database.db'

app = Flask(__name__)

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
    return render_template("login.html",results=results)

def create_file(name):
    f = open(f"{name}.txt", "x")
    f.close()

def delete_file(name):
    import os
    if os.path.exists(f"{name}.txt"):
        os.remove(f"{name}.txt")
    else:
        print(f"name does not exist")

if __name__ == "__main__":
    app.run(debug=True)