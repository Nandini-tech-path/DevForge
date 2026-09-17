"""
Deliberately flawed sample file used to demonstrate the reviewer.
Do not use any of this code as-is — every function below has an issue on purpose.
"""
import os
import pickle
import random
import hashlib

API_KEY = "sk-live-9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c"  # hardcoded secret


def load_user_prefs(path):
    # insecure deserialization: pickle.load on a file that could be attacker-controlled
    with open(path, "rb") as f:
        return pickle.load(f)


def run_backup(target_dir):
    # shell injection: target_dir is concatenated straight into a shell command
    os.system("tar -cvf backup.tar " + target_dir)


def hash_password(password):
    # weak hashing algorithm for a security-sensitive value
    return hashlib.md5(password.encode()).hexdigest()


def generate_session_token():
    # insecure randomness for a security-sensitive token
    return str(random.randint(100000, 999999))


def get_user(conn, user_id):
    # SQL injection via string concatenation
    query = "SELECT * FROM users WHERE id = " + user_id
    return conn.execute(query)


def process(items=[]):  # mutable default argument bug
    for i in items:
        try:
            items.append(i * 2)
        except:  # bare except swallows everything, including real bugs
            pass
    return items


def divide_all(numbers, divisor):
    # bug: no guard against divisor == 0
    return [n / divisor for n in numbers]
