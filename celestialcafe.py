import streamlit as st 
from collections import defaultdict
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
import pandas as pd

# Replace this with your actual MongoDB Atlas connection string
MONGO_URI = "mongodb+srv://sr_db_user:shiana@shianaraghav.ihc9zgc.mongodb.net/?appName=shianaraghav"

# Connect to MongoDB Atlas
mongooncloud = MongoClient(MONGO_URI)

# Select database and collection
db = mongooncloud["celestialcafe"]
collection = db["customers"]

# Inject custom CSS
page_bg = """
<style>
.stApp {
    background-color: #D4FAFA; 
    background-image: 
        "url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%25%22 height=%22100%25%22><text x=%225%25%22 y=%2210%25%22 font-size=%2240%22>🧋</text><text x=%2250%25%22 y=%2250%25%22 font-size=%2240%22>🐼</text><text x=%2270%25%22 y=%2230%25%22 font-size=%2240%22>🦘</text><text x=%2220%25%22 y=%2270%25%22 font-size=%2240%22>✨</text><text x=%2280%25%22 y=%2280%25%22 font-size=%2240%22>🌸</text></svg>')";
    background-repeat: repeat;
    background-size: 200px 200px; /* Adjust size of emoji grid */
}
</style>
"""
st.markdown(page_bg, unsafe_allow_html=True)

# --- Tab Navigation ---
tabs = st.tabs(["Order Boba Tea", "About", "Contact", "Search Orders", "📊 Dashboard", "Review Orders"])

# --- Order Boba Tea Tab ---
with tabs[0]:
    st.title("🌌 Celestial Cafe - Your Cosmic Dining Experience")
    st.subheader("Today's special: Our exotic and amazing boba tea, it's out of this world!")
    st.write("This boba tea is made with a blend of cosmic fruits and topped with stardust sprinkles. It's a must-try for all space enthusiasts!")

    name = st.text_input("Enter your name:")
    date = st.date_input("Select the date for your order:")

    st.subheader("Boba tea flavors:")
    boba_flavors = [
        "Galaxy Grape", "Stellar Strawberry", "Nebula Nectar", "Meteor Mango", "Planetary Peach",
        "Supernova Strawberry", "Lunar Lychee", "Celestial Cherry", "Asteroid Apple", "Citrus Comet",
        "Solar Strawberry", "Milky Way Matcha", "Interstellar Iced Tea", "Lunar Lavender", "Galactic Green Tea",
        "Stardust Strawberry", "Nebula Nectarine", "Meteor Mango Melon", "Planetary Pineapple"
    ]
    selected_flavors = st.multiselect("Select your favorite boba tea flavors:", boba_flavors)
    if selected_flavors:
        st.write("You selected the following boba tea flavors:")
        for flavor in selected_flavors:
            st.write(f"- {flavor}")
    else:
        st.write("No flavors selected. You can choose some to enjoy your boba tea!")

    st.subheader("Boba pearls:")
    BobaPearls = [
        "Strawberry Jelly", "Rainbow Jelly", "Coconut Jelly", "Mango Jelly", "Bluberry Jelly", "Grape Jelly",
        "Passionfruit Jelly", "Lychee Jelly", "Peach Jelly", "Pineapple Jelly", "Matcha Jelly",
        "Strawberry Popping Pearls", "Rainbow Popping Pearls", "Coconut Popping Pearls", "Mango Popping Pearls",
        "Bluberry Popping Pearls", "Grape Popping Pearls", "Passionfruit Popping Pearls", "Lychee Popping Pearls",
        "Peach Popping Pearls", "Pineapple Popping Pearls", "Matcha Popping Pearls", "Strawberry Tapioca Pearls",
        "Rainbow Tapioca Pearls", "Coconut Tapioca Pearls", "Mango Tapioca Pearls", "Bluberry Tapioca Pearls",
        "Grape Tapioca Pearls", "Passionfruit Tapioca Pearls", "Lychee Tapioca Pearls", "Peach Tapioca Pearls",
        "Pineapple Tapioca Pearls", "Matcha Tapioca Pearls", "Classic Tapioca Pearls", "Chocolate Tapioca Pearls",
        "Vanilla Tapioca Pearls", "Caramel Tapioca Pearls"
    ]
    selected_pearls = st.multiselect("Select your favorite boba pearls:", BobaPearls)
    if selected_pearls:
        st.write("You selected the following boba pearls:")
        for pearl in selected_pearls:
            st.write(f"- {pearl}")
    else:
        st.write("No pearls selected. You can choose some to enhance your boba tea experience!")

    st.subheader("Boba tea sizes:")
    boba_sizes = ["Small", "Medium", "Large", "Extra Large"]
    selected_size = st.selectbox("Select your boba tea size:", boba_sizes)

    st.subheader("Boba tea toppings:")
    boba_toppings = [
        "Jelly Cubes", "Fruit Bits", "Whipped Cream", "Chocolate Drizzle", "Caramel Swirl",
        "Rainbow Sprinkles", "Coconut Shavings", "Matcha Powder"
    ]
    selected_toppings = st.multiselect("Select your favorite boba tea toppings:", boba_toppings)

    # --- Pricing ---
    total_cost = 0
    if selected_flavors:
        total_cost += len(selected_flavors) * 5
    if selected_pearls:
        total_cost += len(selected_pearls) * 2
    if selected_size == "Small":
        total_cost += 3
    elif selected_size == "Medium":
        total_cost += 4
    elif selected_size == "Large":
        total_cost += 5
    elif selected_size == "Extra Large":
        total_cost += 6
    if selected_toppings:
        total_cost += len(selected_toppings) * 2

    st.subheader("Order Summary")
    st.write(f"Name: {name}")
    st.write(f"Date: {date}")
    st.write(f"Selected Flavors: {', '.join(selected_flavors) if selected_flavors else 'None'}")
    st.write(f"Selected Pearls: {', '.join(selected_pearls) if selected_pearls else 'None'}")
    st.write(f"Selected Size: {selected_size}")
    st.write(f"Selected Toppings: {', '.join(selected_toppings) if selected_toppings else 'None'}")
    st.write(f"Total Cost: ${total_cost:.2f}")

    st.subheader("Order Confirmation")
    if st.button("Confirm Order"):
        document = {
            "cname": name,
            "date": str(date),
            "size": selected_size,
            "selected_flavors": selected_flavors,
            "selected_pearls": selected_pearls,
            "selected_toppings": selected_toppings,
            "totalcost": int(total_cost)
        }
        result = collection.insert_one(document)
        st.success("Your order has been confirmed! Enjoy your cosmic boba tea experience! 🌌🧋 Thank you for choosing Celestial Cafe! Your boba tea will be ready shortly.")
        with open("order.txt", "a") as order:
            order.write(f"Name: {name}\n")
            order.write(f"Date: {date}\n")
            order.write(f"Selected Flavors: {', '.join(selected_flavors) if selected_flavors else 'None'}\n")
            order.write(f"Selected Pearls: {', '.join(selected_pearls) if selected_pearls else 'None'}\n")
            order.write(f"Selected Size: {selected_size}\n")
            order.write(f"Selected Toppings: {', '.join(selected_toppings) if selected_toppings else 'None'}\n")
            order.write(f"Total Cost: ${total_cost:.2f}\n")
            order.write("--------------------------------------------------\n")
    else:
        st.info("Click the button to confirm your order.")

