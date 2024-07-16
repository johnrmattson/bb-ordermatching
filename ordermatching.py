import streamlit as st
import pandas as pd
import altair as alt

# --- Functions ---
def crepe_erase_order_matching(client_df, blockboard_df):
    """Performs order matching specific to Crepe Erase."""
    filtered_client_df = client_df[client_df['order_medium'].isin(
        ['paid_search', 'direct', 'none', 'organic']
    )]
    client_transaction_ids = filtered_client_df['transaction_id'].astype(str).to_list()
    client_transaction_ids = [tid.strip() for tid in client_transaction_ids]
    
    blockboard_order_set = set(blockboard_df["Order ID"])
    match_count = sum(1 for order_id in blockboard_order_set if order_id in client_transaction_ids)
    
    matched_rows = [
        row.to_dict() for index, row in blockboard_df.iterrows()
        if row['Order ID'] in client_transaction_ids
    ]
    return match_count, pd.DataFrame(matched_rows)

def nutrisystem_order_matching(client_df, blockboard_df):
    """Performs order matching specific to Nutrisystem."""
    filtered_client_df = client_df[client_df['order_medium'].isin(
        ['cpc', '(none)', 'organic', 'tv', 'null'] 
    )]
    client_transaction_ids = filtered_client_df['transaction_id'].astype(str).to_list()
    client_transaction_ids = [tid.strip() for tid in client_transaction_ids]

    blockboard_order_set = set(blockboard_df["Order ID"])
    match_count = sum(1 for order_id in blockboard_order_set if order_id in client_transaction_ids)

    matched_rows = [
        row.to_dict() for index, row in blockboard_df.iterrows()
        if row['Order ID'] in client_transaction_ids
    ]
    return match_count, pd.DataFrame(matched_rows)

def smileactives_order_matching(client_df, blockboard_df):
    """Performs order matching specific to Smileactives."""
    filtered_client_df = client_df[client_df['order_medium'].isin(
        ['paid_search', 'direct', 'none', 'organic'] 
    )]
    client_transaction_ids = filtered_client_df['transaction_id'].astype(str).to_list()
    client_transaction_ids = [tid.strip() for tid in client_transaction_ids]
    
    blockboard_order_set = set(blockboard_df["Order ID"])
    match_count = sum(1 for order_id in blockboard_order_set if order_id in client_transaction_ids)
    
    matched_rows = [
        row.to_dict() for index, row in blockboard_df.iterrows()
        if row['Order ID'] in client_transaction_ids
    ]
    return match_count, pd.DataFrame(matched_rows)

def load_and_process_data(uploaded_client_file, uploaded_blockboard_file):
    """Loads, filters, and processes client and blockboard data."""
    client_df = pd.read_csv(uploaded_client_file)
    blockboard_df = pd.read_csv(uploaded_blockboard_file)

    # Blockboard data cleaning
    blockboard_df['Order ID'] = blockboard_df['Order ID'].astype(str).str.strip()
    blockboard_df = blockboard_df[~blockboard_df['Order ID'].str.contains("VALUE")]
    blockboard_df_deduped = blockboard_df.drop_duplicates(subset='Order ID', keep='first')

    for column in blockboard_df_deduped.columns:
        if column.startswith("Leads"):
            blockboard_df_deduped.loc[:, column] = blockboard_df_deduped[column].clip(upper=1)

    # --- Sorting by Date --- 
    # 1. Identify Date Columns
    client_date_column = 'easternstandardate'  # Replace with your actual client date column name
    blockboard_date_column = 'Date'  # Replace if needed

    # 2. Convert to Datetime (if not already)
    client_df[client_date_column] = pd.to_datetime(client_df[client_date_column])
    blockboard_df[blockboard_date_column] = pd.to_datetime(blockboard_df[blockboard_date_column])

    # 3. Sort by Date
    client_df = client_df.sort_values(by=client_date_column)
    blockboard_df_deduped = blockboard_df_deduped.sort_values(by=blockboard_date_column)        

    return client_df, blockboard_df_deduped 

def create_matched_orders_chart(matched_df, date_column='Date'):
    # Convert the date column to datetime if it's not already
    matched_df[date_column] = pd.to_datetime(matched_df[date_column])

    # Aggregate matched orders by date
    daily_matches = matched_df[date_column].dt.date.value_counts().reset_index()
    daily_matches.columns = [date_column, 'Matched Orders']

    # Create the Altair chart
    chart = alt.Chart(daily_matches).mark_line().encode(
        x=alt.X(date_column, axis=alt.Axis(title='Date', labelAngle=-45)),
        y=alt.Y('Matched Orders', axis=alt.Axis(title='Number of Matched Orders')),
        tooltip=[date_column, 'Matched Orders']
    ).properties(
        title='Matched Orders by Day'
    ).interactive()

    return chart


