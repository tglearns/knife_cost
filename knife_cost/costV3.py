import streamlit as st
import pandas as pd
import io
import os
import math

# File path for the Excel sheet
EXCEL_FILE = 'knife_components_V2.xlsx'

def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
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
        # Recalculate Per_Knife_Cost
        df['Per_Knife_Cost'] = df['Purchase_Cost'] * df['Usage_Per_Knife']
        return df
    else:
        cols = ['Category', 'Description', 'Purchase_Cost', 'Usage_Per_Knife', 
                'Per_Knife_Cost', 'Fixed_cost', 'Bar_Length']
        return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_excel(EXCEL_FILE, index=False)

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
            if cat == "Fasteners" and isinstance(info[0], list):
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

# ── DATABASE MANAGEMENT ──
st.header("Components Database")
if not df.empty:
    st.dataframe(df.sort_values('Category'))
else:
    st.info("No components yet.")

st.header("Add New Component")
with st.form(key='add_form'):
    category = st.text_input("Category")
    description = st.text_input("Description")
    purchase_cost = st.number_input("Purchase Cost ($)", min_value=0.0, step=0.01)
    usage_per_knife = st.number_input("Usage Per Knife (default/fallback)", min_value=0.0, step=0.01)
    bar_length = st.number_input("Bar Length (inches) - for Steel only", min_value=0.0, step=0.1)
    fixed_cost = st.checkbox("Fixed Cost (always include)")
    submit = st.form_submit_button("Add")

    if submit and category and description and purchase_cost > 0:
        per_knife = purchase_cost * usage_per_knife
        fixed_val = 'Y' if fixed_cost else 'N'
        new_row = pd.DataFrame({
            'Category': [category], 'Description': [description],
            'Purchase_Cost': [purchase_cost], 'Usage_Per_Knife': [usage_per_knife],
            'Per_Knife_Cost': [per_knife], 'Fixed_cost': [fixed_val],
            'Bar_Length': [bar_length if bar_length > 0 else pd.NA]
        })
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df)
        st.success("Added!")
        st.rerun()

st.header("Update Component")
if not df.empty:
    sel_idx = st.selectbox("Select to Update", df.index,
                           format_func=lambda i: f"{df.loc[i,'Category']} - {df.loc[i,'Description']}")
    if sel_idx is not None:
        with st.form(key='update_form'):
            cat = st.text_input("Category", df.loc[sel_idx, 'Category'])
            desc = st.text_input("Description", df.loc[sel_idx, 'Description'])
            pcost = st.number_input("Purchase Cost ($)", value=float(df.loc[sel_idx, 'Purchase_Cost']), step=0.01)
            usage = st.number_input("Usage Per Knife (default)", value=float(df.loc[sel_idx, 'Usage_Per_Knife']), step=0.01)
            bar_len = st.number_input("Bar Length (inches)", value=float(df.loc[sel_idx, 'Bar_Length']) if pd.notna(df.loc[sel_idx, 'Bar_Length']) else 0.0, step=0.1)
            fixed = st.checkbox("Fixed Cost", value=df.loc[sel_idx, 'Fixed_cost'] == 'Y')
            upd = st.form_submit_button("Update")
            if upd:
                new_per = pcost * usage
                fixed_val = 'Y' if fixed else 'N'
                df.loc[sel_idx] = [cat, desc, pcost, usage, new_per, fixed_val, bar_len if bar_len > 0 else pd.NA]
                save_data(df)
                st.success("Updated!")
                st.rerun()

st.header("Upload / Download Database")
up = st.file_uploader("Upload .xlsx to replace current data", type=['xlsx'])
if up:
    temp_df = pd.read_excel(up)
    required = ['Category', 'Description', 'Purchase_Cost']
    if all(c in temp_df.columns for c in required):
        if 'Usage_Per_Knife' not in temp_df.columns:
            temp_df['Usage_Per_Knife'] = 0.0
        if 'Per_Knife_Cost' not in temp_df.columns:
            temp_df['Per_Knife_Cost'] = temp_df['Purchase_Cost'] * temp_df['Usage_Per_Knife']
        if 'Fixed_cost' not in temp_df.columns:
            temp_df['Fixed_cost'] = 'N'
        if 'Bar_Length' not in temp_df.columns:
            temp_df['Bar_Length'] = pd.NA
        temp_df['Fixed_cost'] = temp_df['Fixed_cost'].fillna('N')
        temp_df['Usage_Per_Knife'] = temp_df['Usage_Per_Knife'].fillna(0.0)
        temp_df['Per_Knife_Cost'] = temp_df['Purchase_Cost'] * temp_df['Usage_Per_Knife']
        save_data(temp_df)
        st.success("Database updated from upload!")
        st.rerun()
    else:
        st.error(f"Missing required columns: {', '.join(set(required) - set(temp_df.columns))}")

if not df.empty:
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    st.download_button(
        label="Download Current Database as Excel",
        data=output.getvalue(),
        file_name='knife_components.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )