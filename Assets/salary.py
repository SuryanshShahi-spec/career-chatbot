"""
Salary Suite - A combined Tkinter GUI application
Features:
    1. Currency Conversion
    2. Salary Comparison  (HRA / DA / TA / Gross Salary, side by side)
    3. Salary Research    (lookup average salaries by job role)
    4. Salary Logs        (history of every calculation, exportable to CSV)

Run with:  python salary_suite.py
Requires:  Python 3.x (tkinter ships with the standard library)
"""

import csv
import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

# --------------------------------------------------------------------------
# Static / offline reference data
# --------------------------------------------------------------------------

# Exchange rates are expressed relative to 1 USD.
# NOTE: These are fixed demo rates (not live). Edit this dictionary,
# or wire it up to a live API, if you need real-time rates.
CURRENCY_RATES = {
    "USD": 1.0,
    "INR": 83.10,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.30,
    "AUD": 1.52,
    "CAD": 1.36,
    "CNY": 7.24,
    "SGD": 1.34,
    "AED": 3.67,
}

# Sample average annual salary dataset (in INR) used for "Salary Research".
JOB_SALARY_DATA = {
    "Software Engineer": 800000,
    "Senior Software Engineer": 1500000,
    "Data Scientist": 1100000,
    "Data Analyst": 600000,
    "Product Manager": 1800000,
    "Project Manager": 1200000,
    "HR Manager": 750000,
    "HR Executive": 400000,
    "Accountant": 450000,
    "Chartered Accountant": 900000,
    "Sales Executive": 400000,
    "Sales Manager": 950000,
    "Marketing Manager": 900000,
    "Digital Marketing Executive": 450000,
    "Web Developer": 550000,
    "Mobile App Developer": 700000,
    "System Administrator": 600000,
    "Network Engineer": 650000,
    "DevOps Engineer": 1200000,
    "UI/UX Designer": 650000,
    "Business Analyst": 850000,
    "Customer Support Executive": 300000,
    "Content Writer": 350000,
    "Graphic Designer": 400000,
    "Teacher": 350000,
}

# Salary component percentages (of Basic Salary), matching the original
# "Salary Conversion" program: HRA 15%, DA 5%, TA 2%.
HRA_PCT = 15
DA_PCT = 5
TA_PCT = 2

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salary_logs.json")


# --------------------------------------------------------------------------
# Helper functions (pure logic, independent of the GUI)
# --------------------------------------------------------------------------

def compute_salary_breakdown(basic_salary: float):
    """Return (hra, da, ta, gross) for a given basic salary."""
    hra = (HRA_PCT * basic_salary) / 100
    da = (DA_PCT * basic_salary) / 100
    ta = (TA_PCT * basic_salary) / 100
    gross = basic_salary + hra + da + ta
    return hra, da, ta, gross


def convert_currency(amount: float, from_cur: str, to_cur: str):
    """Convert `amount` from `from_cur` to `to_cur` using CURRENCY_RATES."""
    usd_amount = amount / CURRENCY_RATES[from_cur]
    return usd_amount * CURRENCY_RATES[to_cur]


def load_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_logs(logs):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


# --------------------------------------------------------------------------
# Main Application
# --------------------------------------------------------------------------

class SalarySuiteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Salary Suite")
        self.geometry("760x560")
        self.minsize(700, 520)

        self.logs = load_logs()

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.currency_tab = ttk.Frame(notebook)
        self.comparison_tab = ttk.Frame(notebook)
        self.research_tab = ttk.Frame(notebook)
        self.logs_tab = ttk.Frame(notebook)

        notebook.add(self.currency_tab, text="Currency Conversion")
        notebook.add(self.comparison_tab, text="Salary Comparison")
        notebook.add(self.research_tab, text="Salary Research")
        notebook.add(self.logs_tab, text="Salary Logs")

        self._build_currency_tab()
        self._build_comparison_tab()
        self._build_research_tab()
        self._build_logs_tab()

        self._refresh_logs_view()

    # ----------------------------------------------------------------
    # Logging
    # ----------------------------------------------------------------
    def _add_log(self, entry_type: str, details: str):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": entry_type,
            "details": details,
        }
        self.logs.append(entry)
        save_logs(self.logs)
        self._refresh_logs_view()

    def _refresh_logs_view(self):
        for row in self.logs_tree.get_children():
            self.logs_tree.delete(row)
        for entry in self.logs:
            self.logs_tree.insert(
                "", "end",
                values=(entry["timestamp"], entry["type"], entry["details"])
            )

    # ----------------------------------------------------------------
    # Tab 1: Currency Conversion
    # ----------------------------------------------------------------
    def _build_currency_tab(self):
        frame = self.currency_tab
        pad = {"padx": 10, "pady": 8}

        ttk.Label(frame, text="Currency Conversion", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", **pad
        )

        ttk.Label(frame, text="Amount:").grid(row=1, column=0, sticky="e", **pad)
        self.cur_amount_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.cur_amount_var, width=20).grid(
            row=1, column=1, sticky="w", **pad
        )

        currencies = sorted(CURRENCY_RATES.keys())

        ttk.Label(frame, text="From:").grid(row=2, column=0, sticky="e", **pad)
        self.from_cur_var = tk.StringVar(value="USD")
        ttk.Combobox(
            frame, textvariable=self.from_cur_var, values=currencies,
            state="readonly", width=17
        ).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(frame, text="To:").grid(row=3, column=0, sticky="e", **pad)
        self.to_cur_var = tk.StringVar(value="INR")
        ttk.Combobox(
            frame, textvariable=self.to_cur_var, values=currencies,
            state="readonly", width=17
        ).grid(row=3, column=1, sticky="w", **pad)

        ttk.Button(frame, text="Convert", command=self._do_currency_conversion).grid(
            row=4, column=0, columnspan=2, pady=15
        )

        self.cur_result_var = tk.StringVar(value="Result will appear here")
        ttk.Label(
            frame, textvariable=self.cur_result_var,
            font=("Segoe UI", 12, "bold"), foreground="#1a5d1a"
        ).grid(row=5, column=0, columnspan=3, sticky="w", **pad)

        ttk.Label(
            frame,
            text="Note: exchange rates are fixed demo values, not live market rates.",
            foreground="gray"
        ).grid(row=6, column=0, columnspan=3, sticky="w", **pad)

    def _do_currency_conversion(self):
        try:
            amount = float(self.cur_amount_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid numeric amount.")
            return

        from_cur = self.from_cur_var.get()
        to_cur = self.to_cur_var.get()
        converted = convert_currency(amount, from_cur, to_cur)

        result_text = f"{amount:,.2f} {from_cur} = {converted:,.2f} {to_cur}"
        self.cur_result_var.set(result_text)
        self._add_log("Currency Conversion", result_text)

    # ----------------------------------------------------------------
    # Tab 2: Salary Comparison
    # ----------------------------------------------------------------
    def _build_comparison_tab(self):
        frame = self.comparison_tab
        pad = {"padx": 10, "pady": 6}

        ttk.Label(frame, text="Salary Comparison", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", **pad
        )

        ttk.Label(frame, text="Employee A - Basic Salary:").grid(row=1, column=0, sticky="e", **pad)
        self.basic_a_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.basic_a_var, width=18).grid(row=1, column=1, **pad)

        ttk.Label(frame, text="Employee B - Basic Salary:").grid(row=1, column=2, sticky="e", **pad)
        self.basic_b_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.basic_b_var, width=18).grid(row=1, column=3, **pad)

        ttk.Button(frame, text="Compare", command=self._do_salary_comparison).grid(
            row=2, column=0, columnspan=4, pady=12
        )

        columns = ("component", "employee_a", "employee_b")
        self.comparison_tree = ttk.Treeview(frame, columns=columns, show="headings", height=6)
        self.comparison_tree.heading("component", text="Component")
        self.comparison_tree.heading("employee_a", text="Employee A")
        self.comparison_tree.heading("employee_b", text="Employee B")
        self.comparison_tree.column("component", width=150, anchor="w")
        self.comparison_tree.column("employee_a", width=170, anchor="e")
        self.comparison_tree.column("employee_b", width=170, anchor="e")
        self.comparison_tree.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

        self.comparison_result_var = tk.StringVar()
        ttk.Label(
            frame, textvariable=self.comparison_result_var,
            font=("Segoe UI", 11, "bold"), foreground="#1a5d1a"
        ).grid(row=4, column=0, columnspan=4, sticky="w", padx=10)

    def _do_salary_comparison(self):
        try:
            basic_a = float(self.basic_a_var.get())
            basic_b = float(self.basic_b_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid numeric basic salaries.")
            return

        hra_a, da_a, ta_a, gross_a = compute_salary_breakdown(basic_a)
        hra_b, da_b, ta_b, gross_b = compute_salary_breakdown(basic_b)

        for row in self.comparison_tree.get_children():
            self.comparison_tree.delete(row)

        rows = [
            ("Basic Salary", basic_a, basic_b),
            (f"HRA ({HRA_PCT}%)", hra_a, hra_b),
            (f"DA ({DA_PCT}%)", da_a, da_b),
            (f"TA ({TA_PCT}%)", ta_a, ta_b),
            ("Gross Salary", gross_a, gross_b),
        ]
        for label, val_a, val_b in rows:
            self.comparison_tree.insert(
                "", "end", values=(label, f"{val_a:,.2f}", f"{val_b:,.2f}")
            )

        diff = gross_a - gross_b
        if diff > 0:
            verdict = f"Employee A earns more, by {diff:,.2f}"
        elif diff < 0:
            verdict = f"Employee B earns more, by {abs(diff):,.2f}"
        else:
            verdict = "Both employees have the same gross salary"
        self.comparison_result_var.set(verdict)

        details = (
            f"A basic={basic_a:,.2f} -> gross={gross_a:,.2f} | "
            f"B basic={basic_b:,.2f} -> gross={gross_b:,.2f} | {verdict}"
        )
        self._add_log("Salary Comparison", details)

    # ----------------------------------------------------------------
    # Tab 3: Salary Research
    # ----------------------------------------------------------------
    def _build_research_tab(self):
        frame = self.research_tab
        pad = {"padx": 10, "pady": 8}

        ttk.Label(frame, text="Salary Research", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", **pad
        )

        ttk.Label(frame, text="Search job role:").grid(row=1, column=0, sticky="e", **pad)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(frame, textvariable=self.search_var, width=30)
        search_entry.grid(row=1, column=1, sticky="w", **pad)
        search_entry.bind("<KeyRelease>", lambda e: self._filter_research())

        ttk.Button(frame, text="Show All", command=self._show_all_research).grid(
            row=1, column=2, sticky="w", **pad
        )

        columns = ("role", "avg_salary")
        self.research_tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        self.research_tree.heading("role", text="Job Role")
        self.research_tree.heading("avg_salary", text="Average Annual Salary (INR)")
        self.research_tree.column("role", width=280, anchor="w")
        self.research_tree.column("avg_salary", width=220, anchor="e")
        self.research_tree.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.research_tree.bind("<<TreeviewSelect>>", self._on_research_select)

        self.research_detail_var = tk.StringVar(
            value="Select a role to log it, or use the Salary Comparison tab with this figure as Basic Salary."
        )
        ttk.Label(frame, textvariable=self.research_detail_var, foreground="gray", wraplength=650).grid(
            row=3, column=0, columnspan=3, sticky="w", padx=10
        )

        self._show_all_research()

    def _populate_research_tree(self, data: dict):
        for row in self.research_tree.get_children():
            self.research_tree.delete(row)
        for role, salary in sorted(data.items()):
            self.research_tree.insert("", "end", values=(role, f"{salary:,.0f}"))

    def _show_all_research(self):
        self.search_var.set("")
        self._populate_research_tree(JOB_SALARY_DATA)

    def _filter_research(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self._populate_research_tree(JOB_SALARY_DATA)
            return
        filtered = {
            role: salary for role, salary in JOB_SALARY_DATA.items()
            if query in role.lower()
        }
        self._populate_research_tree(filtered)

    def _on_research_select(self, event):
        selection = self.research_tree.selection()
        if not selection:
            return
        role, salary = self.research_tree.item(selection[0], "values")
        self.research_detail_var.set(f"Selected: {role} - Average Salary: {salary} INR/year")
        self._add_log("Salary Research", f"Looked up '{role}' -> avg {salary} INR/year")

    # ----------------------------------------------------------------
    # Tab 4: Salary Logs
    # ----------------------------------------------------------------
    def _build_logs_tab(self):
        frame = self.logs_tab
        pad = {"padx": 10, "pady": 8}

        ttk.Label(frame, text="Salary Logs", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", **pad
        )

        columns = ("timestamp", "type", "details")
        self.logs_tree = ttk.Treeview(frame, columns=columns, show="headings", height=16)
        self.logs_tree.heading("timestamp", text="Timestamp")
        self.logs_tree.heading("type", text="Type")
        self.logs_tree.heading("details", text="Details")
        self.logs_tree.column("timestamp", width=140, anchor="w")
        self.logs_tree.column("type", width=140, anchor="w")
        self.logs_tree.column("details", width=420, anchor="w")
        self.logs_tree.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=8)

        ttk.Button(btn_frame, text="Refresh", command=self._refresh_logs_view).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Export to CSV", command=self._export_logs_csv).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Logs", command=self._clear_logs).pack(side="left", padx=5)

    def _export_logs_csv(self):
        if not self.logs:
            messagebox.showinfo("No data", "There are no logs to export yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="salary_logs.csv"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Type", "Details"])
            for entry in self.logs:
                writer.writerow([entry["timestamp"], entry["type"], entry["details"]])
        messagebox.showinfo("Exported", f"Logs exported to:\n{path}")

    def _clear_logs(self):
        if not self.logs:
            return
        if messagebox.askyesno("Confirm", "Clear all salary logs? This cannot be undone."):
            self.logs = []
            save_logs(self.logs)
            self._refresh_logs_view()


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    app = SalarySuiteApp()
    app.mainloop()


if __name__ == "__main__":
    main()