# --- Streamlit App ---
st.title("Blockboard Order Matching")

# Client Selection Dropdown (Default Blank)
client_selection = st.selectbox(
    "Select Client:", ["", "Crepe Erase", "Nutrisystem", "Smileactives"]  # Add blank option
)

# File upload section
uploaded_client_file = st.file_uploader("Upload Client Order Data (CSV)", type=['csv'])
uploaded_blockboard_file = st.file_uploader("Upload Blockboard Order Data (CSV)", type=['csv'])

# User input section
blockboard_spend = st.number_input("Enter Blockboard Media Spend:", value=0.00)
cpa = st.number_input("Enter CPA:", value=0.00)
order_goal = st.number_input("Enter IO Order Goal:", value=0, step=1)


# Data processing and display
if uploaded_client_file and uploaded_blockboard_file:
    client_df, blockboard_df_deduped = load_and_process_data(
        uploaded_client_file, uploaded_blockboard_file
    )

    num_blockboard_orders_unique = len(blockboard_df_deduped['Order ID'].unique())
    num_blockboard_orders = len(blockboard_df_deduped['Order ID'])

   # --- Client Selection Validation ---
    if client_selection:

        # Order Matching based on Selection
        if client_selection == "Crepe Erase":
            match_count, matched_df = crepe_erase_order_matching(
                client_df, blockboard_df_deduped
                # Create and display the chart
                st.altair_chart(create_matched_orders_chart(matched_df), use_container_width=True)
            )
        elif client_selection == "Nutrisystem":
            match_count, matched_df = nutrisystem_order_matching(
                client_df, blockboard_df_deduped
                # Create and display the chart
                st.altair_chart(create_matched_orders_chart(matched_df), use_container_width=True)
            )
        elif client_selection == "Smileactives":
            match_count, matched_df = smileactives_order_matching(
                client_df, blockboard_df_deduped
                # Create and display the chart
                st.altair_chart(create_matched_orders_chart(matched_df), use_container_width=True)
            )

        # Calculations 
        revenue = cpa * match_count
        total_cost = blockboard_spend
        profit = revenue - total_cost
        profit_margin = (profit / revenue) * 100 if revenue != 0 else 0.00

        # Display results
        st.subheader("Results:")
        st.write("Number of unique order IDs in Blockboard file:", num_blockboard_orders_unique)
        st.write("Number of order IDs in Blockboard file:", num_blockboard_orders)
        st.write("IO Order Goal:", order_goal)
        st.write("Matched Blockboard Order IDs:", match_count)
        st.write("Blockboard Revenue: {:.2f}".format(revenue))
        st.write("Blockboard Media Spend: {:.2f}".format(blockboard_spend))
        st.write("Blockboard CPO: {:.2f}".format(blockboard_spend / match_count if match_count != 0 else 0))
        st.write("Profit Margin: {:.2f}%".format(profit_margin))

     # --- Create Excel File with Multiple Tabs ---
        output_excel_file = "blockboard_data.xlsx" 

        with pd.ExcelWriter(output_excel_file, engine='xlsxwriter') as writer:
        # Convert date columns to datetime objects and format *before* writing 
            blockboard_df_deduped['Date'] = pd.to_datetime(blockboard_df_deduped['Date']).dt.date 
            matched_df['Date'] = pd.to_datetime(matched_df['Date']).dt.date

            blockboard_df_deduped.to_excel(writer, sheet_name="All Orders", index=False)
            matched_df.to_excel(writer, sheet_name="Matched Orders", index=False)

                # --- Format Date Columns ---
            workbook = writer.book
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'}) 

            worksheet1 = writer.sheets['All Orders']
            worksheet1.set_column(0, 0, 12, date_format) 

            worksheet2 = writer.sheets['Matched Orders']
            worksheet2.set_column(0, 0, 12, date_format) 


     # --- Download Button for Excel File ---
        st.download_button(
            label="Download Blockboard Data (Excel)",
            data=open(output_excel_file, 'rb').read(), 
            file_name=output_excel_file,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ) 

    else:
        st.warning("Please select a client from the dropdown menu.")

else:
    st.info("Please upload both CSV files to begin.")