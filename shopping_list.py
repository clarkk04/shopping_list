from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "LOGIN"

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