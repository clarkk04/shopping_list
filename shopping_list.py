def create_file(name):
    f = open(f"{name}.txt", "x")
    f.close()
def delete_file(name):
    import os
    if os.path.exists(f"{name}.txt"):
        os.remove(f"{name}.txt")
    else:
        print(f"name does not exist")

test = input("????")
while test != "0":
    if test == "1":
        name = input("name?")
        create_file(name)
    else:
        name = input("name?")
        delete_file(name)
    test = input("????")
