import tkinter as tk
from tkinter import messagebox
import psycopg2

# --- DATABASE CONNECTION SETTINGS ---
# Replace these values with your actual database details
DB_CONFIG = {
    "dbname": "your_database_name",
    "user": "your_username",
    "password": "your_password",
    "host": "localhost",
    "port": "5432"
}

def save_job_alert():
    """Saves the user inputs from the UI fields into the database."""
    # 1. Get data from the UI input fields
    user_id_val = entry_user_id.get()
    keywords_val = entry_keywords.get()
    location_val = entry_location.get()
    frequency_val = var_frequency.get()
    
    # 2. Check if the user left important fields empty
    if not user_id_val or not keywords_val:
        messagebox.showwarning("Input Error", "User ID and Keywords are required!")
        return

    # 3. Connect to the database and insert the data
    try:
        # Establish connection
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # SQL insert query matching your PostgreSQL table structure
        insert_query = """
        INSERT INTO job_alerts (user_id, keywords, location, frequency, is_active)
        VALUES (%s, %s, %s, %s, TRUE);
        """
        
        # Execute query safely using parameters to prevent SQL injection
        cursor.execute(insert_query, (int(user_id_val), keywords_val, location_val, frequency_val))
        
        # Commit the transaction to save changes permanently
        conn.commit()
        
        # Close the connection doors
        cursor.close()
        conn.close()
        
        # Show success message and clear fields
        messagebox.showinfo("Success", "Job alert created successfully!")
        clear_fields()
        
    except Exception as e:
        messagebox.showerror("Database Error", f"Could not save alert:\n{e}")

def clear_fields():
    """Clears the text input boxes."""
    entry_user_id.delete(0, tk.END)
    entry_keywords.delete(0, tk.END)
    entry_location.delete(0, tk.END)
    var_frequency.set("daily")

# --- UI WINDOW DESIGN ---
root = tk.Tk()
root.title("Job Alert Creator")
root.geometry("400x300")

# User ID Input Row
tk.Label(root, text="User ID:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
entry_user_id = tk.Entry(root, width=30)
entry_user_id.grid(row=0, column=1, padx=10, pady=10)

# Keywords Input Row
tk.Label(root, text="Keywords:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
entry_keywords = tk.Entry(root, width=30)
entry_keywords.grid(row=1, column=1, padx=10, pady=10)

# Location Input Row
tk.Label(root, text="Location:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
entry_location = tk.Entry(root, width=30)
entry_location.grid(row=2, column=1, padx=10, pady=10)

# Frequency Dropdown Menu Row
tk.Label(root, text="Frequency:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
var_frequency = tk.StringVar(root)
var_frequency.set("daily") # default value
dropdown_frequency = tk.OptionMenu(root, var_frequency, "instantly", "daily", "weekly")
dropdown_frequency.grid(row=3, column=1, padx=10, pady=10, sticky="w")

# Submit Button Row
btn_submit = tk.Button(root, text="Create Alert", command=save_job_alert, bg="#4CAF50", fg="white", width=15)
btn_submit.grid(row=4, column=0, columnspan=2, pady=20)

# Keep the window running open
root.mainloop()