# --- About Tab ---
with tabs[1]:
    st.title("About Celestial Cafe")
    st.write("Celestial Cafe brings you cosmic flavors and a stellar experience. Our boba tea is crafted with the finest ingredients from across the galaxy!")

# --- Contact Tab ---
with tabs[2]:
    st.title("Contact Us")
    st.write("Questions or feedback? Reach out to us at contact@celestialcafe.com or visit us at our cosmic location!")

# --- Search Orders Tab ---
with tabs[3]:
    st.title("🔍 Search Previous Orders")

    search_name = st.text_input("Enter your name to find your past orders:")

    if search_name:
        try:
            with open("order.txt", "r") as f:
                lines=f.readlines()
            orders = []
            current_order = []

            for line in lines:
                if "--------------------------------------------------" in line:
                    if current_order:
                        orders.append("".join(current_order))
                        current_order = []
                else:
                    current_order.append(line)

            matching_orders = [order for order in orders if f"Name: {search_name}" in order]

            if matching_orders:
                st.success(f"Found {len(matching_orders)} order(s) for **{search_name}**:")
                for i, order in enumerate(matching_orders, 1):
                    st.text(f"Order #{i}\n{order}")
            else:
                st.warning("No orders found for that name.")
        except FileNotFoundError:
            st.error("Order file not found.")

# --- Dashboard Tab ---
with tabs[4]:
    st.title("📊 Celestial Cafe Dashboard")

    try:
        with open("order.txt", "r") as f:
            lines=[line.strip() for line in f if line.strip()]
        if not lines:
            st.warning("Order file is empty. No data available.")
        else:
            revenue_by_date=defaultdict(float)
            orders_by_date=defaultdict(int)
            current_date=None
            for line in lines:
                if line.startswith("Date: "):
                    current_date=line.split("Date: ")[1].strip()
                elif line.startswith("Total Cost: $") and current_date:
                    try:
                        amount=float(line.split("$")[1])
                        revenue_by_date[current_date] += amount
                        orders_by_date[current_date] += 1
                    except ValueError:
                        pass
                df = pd.DataFrame({
                "Date": list(revenue_by_date.keys()),
                "Revenue": list(revenue_by_date.values()),
                "Orders": list(orders_by_date.values())
            }).sort_values("Date")

            # Show summary table
            st.subheader("📅 Daily Totals")
            st.dataframe(df, use_container_width=True)

            # Show revenue trend
            st.subheader("💵 Revenue by Date")
            st.bar_chart(df.set_index("Date")["Revenue"])

            # Overall metrics
            total_revenue=sum(revenue_by_date.values())
            total_orders=sum(orders_by_date.values())
            st.metric("Total Revenue", f"${total_revenue:.2f}")
            st.metric("Total Orders", total_orders)

    except FileNotFoundError:
        st.warning("No orders have been placed yet. Dashboard data unavailable.")
# --- Review Orders Tab ---
with tabs[5]:
    # Read all documents
    documents = collection.find()

    # Convert JSON to DataFrame
    df = pd.DataFrame(documents)

    # Display as table
    st.title("🧋 Review All Boba Tea Orders")
    st.dataframe(df)    # Interactive table
# --- End of code ---