import streamlit as st
import hashlib
import time
import json
import uuid
import os
from cryptography.fernet import Fernet
import base64


DATA_FILE = "secure_data.json"

for key in ["failed_attempts", "last_attempt_time", "page", "user"]:
    if key not in st.session_state:
        st.session_state[key] = 0 if key in ["failed_attempts", "last_attempt_time"] else "home" if key == "page" else None


def hash_passkey(passkey):
    return hashlib.sha256(passkey.encode()).hexdigest()

def generate_key(passkey):
    return base64.urlsafe_b64encode(hashlib.sha256(passkey.encode()).digest()[:32])

def encrypt_data(data, passkey):
    cipher = Fernet(generate_key(passkey))
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(encrypted_text, passkey):
    try:
        cipher = Fernet(generate_key(passkey))
        return cipher.decrypt(encrypted_text.encode()).decode()
    except:
        return None

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def too_many_attempts():
    return st.session_state.failed_attempts >= 3 and (time.time() - st.session_state.last_attempt_time) < 10

def reset_attempts():
    st.session_state.failed_attempts = 0

stored_data = load_data()

st.title("Secure Data encryption App")

if st.session_state.page == "home":
    st.subheader("Welcome!")
    st.write("Securely store and retrieve your encrypted data.")

    if st.button("Login"):
        st.session_state.page = "login"
    if st.button("Create Account"):
        st.session_state.page = "register"
    if st.button("Store Data"):
        if st.session_state.user:
            st.session_state.page = "store"
        else:
            st.warning("Please login first.")
    if st.button("Retrieve Data"):
        if st.session_state.user:
            st.session_state.page = "retrieve"
        else:
            st.warning("Please login first.")

elif st.session_state.page == "register":
    st.subheader("Create Account")
    username = st.text_input("Choose a Username")
    password = st.text_input("Set Admin Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if not all([username, password, confirm_password]):
            st.error("All fields are required.")
        elif username in stored_data:
            st.error("Username already exists.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        else:
            stored_data[username] = {
                "admin_password": hash_passkey(password),
                "data": {}
            }
            save_data(stored_data)
            st.success("Account created successfully.")
            st.session_state.page = "home"

    if st.button("Back"):
        st.session_state.page = "home"

elif st.session_state.page == "login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Admin Password", type="password")

    if st.button("Login"):
        if username in stored_data and hash_passkey(password) == stored_data[username]["admin_password"]:
            st.session_state.user = username
            reset_attempts()
            st.success(f"Welcome, {username}!")
            st.session_state.page = "home"
        else:
            st.session_state.failed_attempts += 1
            st.session_state.last_attempt_time = time.time()
            st.error("Invalid credentials.")

    if st.button("Back"):
        st.session_state.page = "home"

elif st.session_state.page == "store":
    st.subheader("Store Encrypted Data")
    data = st.text_area("Enter data to store")
    passkey = st.text_input("Encryption Key", type="password")
    confirm_passkey = st.text_input("Confirm Key", type="password")

    if st.button("Save Data"):
        if not all([data, passkey, confirm_passkey]):
            st.error("All fields are required.")
        elif passkey != confirm_passkey:
            st.error("Keys do not match.")
        else:
            data_id = str(uuid.uuid4())
            encrypted = encrypt_data(data, passkey)
            user = st.session_state.user
            stored_data[user]["data"][data_id] = {
                "encrypted": encrypted,
                "passkey": hash_passkey(passkey)
            }
            save_data(stored_data)
            st.success("Data saved successfully!")
            st.code(data_id)
            st.session_state.page = "home"

    if st.button("Back"):
        st.session_state.page = "home"

elif st.session_state.page == "retrieve":
    st.subheader("Retrieve Data")
    if too_many_attempts():
        wait = int(10 - (time.time() - st.session_state.last_attempt_time))
        st.warning(f"Wait {wait}s before trying again.")
    else:
        data_id = st.text_input("Enter your Data ID")
        passkey = st.text_input("Enter your Encryption Key", type="password")

        if st.button("Decrypt"):
            user = st.session_state.user
            if data_id in stored_data[user]["data"]:
                correct_hash = stored_data[user]["data"][data_id]["passkey"]
                if hash_passkey(passkey) == correct_hash:
                    decrypted = decrypt_data(stored_data[user]["data"][data_id]["encrypted"], passkey)
                    st.success("Decryption successful!")
                    st.code(decrypted)
                    reset_attempts()
                else:
                    st.session_state.failed_attempts += 1
                    st.session_state.last_attempt_time = time.time()
                    st.error("Wrong encryption key.")
            else:
                st.error("Data ID not found.")

    if st.button("Back"):
        st.session_state.page = "home"


