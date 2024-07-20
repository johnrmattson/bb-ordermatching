import streamlit as st
import pandas as pd
import altair as alt # type: ignore

# --- Configuration --- 
CLIENT_CONFIG = {
    "Crepe Erase": {
        "order_medium_filter": ['paid_search', 'direct', 'none', 'organic']
    },
    "Nutrisystem": {
        "order_medium_filter": ['cpc', '(none)', 'organic', 'tv', 'null']
    },
    "Smileactives": {
        "order_medium_filter": ['paid_search', 'direct', 'none', 'organic'] 
    }
}

# --- Functions ---
def match_orders(client_df: pd.DataFrame, 
                 blockboard_df: pd.DataFrame, 
                 client_name: str) -> tuple[int, pd.DataFrame]:
    """
    Performs order matching based on client-specific filters.

    Args:
        client_df (pd.DataFrame): DataFrame containing client order data.
        blockboard_df (pd.DataFrame): DataFrame containing Blockboard order data.
        client_name (str): Name of the client to apply specific filters. 

    Returns:
        tuple[int, pd.DataFrame]: A tuple containing the match count and 
                                    a DataFrame of matched orders.
    """
    
    filters = CLIENT_CONFIG.get(client_name, {}) 
    filtered_client_df = client_df[client_df['order_medium'].isin(
        filters.get("order_medium_filter", [])
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
    """Loads, filters, and processes client and Blockboard data."""
    try: 
        client_df = pd.read_csv(uploaded_client_file)
        blockboard_df = pd.read_csv(uploaded_blockboard_file)
    except Exception as e:
        st.error(f"Error loading files: {e}")
        return None, None

    # Blockboard Data Cleaning & Preprocessing
    blockboard_df['Order ID'] = blockboard_df['Order ID'].astype(str).str.strip()
    blockboard_df = blockboard_df[~blockboard_df['Order ID'].str.contains("VALUE")]
    blockboard_df = blockboard_df.drop_duplicates(subset='Order ID', keep='first')

    for column in blockboard_df.columns:
        if column.startswith("Leads"):
            blockboard_df.loc[:, column] = blockboard_df[column].clip(upper=1)

    # --- Date Handling --- 
    try: 
        client_df['easternstandardate'] = pd.to_datetime(client_df['easternstandardate'])
        blockboard_df['Date'] = pd.to_datetime(blockboard_df['Date'])
    except KeyError as e:
        st.error(f"Date column not found: {e}")
        return None, None 

    # --- Sorting ---
    client_df = client_df.sort_values(by='easternstandardate')
    blockboard_df = blockboard_df.sort_values(by='Date')   

    return client_df, blockboard_df

def create_matched_orders_chart(matched_df: pd.DataFrame, date_column='Date'):
    """Creates an Altair chart of matched orders by day."""
    matched_df['Date'] = pd.to_datetime(matched_df['Date'], errors='coerce')
    matched_df.dropna(subset=['Date'], inplace=True)
    
    daily_matches = matched_df[date_column].dt.date.value_counts().reset_index()
    daily_matches.columns = [date_column, 'Matched Orders']

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

client_selection = st.selectbox(
    "Select Client:", ["", *CLIENT_CONFIG.keys()] 
)

uploaded_client_file = st.file_uploader("Upload Client Order Data (CSV)", type=['csv'])
uploaded_blockboard_file = st.file_uploader("Upload Blockboard Order Data (CSV)", type=['csv'])

blockboard_spend = st.number_input("Enter Blockboard Media Spend:", value=0.00)
cpa = st.number_input("Enter CPA:", value=0.00)
order_goal = st.number_input("Enter IO Order Goal:", value=0, step=1)

if uploaded_client_file and uploaded_blockboard_file:
    client_df, blockboard_df = load_and_process_data(
        uploaded_client_file, uploaded_blockboard_file
    )

    if client_df is not None and blockboard_df is not None: 
        num_blockboard_orders_unique = len(blockboard_df['Order ID'].unique())
        num_blockboard_orders = len(blockboard_df['Order ID'])

        if client_selection:
            match_count, matched_df = match_orders(
                client_df, blockboard_df, client_selection
            )

            st.altair_chart(create_matched_orders_chart(matched_df), use_container_width=True)

            revenue = cpa * match_count
            total_cost = blockboard_spend
            profit = revenue - total_cost
            profit_margin = (profit / revenue) * 100 if revenue != 0 else 0.00

            st.subheader("Results:")
            st.write("Number of unique order IDs in Blockboard file:", num_blockboard_orders_unique)
            st.write("Number of order IDs in Blockboard file:", num_blockboard_orders)
            st.write("IO Order Goal:", order_goal)
            st.write("Matched Blockboard Order IDs:", match_count)
            st.write("Blockboard Revenue: {:.2f}".format(revenue))
            st.write("Blockboard Media Spend: {:.2f}".format(blockboard_spend))
            st.write("Blockboard CPO: {:.2f}".format(blockboard_spend / match_count if match_count != 0 else 0))
            st.write("Profit Margin: {:.2f}%".format(profit_margin))

            # --- Excel Output ---
            output_excel_file = "blockboard_data.xlsx" 

            with pd.ExcelWriter(output_excel_file, engine='xlsxwriter') as writer:
                blockboard_df['Date'] = blockboard_df['Date'].dt.date 
                matched_df['Date'] = matched_df['Date'].dt.date 

                blockboard_df.to_excel(writer, sheet_name="All Orders", index=False)
                matched_df.to_excel(writer, sheet_name="Matched Orders", index=False)

                # --- Format Date Columns ---
                workbook = writer.book
                date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'}) 

                worksheet1 = writer.sheets['All Orders']
                worksheet1.set_column('A:A', 12, date_format) # Assuming date is in the first column 'A'

                worksheet2 = writer.sheets['Matched Orders']
                worksheet2.set_column('A:A', 12, date_format) 

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