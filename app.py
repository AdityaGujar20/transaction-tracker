import streamlit as st
import pandas as pd
import tempfile
import os
from dotenv import load_dotenv

# Import your existing processor class
# Adjust the import path based on your file structure
try:
    from processor.tab_cat_merged import BankStatementProcessor  # Adjust import name as needed
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False
    st.error("Could not import BankStatementProcessor. Please ensure the processor file is in the correct location.")

# Load environment variables
load_dotenv()

def main():
    st.set_page_config(
        page_title="Bank Statement Categorizer",
        page_icon="💳",
        layout="wide"
    )
    
    st.title("💳 Bank Statement Categorizer")
    st.markdown("Upload your bank statement PDF and get categorized transactions instantly!")
    
    # Initialize session state for storing processed data
    if 'df_processed' not in st.session_state:
        st.session_state.df_processed = None
    if 'processor' not in st.session_state:
        st.session_state.processor = None
    
    # Sidebar for API key
    st.sidebar.header("🔑 Configuration")
    
    # API Key input
    api_key = st.sidebar.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Enter your OpenAI API key. You can also set it in your .env file."
    )
    
    # Model selection
    model_choice = st.sidebar.selectbox(
        "Select Model",
        ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
        index=0,
        help="Choose the OpenAI model for categorization"
    )
    
    # Batch size
    batch_size = st.sidebar.slider(
        "Batch Size",
        min_value=5,
        max_value=50,
        value=20,
        help="Number of transactions to process per API call"
    )
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload Bank Statement")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            help="Upload your bank statement in PDF format"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            st.info(f"📄 File size: {uploaded_file.size / 1024:.1f} KB")
    
    with col2:
        st.header("⚙️ Processing Options")
        
        # Processing options
        show_raw_data = st.checkbox("Show extracted raw data", value=False)
        show_summary = st.checkbox("Show category summary", value=True)
        
        # Submit button
        process_button = st.button(
            "🚀 Process Statement",
            type="primary",
            disabled=not uploaded_file or not api_key or not PROCESSOR_AVAILABLE
        )
    
    # Processing section
    if process_button and uploaded_file and api_key and PROCESSOR_AVAILABLE:
        
        # Create a temporary file to save the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_pdf_path = tmp_file.name
        
        try:
            # Initialize progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize the processor
            status_text.text("🔧 Initializing processor...")
            progress_bar.progress(10)
            
            processor = BankStatementProcessor(api_key, model_name=model_choice)
            st.session_state.processor = processor
            
            # Extract transactions from PDF
            status_text.text("📄 Extracting transactions from PDF...")
            progress_bar.progress(30)
            
            try:
                df = processor.extract_bank_statement_table(tmp_pdf_path)
                df = processor.clean_and_format_data(df)
                
                if df.empty:
                    status_text.text("🔄 Trying alternative extraction method...")
                    df = processor.extract_transactions_regex(tmp_pdf_path)
                    df = processor.clean_and_format_data(df)
                    
            except Exception as e:
                status_text.text("🔄 Trying alternative extraction method...")
                df = processor.extract_transactions_regex(tmp_pdf_path)
                df = processor.clean_and_format_data(df)
            
            if df.empty:
                st.error("❌ No transactions found in the PDF. Please check the PDF format.")
                return
            
            st.success(f"✅ Successfully extracted {len(df)} transactions")
            progress_bar.progress(50)
            
            # Show raw data if requested
            if show_raw_data:
                st.subheader("📋 Extracted Raw Data")
                st.dataframe(df, use_container_width=True)
            
            # Convert to JSON for categorization
            status_text.text("🔄 Preparing data for categorization...")
            progress_bar.progress(60)
            
            transactions_json = processor.df_to_json_for_categorization(df)
            
            # Categorize transactions
            status_text.text("🤖 Categorizing transactions with AI...")
            progress_bar.progress(70)
            
            categorization_results = processor.batch_categorize_all_transactions(
                transactions_json, 
                batch_size=batch_size
            )
            
            # Add categories to dataframe
            status_text.text("📊 Preparing final results...")
            progress_bar.progress(90)
            
            categories = []
            for index in range(len(df)):
                category = categorization_results.get(index, "Miscellaneous")
                categories.append(category)
            
            df['Category'] = categories
            
            # Store in session state
            st.session_state.df_processed = df.copy()
            
            # Final progress
            progress_bar.progress(100)
            status_text.text("✅ Processing complete!")
            
        except Exception as e:
            st.error(f"❌ An error occurred during processing: {str(e)}")
            st.error("Please check your API key and try again.")
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_pdf_path):
                os.unlink(tmp_pdf_path)
    
    # Display results if we have processed data
    if st.session_state.df_processed is not None:
        df = st.session_state.df_processed.copy()
        processor = st.session_state.processor
        
        # Display results
        st.header("📊 Categorized Transactions")
        
        # Create year-month column for filtering
        df['Year-Month'] = df['Date'].dt.strftime('%Y-%m')
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.month
        
        # Get unique year-months for filtering
        unique_periods = sorted(df['Year-Month'].unique(), reverse=True)
        unique_years = sorted(df['Year'].unique(), reverse=True)
        
        # Filter controls
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            view_type = st.selectbox(
                "📅 View Type",
                ["All Transactions", "By Month-Year", "By Year"],
                index=0
            )
        
        with filter_col2:
            if view_type == "By Month-Year":
                selected_period = st.selectbox(
                    "Select Period",
                    ["All"] + unique_periods,
                    index=0
                )
            elif view_type == "By Year":
                selected_year = st.selectbox(
                    "Select Year",
                    ["All"] + unique_years,
                    index=0
                )
        
        with filter_col3:
            show_summary_tabs = st.checkbox("Show Monthly Comparison", value=True)
        
        # Filter dataframe based on selection
        if view_type == "By Month-Year" and selected_period != "All":
            filtered_df = df[df['Year-Month'] == selected_period].copy()
            st.subheader(f"📋 Transactions for {selected_period}")
        elif view_type == "By Year" and selected_year != "All":
            filtered_df = df[df['Year'] == selected_year].copy()
            st.subheader(f"📋 Transactions for {selected_year}")
        else:
            filtered_df = df.copy()
            st.subheader("📋 All Transactions")
        
        # Create columns for layout
        result_col1, result_col2 = st.columns([2, 1])
        
        with result_col1:
            # Add editing interface
            st.markdown("### 📝 Editable Transactions Table")
            st.info("💡 **Tip**: Use the data editor below to correct any misclassified categories. Changes will update the summary automatically!")
            
            # Prepare editable dataframe
            editable_df = filtered_df.copy()
            editable_df = editable_df.drop(columns=['Chq/Ref No', 'Year-Month', 'Year', 'Month'], errors='ignore')
            editable_df['Date'] = editable_df['Date'].dt.strftime('%d-%m-%Y')
            
            # Format currency columns for display but keep original values for editing
            display_cols = editable_df.columns.tolist()
            
            # Create the editable data editor
            edited_df = st.data_editor(
                editable_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": st.column_config.TextColumn(
                        "Date",
                        disabled=True,
                        help="Transaction date"
                    ),
                    "Description": st.column_config.TextColumn(
                        "Description", 
                        disabled=True,
                        help="Transaction description"
                    ),
                    "Withdrawal(Dr)": st.column_config.NumberColumn(
                        "Withdrawal(Dr)",
                        disabled=True,
                        format="₹%.2f",
                        help="Withdrawal amount"
                    ),
                    "Deposit(Cr)": st.column_config.NumberColumn(
                        "Deposit(Cr)",
                        disabled=True,
                        format="₹%.2f",
                        help="Deposit amount"
                    ),
                    "Balance": st.column_config.NumberColumn(
                        "Balance",
                        disabled=True,
                        format="₹%.2f",
                        help="Account balance"
                    ),
                    "Category": st.column_config.SelectboxColumn(
                        "Category",
                        options=processor.categories if processor else [
                            "Food & Dining", "Transportation", "Shopping", "Healthcare",
                            "Entertainment", "Utilities & Bills", "Financial Services",
                            "Personal Care", "Education", "Transfer/Refund", "Miscellaneous"
                        ],
                        help="Select the correct category",
                        required=True
                    )
                },
                key="transaction_editor"
            )
            
            # Update the main dataframe with edited categories
            if not edited_df.equals(editable_df):
                # Find which categories were changed
                category_changes = edited_df['Category'] != editable_df['Category']
                if category_changes.any():
                    # Update the filtered dataframe
                    filtered_df.loc[filtered_df.index, 'Category'] = edited_df['Category'].values
                    
                    # Update the main session dataframe
                    for idx, new_category in zip(filtered_df.index, edited_df['Category']):
                        st.session_state.df_processed.loc[idx, 'Category'] = new_category
                    
                    st.success("✅ Categories updated successfully!")
                    
                    # Force rerun to update summary
                    st.rerun()
        
        with result_col2:
            if show_summary:
                st.subheader("📈 Current Period Summary")
                
                # Calculate category statistics for filtered data (using updated categories)
                category_counts = filtered_df['Category'].value_counts()
                total_transactions = len(filtered_df)
                
                if total_transactions > 0:
                    # Create summary dataframe
                    summary_data = []
                    for category, count in category_counts.items():
                        percentage = (count / total_transactions) * 100
                        summary_data.append({
                            'Category': category,
                            'Count': count,
                            'Percentage': f"{percentage:.1f}%"
                        })
                    
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
                    
                    # Display total
                    st.metric("Total Transactions", total_transactions)
                    
                    # Show spending by category (for withdrawals only)
                    st.subheader("💰 Spending by Category")
                    spending_data = filtered_df[filtered_df['Withdrawal(Dr)'] > 0].groupby('Category')['Withdrawal(Dr)'].sum().sort_values(ascending=False)
                    
                    for category, amount in spending_data.head(5).items():  # Show top 5
                        st.metric(category, f"₹{amount:,.2f}")
                else:
                    st.info("No transactions in selected period")
        
        # Add a button to save/export updated categories
        st.markdown("---")
        save_col1, save_col2, save_col3 = st.columns([1, 1, 1])
        
        with save_col1:
            if st.button("🔄 Reset All Categories", type="secondary"):
                if st.session_state.processor:
                    # Show confirmation dialog
                    st.warning("⚠️ This will reset all categories to their original AI-generated values!")
                    
        with save_col2:
            # Show number of manual edits made
            if st.session_state.df_processed is not None:
                # Compare with original if we had it stored
                manual_edits = 0  # This would need to be tracked if we stored original categories
                st.info(f"📝 Manual edits made: {manual_edits}")
        
        # Monthly/Yearly Comparison Section (using updated dataframe)
        if show_summary_tabs and len(unique_periods) > 1:
            # Use the updated dataframe from session state
            df_for_analysis = st.session_state.df_processed.copy()
            df_for_analysis['Year-Month'] = df_for_analysis['Date'].dt.strftime('%Y-%m')
            
            st.header("📈 Monthly Category Analysis")
            
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["📊 Category by Month", "💰 Spending Trends", "📋 Summary Table"])
            
            with tab1:
                # Category distribution by month
                monthly_category = df_for_analysis.groupby(['Year-Month', 'Category']).size().unstack(fill_value=0)
                
                if not monthly_category.empty:
                    st.subheader("Transaction Count by Category and Month")
                    st.bar_chart(monthly_category)
                    
                    # Show percentage distribution
                    monthly_category_pct = monthly_category.div(monthly_category.sum(axis=1), axis=0) * 100
                    st.subheader("Category Distribution (%) by Month")
                    st.area_chart(monthly_category_pct)
            
            with tab2:
                # Spending trends by month
                monthly_spending = df_for_analysis[df_for_analysis['Withdrawal(Dr)'] > 0].groupby(['Year-Month', 'Category'])['Withdrawal(Dr)'].sum().unstack(fill_value=0)
                
                if not monthly_spending.empty:
                    st.subheader("Spending Amount by Category and Month")
                    st.bar_chart(monthly_spending)
                    
                    # Total monthly spending trend
                    total_monthly_spending = monthly_spending.sum(axis=1)
                    st.subheader("Total Monthly Spending Trend")
                    st.line_chart(total_monthly_spending)
            
            with tab3:
                # Detailed comparison table (using updated categories)
                comparison_data = []
                processor_categories = processor.categories if processor else [
                    "Food & Dining", "Transportation", "Shopping", "Healthcare",
                    "Entertainment", "Utilities & Bills", "Financial Services",
                    "Personal Care", "Education", "Transfer/Refund", "Miscellaneous"
                ]
                
                for period in unique_periods:
                    period_data = df_for_analysis[df_for_analysis['Year-Month'] == period]
                    category_counts = period_data['Category'].value_counts()
                    total_spending = period_data[period_data['Withdrawal(Dr)'] > 0]['Withdrawal(Dr)'].sum()
                    
                    for category in processor_categories:
                        count = category_counts.get(category, 0)
                        category_spending = period_data[
                            (period_data['Category'] == category) & 
                            (period_data['Withdrawal(Dr)'] > 0)
                        ]['Withdrawal(Dr)'].sum()
                        
                        comparison_data.append({
                            'Period': period,
                            'Category': category,
                            'Transaction Count': count,
                            'Total Spending': f"₹{category_spending:,.2f}",
                            'Avg per Transaction': f"₹{category_spending/count:,.2f}" if count > 0 else "₹0.00"
                        })
                
                comparison_df = pd.DataFrame(comparison_data)
                
                if not comparison_df.empty:
                    # Pivot table for better view
                    pivot_count = comparison_df.pivot(index='Category', columns='Period', values='Transaction Count').fillna(0)
                    
                    st.subheader("Transaction Count Comparison")
                    st.dataframe(pivot_count, use_container_width=True)
                    
                    # Filter to show only categories with transactions
                    active_categories = comparison_df[comparison_df['Transaction Count'] > 0]['Category'].unique()
                    filtered_comparison = comparison_df[comparison_df['Category'].isin(active_categories)]
                    
                    st.subheader("Detailed Spending Analysis")
                    st.dataframe(
                        filtered_comparison, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            'Period': st.column_config.TextColumn('Period'),
                            'Category': st.column_config.TextColumn('Category'),
                            'Transaction Count': st.column_config.NumberColumn('Count'),
                            'Total Spending': st.column_config.TextColumn('Total Spending'),
                            'Avg per Transaction': st.column_config.TextColumn('Avg/Transaction')
                        }
                    )
        
        # Download section (using updated dataframe)
        st.header("💾 Download Results")
        
        download_col1, download_col2 = st.columns(2)
        
        # Use the updated dataframe for downloads
        final_df = st.session_state.df_processed.copy()
        
        with download_col1:
            # Convert to CSV for download
            csv_data = final_df.to_csv(index=False)
            st.download_button(
                label="📄 Download Updated CSV",
                data=csv_data,
                file_name=f"categorized_transactions_updated.csv",
                mime="text/csv",
                help="Download CSV with your manually corrected categories"
            )
        
        with download_col2:
            # Convert to JSON for download
            json_data = final_df.to_json(orient='records', date_format='iso', indent=2)
            st.download_button(
                label="📄 Download Updated JSON",
                data=json_data,
                file_name=f"categorized_transactions_updated.json",
                mime="application/json",
                help="Download JSON with your manually corrected categories"
            )
    
    # Instructions section
    if st.session_state.df_processed is None:
        st.header("📋 Instructions")
        st.markdown("""
        **How to use this app:**
        
        1. **Set up API Key**: Enter your OpenAI API key in the sidebar (or set it in your .env file)
        2. **Upload PDF**: Upload your bank statement PDF file
        3. **Configure Options**: Choose model and batch size in the sidebar
        4. **Process**: Click the "Process Statement" button
        5. **Review & Edit**: Use the editable table to correct any misclassified categories
        6. **View Results**: See your categorized transactions and updated summaries
        7. **Download**: Download the results with your corrections as CSV or JSON
        
        **✨ New Features:**
        - **Editable Categories**: Click on any category in the table to change it using a dropdown
        - **Real-time Updates**: Summary statistics update automatically when you make changes
        - **Manual Corrections**: All your edits are preserved and included in downloads
        
        **Supported Categories:**
        - Food & Dining
        - Transportation
        - Shopping
        - Healthcare
        - Entertainment
        - Utilities & Bills
        - Financial Services
        - Personal Care
        - Education
        - Transfer/Refund
        - Miscellaneous
        
        **Note**: Make sure your PDF contains transaction data in a standard bank statement format.
        """)

if __name__ == "__main__":
    if not PROCESSOR_AVAILABLE:
        st.error("""
        ❌ **BankStatementProcessor not found!**
        
        Please ensure you have the processor file in the same directory and update the import statement:
        ```python
        from your_processor_file_name import BankStatementProcessor
        ```
        """)
    else:
        main()