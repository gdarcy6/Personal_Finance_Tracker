import streamlit as st
import sqlite3
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# Set page config 
st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")

# Currency selection
currency_symbols = {"EUR": "€", "GBP": "£", "USD": "$"}
currency = st.sidebar.selectbox("Select Currency", list(currency_symbols.keys()), index=0)
currency_symbol = currency_symbols[currency]

# Database Connection
def get_connection():
    conn = sqlite3.connect("finance_app.db")
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            amount REAL,
            category TEXT,
            date TEXT
        );
        
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            category TEXT,
            payment_method TEXT,
            date TEXT
        );
        
        CREATE TABLE IF NOT EXISTS savings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            saved_amount REAL DEFAULT 0,
            goal_amount REAL DEFAULT 0,
            monthly_savings REAL DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creditor TEXT,
            amount_owed REAL,
            interest_rate REAL,
            min_payment REAL
        );

        CREATE TABLE IF NOT EXISTS debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_id INTEGER,
            payment_amount REAL,
            payment_date TEXT,
            FOREIGN KEY (debt_id) REFERENCES debts (id)
        );
    ''')
    
    # Ensure the savings table has at least one row
    cursor.execute("SELECT COUNT(*) AS count FROM savings")
    count = cursor.fetchone()["count"]
    if count == 0:
        cursor.execute("INSERT INTO savings (saved_amount, goal_amount, monthly_savings) VALUES (0, 0, 0)")
    
    conn.commit()
    conn.close()

def fetch_data(query, params=()):
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def main():
    st.title("📊 Personal Finance Tracker")

    if st.sidebar.button("Reset Database"):
        if os.path.exists("finance_app.db"):
            os.remove("finance_app.db")
        initialize_db()
        st.sidebar.success("Database has been reset successfully!")
        st.rerun()

    menu = ["Overview", "Income", "Expenses", "Savings & Investments", "Debt Tracking"]
    choice = st.sidebar.selectbox("Navigation", menu)

    if choice == "Overview":
        show_overview()
    elif choice == "Income":
        manage_income()
    elif choice == "Expenses":
        manage_expenses()
    elif choice == "Savings & Investments":
        manage_savings()
    elif choice == "Debt Tracking":
        manage_debts()

def show_overview():
    st.subheader("💰 Financial Overview")

    # Fetch data
    income_df = fetch_data("SELECT SUM(amount) AS total_income FROM incomes")
    expense_df = fetch_data("SELECT SUM(amount) AS total_expense FROM expenses")
    savings_df = fetch_data("SELECT SUM(saved_amount) AS total_savings FROM savings")
    debt_df = fetch_data("SELECT SUM(amount_owed) AS total_debt FROM debts")
    debt_payments_df = fetch_data("SELECT SUM(payment_amount) AS total_debt_payments FROM debt_payments")

    # Calculate totals
    total_income = income_df.iloc[0]["total_income"] or 0
    total_expense = expense_df.iloc[0]["total_expense"] or 0
    total_savings = savings_df.iloc[0]["total_savings"] or 0
    total_debt = debt_df.iloc[0]["total_debt"] or 0
    total_debt_payments = debt_payments_df.iloc[0]["total_debt_payments"] or 0

    # Deduct monthly savings from remaining balance
    monthly_savings = fetch_data("SELECT SUM(monthly_savings) AS total_monthly_savings FROM savings")
    total_monthly_savings = monthly_savings.iloc[0]["total_monthly_savings"] or 0

    # Calculate remaining balance (after income, expenses, savings, and debt)
    remaining_balance = total_income - total_expense - total_monthly_savings - total_debt

    # Calculate total remaining balance without debt 
    remaining_balance_without_debt = total_income - total_expense - total_monthly_savings - total_debt_payments

    # Display metrics
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Income", f"{currency_symbol}{total_income:,.2f}")
    col2.metric("Total Expenses", f"{currency_symbol}{total_expense:,.2f}")
    col3.metric("Total Savings", f"{currency_symbol}{total_savings:,.2f}")
    col4.metric("Total Debt", f"{currency_symbol}{total_debt:,.2f}")
    col5.metric("Remaining Balance", f"{currency_symbol}{remaining_balance:,.2f}")
    col6.metric("Remaining Balance (Without Debt)", f"{currency_symbol}{remaining_balance_without_debt:,.2f}")

    # Prepare data for the pie chart
    labels = ["Total Income", "Total Expenses", "Total Savings", "Total Debt"]
    values = [total_income, total_expense, total_savings, total_debt]


    # Create a pie chart using go.Figure
    fig = go.Figure()

    fig.add_trace(go.Pie(
        labels=labels,
        values=values,
        pull=[0.1, 0, 0, 0],  # Slightly pull out the first slice
        textinfo="percent+label",
        hoverinfo="label+percent+value",
        marker=dict(
            colors=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],  
            line=dict(color="black", width=2),  
        )
    ))

    # Update layout to simulate depth
    fig.update_layout(
        title="Financial Overview",
        title_font_size=20,
        title_x=0.5,  
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        paper_bgcolor="rgba(0, 0, 0, 0)",  
        plot_bgcolor="rgba(0, 0, 0, 0)",
    )

    # Display the chart
    st.plotly_chart(fig, use_container_width=True)

def manage_income():
    st.subheader("💵 Income Management")
    with st.form("income_form"):
        source = st.text_input("Income Source")
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        category = st.selectbox("Category", ["Salary", "Freelance", "Business", "Investments", "Other"])
        date = st.date_input("Date", datetime.today())
        submitted = st.form_submit_button("Add Income")
        if submitted:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO incomes (source, amount, category, date) VALUES (?, ?, ?, ?)", (source, amount, category, date))
            conn.commit()
            conn.close()
            st.success("Income added successfully!")
            st.rerun()

def manage_expenses():
    st.subheader("💸 Expense Management")
    with st.form("expense_form"):
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        category = st.selectbox("Category", ["Food", "Rent", "Utilities", "Entertainment", "Other"])
        payment_method = st.selectbox("Payment Method", ["Cash", "Credit Card", "Debit Card", "Other"])
        date = st.date_input("Date", datetime.today())
        submitted = st.form_submit_button("Add Expense")
        if submitted:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO expenses (amount, category, payment_method, date) VALUES (?, ?, ?, ?)", (amount, category, payment_method, date))
            conn.commit()
            conn.close()
            st.success("Expense added successfully!")
            st.rerun()

def manage_savings():
    st.subheader("💰 Savings & Investments")

    # Fetch current savings data
    savings_df = fetch_data("SELECT * FROM savings LIMIT 1")

    if savings_df.empty:
        st.warning("No savings data found. Please set a savings goal and monthly savings amount.")
        total_savings, goal_amount, monthly_savings = 0.0, 0.0, 0.0
    else:
        total_savings = float(savings_df.iloc[0]["saved_amount"] or 0)
        goal_amount = float(savings_df.iloc[0]["goal_amount"] or 0)
        monthly_savings = float(savings_df.iloc[0]["monthly_savings"] or 0)

    
    # Display savings metrics
    st.metric("Total Savings", f"{currency_symbol}{total_savings:,.2f}")
    st.metric("Savings Goal", f"{currency_symbol}{goal_amount:,.2f}")
    st.metric("Monthly Savings", f"{currency_symbol}{monthly_savings:,.2f}")

    # Remaining amount to goal
    remaining_amount = max(goal_amount - total_savings, 0)
    st.metric("Remaining Amount to Goal", f"{currency_symbol}{remaining_amount:,.2f}")

    # Add Savings Form
    with st.form("add_savings_form"):
        st.subheader("Initial Savings amount")
        savings_amount = st.number_input("Amount to Add to Savings", min_value=0.0, format="%.2f")
        submitted_savings = st.form_submit_button("Add to Savings")
        if submitted_savings:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE savings SET saved_amount = saved_amount + ? WHERE id = (SELECT MIN(id) FROM savings)", (float(savings_amount),))
            conn.commit()
            conn.close()
            st.success(f"Added {currency_symbol}{savings_amount:,.2f} to savings!")
            st.rerun()

    # Update savings goal
    with st.form("savings_goal_form"):
        st.subheader("Savings Goal")
        new_goal = st.number_input("Set New Savings Goal", min_value=0.0, format="%.2f", value=goal_amount)
        submitted_goal = st.form_submit_button("Update Goal")
        if submitted_goal:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE savings SET goal_amount = ? WHERE id = (SELECT MIN(id) FROM savings)", (float(new_goal),))
            conn.commit()
            conn.close()
            st.success(f"Savings goal updated to {currency_symbol}{new_goal:,.2f}!")
            st.rerun()

    # Update monthly savings and deduct from remaining balance
    with st.form("monthly_savings_form"):
        st.subheader("Update Monthly Savings")
        new_monthly_savings = st.number_input("Amount to Add to Monthly Savings", min_value=0.0, format="%.2f")
        submitted_monthly = st.form_submit_button("Update Monthly Savings")
        if submitted_monthly:
            conn = get_connection()
            cursor = conn.cursor()
            # Add the new monthly savings to both monthly_savings and saved_amount
            cursor.execute("""
                UPDATE savings 
                SET monthly_savings = monthly_savings + ?, 
                    saved_amount = saved_amount + ? 
                WHERE id = (SELECT MIN(id) FROM savings)
            """, (float(new_monthly_savings), float(new_monthly_savings)))
            conn.commit()
            conn.close()
            st.success(f"Added {currency_symbol}{new_monthly_savings:,.2f} to monthly savings and total savings!")
            st.rerun()
    
    # Calculate time to reach the goal
    if goal_amount > 0 and monthly_savings > 0:
        st.subheader("⏳ Time to Reach Savings Goal")
        
        # Calculate months required to reach the goal
        months_to_goal = remaining_amount / monthly_savings
        st.write(f"At your current monthly savings rate of **{currency_symbol}{monthly_savings:,.2f}**, it will take approximately **{months_to_goal:.1f} months** to reach your goal.")
    elif goal_amount > 0 and monthly_savings <= 0:
        st.warning("Please set a monthly savings amount to calculate the time to reach your goal.")
    else:
        st.info("Set a savings goal and monthly savings amount to track your progress.")

# Function: Manage Debts
def manage_debts():
    st.subheader("📉 Debt Tracking")

    # Fetch all debts
    debts_df = fetch_data("SELECT * FROM debts")

    # Add new debt form
    with st.form("debt_form"):
        st.subheader("Add New Debt")
        creditor = st.text_input("Creditor Name")
        amount = st.number_input("Amount Owed", min_value=0.0, format="%.2f")
        interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, format="%.2f")
        min_payment = st.number_input("Minimum Payment", min_value=0.0, format="%.2f")
        submitted = st.form_submit_button("Add Debt")
        if submitted:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO debts (creditor, amount_owed, interest_rate, min_payment) VALUES (?, ?, ?, ?)", (creditor, amount, interest_rate, min_payment))
            conn.commit()
            conn.close()
            st.success("Debt added successfully!")
            st.rerun()

    # Display debts in a user-friendly format
    if not debts_df.empty:
        st.subheader("📝 Current Debts")
        for _, debt in debts_df.iterrows():
            with st.expander(f"**{debt['creditor']}**"):
                st.write(f"**Amount Owed:** {currency_symbol}{debt['amount_owed']:,.2f}")
                st.write(f"**Interest Rate:** {debt['interest_rate']:.2f}%")
                st.write(f"**Minimum Payment:** {currency_symbol}{debt['min_payment']:,.2f}")

    # Debt Repayment Calculator
    if not debts_df.empty:
        st.subheader("🧮 Debt Repayment Calculator")

        # Select a debt to calculate repayment
        debt_options = debts_df["creditor"].tolist()
        selected_debt = st.selectbox("Select a Debt to Calculate Repayment", debt_options)

        # Get details of the selected debt
        selected_debt_details = debts_df[debts_df["creditor"] == selected_debt].iloc[0]
        amount_owed = selected_debt_details["amount_owed"]
        interest_rate = selected_debt_details["interest_rate"]
        min_payment = selected_debt_details["min_payment"]

        # Display selected debt details
        st.write(f"**Amount Owed:** {currency_symbol}{amount_owed:,.2f}")
        st.write(f"**Interest Rate:** {interest_rate:.2f}%")
        st.write(f"**Minimum Payment:** {currency_symbol}{min_payment:,.2f}")

        # Calculate time to pay off debt with minimum payment
        st.subheader("⏳ Time to Pay Off Debt (Minimum Payment)")
        if min_payment > 0:
            monthly_interest_rate = (interest_rate / 100) / 12
            remaining_balance = amount_owed
            months = 0
            total_interest = 0

            while remaining_balance > 0:
                interest = remaining_balance * monthly_interest_rate
                principal = min_payment - interest
                remaining_balance -= principal
                total_interest += interest
                months += 1

            st.write(f"It will take **{months} months** (approximately **{months / 12:.1f} years**) to pay off this debt with the minimum payment.")
            st.write(f"**Total Interest Paid:** {currency_symbol}{total_interest:,.2f}")
        else:
            st.warning("Minimum payment must be greater than 0 to calculate repayment time.")

        # Additional Payments Section
        st.subheader("💸 Make Additional Payments")
        additional_payment = st.number_input("Additional Payment Amount", min_value=0.0, format="%.2f")
        if st.button("Apply Additional Payment"):
         if additional_payment > 0:
          conn = get_connection()
          cursor = conn.cursor()
        
          # Calculate interest for the current month
          monthly_interest_rate = (interest_rate / 100) / 12
          interest = amount_owed * monthly_interest_rate

          # Deduct interest from the additional payment
          principal_payment = additional_payment - interest
          if principal_payment < 0:
             st.error("Additional payment is not enough to cover the interest. Increase the payment amount.")
          else:
              # Update the amount owed
              new_amount_owed = amount_owed - principal_payment
              cursor.execute("UPDATE debts SET amount_owed = ? WHERE creditor = ?", (new_amount_owed, selected_debt))
            
              # Record the payment in the debt_payments table
              cursor.execute("INSERT INTO debt_payments (debt_id, payment_amount, payment_date) VALUES (?, ?, ?)", 
                          (selected_debt_details["id"], additional_payment, datetime.today().strftime("%Y-%m-%d")))
            
              # Deduct the additional payment from the remaining balance without debt
              cursor.execute("""
                  UPDATE savings 
                  SET saved_amount = saved_amount - ? 
                  WHERE id = (SELECT MIN(id) FROM savings)
              """, (float(additional_payment),))
            
              conn.commit()
              conn.close()

              st.success(f"Additional payment of {currency_symbol}{additional_payment:,.2f} applied to {selected_debt}!")
              st.write(f"**Interest Paid:** {currency_symbol}{interest:,.2f}")
              st.write(f"**Principal Paid:** {currency_symbol}{principal_payment:,.2f}")
              st.write(f"**New Amount Owed:** {currency_symbol}{new_amount_owed:,.2f}")
              st.rerun()
         else:
            st.warning("Additional payment must be greater than 0.")


if __name__ == "__main__":
    initialize_db()  # Ensure the database is initialized
    main()