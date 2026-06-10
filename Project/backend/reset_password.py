"""
Quick utility to reset a user's password in the SQLite database.
Run: python reset_password.py <email> <new_password>

Example: python reset_password.py user@example.com MyNewPass123
"""
import sys
import sqlite3
import bcrypt

def reset(email: str, new_password: str):
    new_hash = bcrypt.hashpw(new_password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")
    conn = sqlite3.connect("ticket_auditor.db")
    cur = conn.cursor()
    cur.execute("UPDATE users SET hashed_password=? WHERE email=?", (new_hash, email))
    rows = cur.rowcount
    conn.commit()
    conn.close()
    if rows == 0:
        print(f"No user found with email: {email}")
    else:
        print(f"Password reset for {email}. You can now log in with the new password.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_password.py <email> <new_password>")
        sys.exit(1)
    reset(sys.argv[1], sys.argv[2])
