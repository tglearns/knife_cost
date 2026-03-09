import streamlit as st
import pandas as pd
import io
import os
import math

# File path for the CSV file
CSV_FILE = 'knife_components_V2.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        # Ensure required columns exist and handle NaNs
        if 'Per_Knife_Cost' not in df.columns:
            df['Per_Knife_Cost'] = df['Purchase_Cost'] * df['Usage_Per_Knife'].fillna(0)
        if 'Fixed_cost' not in df.columns:
            df['Fixed_cost'] = 'N'
        df['Fixed_cost'] = df['Fixed_cost'].fillna('N')
        if 'Bar_Length' not in df.columns:
            df['Bar_Length'] = pd.NA
        if 'Usage_Per_Knife' not in df.columns:
            df['Usage_Per_Knife'] = 0.0
        else:
            df['Usage_Per_Knife'] = df['Usage_Per_Knife'].fillna(0.0)
        # Recalculate Per_Knife_Cost to be safe
        df['Per_Knife_Cost'] = df['Purchase_Cost'] * df['Usage_Per_Knife']
        return df
    else:
        cols = ['Category', 'Description', 'Purchase_Cost', 'Usage_Per_Knife', 
                'Per_Knife_Cost', 'Fixed_cost', 'Bar_Length']
        return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

st.title("Knife Build Cost Calculator")
st.markdown("### DEBUG: This is version with MULTISELECT fasteners – 2025-02")

# ── COST CALCULATOR ── (at the front)
st.header("Calculate Knife Build Cost")

desired_length = st.number_input(
    "Desired Knife/Blade Length (inches) – used to calculate steel usage",
    min_value=0.0, value=0.0, step=0.1,
    help="Leave at 0 to use stored Usage_Per_Knife values for steel"
)

df = load_data()

if not df.empty:
    categories = sorted(df['Category'].unique())
    selections = {}
    total = 0.0

    for cat in categories:
        cat_df = df[df['Category'] == cat]
        non_fixed = cat_df[cat_df['Fixed_cost'] == 'N']

        if non_fixed.empty:
            continue

        if cat.strip().lower() == "fastener":
            options = non_fixed['Description'].tolist()
            selected_descs = st.multiselect("Fastener Types", options)
            fastener_costs = []
            fastener_total = 0.0
            if selected_descs:
                for desc in selected_descs:
                    base_cost = non_fixed[non_fixed['Description'] == desc]['Purchase_Cost'].values[0]
                    qty_key = f"qty_{desc.replace(' ', '_').replace('-', '_').replace('.', '')}"
                    qty = st.number_input(
                        f"Number of {desc}",
                        min_value=0, value=0, step=1, key=qty_key,
                        help="How many of this fastener type per knife (cost = Purchase_Cost × quantity)"
                    )
                    if qty > 0:
                        cost = base_cost * qty
                        fastener_costs.append((desc, qty, cost))
                        fastener_total += cost
            if fastener_costs:
                selections[cat] = (fastener_costs, fastener_total)
                total += fastener_total
        else:
            options = ['None'] + non_fixed['Description'].tolist()
            selected = st.selectbox(f"{cat}", options, key=f"select_{cat}")
            if selected != 'None':
                row = non_fixed[non_fixed['Description'] == selected].iloc[0]

                if cat == "Steel" and desired_length > 0 and pd.notna(row['Bar_Length']) and row['Bar_Length'] > 0:
                    pieces_per_bar = math.floor(row['Bar_Length'] / desired_length)
                    if pieces_per_bar < 1:
                        st.warning(f"Desired length ({desired_length}\") > bar ({row['Bar_Length']}\") — using full bar cost!")
                        usage = 1.0
                    else:
                        usage = 1.0 / pieces_per_bar
                    cost = row['Purchase_Cost'] * usage
                    note = f" (dynamic: {pieces_per_bar} knives/bar)"
                else:
                    usage = row['Usage_Per_Knife']
                    cost = row['Per_Knife_Cost']
                    note = ""
                    if pd.isna(cost) or cost == 0:
                        st.warning(f"No valid cost data for {selected} — using $0")
                        cost = 0.0

                selections[cat] = (f"{selected}{note}", cost)
                total += cost

    # Fixed costs (always included)
    fixed_df = df[df['Fixed_cost'] == 'Y']
    if not fixed_df.empty:
        fixed_total = fixed_df['Per_Knife_Cost'].sum()
        total += fixed_total
        fixed_list = fixed_df.apply(lambda r: f"{r['Category']}: {r['Description']} (${r['Per_Knife_Cost']:.2f})", axis=1).tolist()
    else:
        fixed_total = 0.0
        fixed_list = []

    # Display summary
    if selections or fixed_total > 0:
        st.subheader("Selected / Included Components")
        for cat, info in selections.items():
            if cat.lower() == "fastener" and isinstance(info[0], list):  # small improvement: case insensitive
                st.write(f"- {cat}:")
                for desc, qty, c in info[0]:
                    st.write(f"  - {desc} × {qty} (${c:.2f})")
            else:
                label, c = info
                st.write(f"- {cat}: {label} (${c:.2f})")
        if fixed_list:
            st.write("**Fixed Costs (always included):**")
            for item in fixed_list:
                st.write(f"- {item}")
        st.markdown(f"**Total Cost per Knife: ${total:.2f}**")
    else:
        st.info("Select components above to calculate cost.")
else:
    st.info("No components in database yet. Add or upload data below.")



