import streamlit as st
import pandas as pd
import os
import tempfile
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64

# Import your pipeline functions
try:
    from pipeline.table_extractor import extract_pdf_to_csv
    from pipeline.categorizer import categorize_transactions
    # from pipeline.faq import run_faq  # Commented out - not implemented yet
except ImportError as e:
    st.error(f"Error importing pipeline modules: {e}")
    st.error("Please ensure your pipeline modules are in the correct location")

    # Page configuration
st.set_page_config(
    page_title="Bank Statement Analyzer",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

def save_edited_data(df, filename="edited_categorized_transactions.csv"):
    """Save edited data to session state and provide download"""
    st.session_state.edited_data = df
    csv = df.to_csv(index=False)
    return csv

def category_editor(df):
    """Interactive category editor for manual corrections"""
    st.subheader("🖊️ Edit Transaction Categories")
    st.info("Select transactions to edit their categories. Changes are applied immediately.")
    
    # Make a copy to avoid modifying the original
    df_edit = df.copy()
    
    # Get unique categories for the selectbox
    if 'Category' in df_edit.columns:
        unique_categories = sorted(df_edit['Category'].unique())
        
        # Add option to create new category
        st.sidebar.markdown("### Category Management")
        new_category = st.sidebar.text_input("Add New Category", placeholder="Enter new category name")
        if new_category and st.sidebar.button("Add Category"):
            unique_categories.append(new_category)
            st.sidebar.success(f"Added category: {new_category}")
        
        # Filter options for easier editing
        st.sidebar.markdown("### Filter for Editing")
        categories_to_show = st.sidebar.multiselect(
            "Show categories",
            options=unique_categories,
            default=unique_categories,
            help="Filter transactions by category for easier editing"
        )
        
        # Search functionality
        search_term = st.sidebar.text_input("Search transactions", placeholder="Search by description, amount, etc.")
        
        # Apply filters
        filtered_df = df_edit[df_edit['Category'].isin(categories_to_show)] if categories_to_show else df_edit
        
        if search_term:
            # Search across all text columns
            text_columns = filtered_df.select_dtypes(include=['object']).columns
            mask = filtered_df[text_columns].astype(str).apply(
                lambda x: x.str.contains(search_term, case=False, na=False)
            ).any(axis=1)
            filtered_df = filtered_df[mask]
        
        st.info(f"Showing {len(filtered_df)} transactions (filtered from {len(df_edit)} total)")
        
        # Pagination for large datasets
        items_per_page = st.selectbox("Items per page", [10, 25, 50, 100], value=25)
        total_pages = (len(filtered_df) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            paginated_df = filtered_df.iloc[start_idx:end_idx]
        else:
            paginated_df = filtered_df
        
        # Display editable transactions
        if len(paginated_df) > 0:
            # Create columns for the editor
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write("**Transactions to Edit:**")
            with col2:
                if st.button("🔄 Reset All Changes", help="Reset all categories to original values"):
                    if 'original_data' in st.session_state:
                        st.session_state.edited_data = st.session_state.original_data.copy()
                                                        st.experimental_rerun()
            
            # Create editable interface
            changes_made = False
            
            for idx, row in paginated_df.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    
                    with col1:
                        # Show transaction details
                        description = row.get('Description', row.get('Narration', 'N/A'))
                        amount = row.get('Amount', 'N/A')
                        st.write(f"**{description[:50]}{'...' if len(str(description)) > 50 else ''}**")
                        st.caption(f"Amount: {amount}")
                    
                    with col2:
                        # Show original category
                        original_category = row['Category']
                        st.write(f"Current: `{original_category}`")
                    
                    with col3:
                        # Category selector
                        current_category = row['Category']
                        new_category_selection = st.selectbox(
                            f"New category",
                            options=unique_categories,
                            index=unique_categories.index(current_category) if current_category in unique_categories else 0,
                            key=f"cat_select_{idx}",
                            label_visibility="collapsed"
                        )
                        
                        # Update the dataframe if category changed
                        if new_category_selection != current_category:
                            df_edit.loc[idx, 'Category'] = new_category_selection
                            changes_made = True
                    
                    with col4:
                        # Quick actions
                        if st.button("↻", key=f"reset_{idx}", help="Reset this transaction"):
                            if 'original_data' in st.session_state:
                                original_category = st.session_state.original_data.loc[idx, 'Category']
                                df_edit.loc[idx, 'Category'] = original_category
                                changes_made = True
                                st.experimental_rerun()
                    
                    st.divider()
            
            # Save changes
            if changes_made or st.button("💾 Save All Changes", type="primary"):
                st.session_state.edited_data = df_edit
                st.success("✅ Changes saved! Updated data is now available in the Analytics Dashboard.")
                
                # Provide download link
                csv_data = save_edited_data(df_edit)
                st.download_button(
                    label="📥 Download Updated Data",
                    data=csv_data,
                    file_name="edited_categorized_transactions.csv",
                    mime="text/csv"
                )
                
                # Show summary of changes
                if 'original_data' in st.session_state:
                    original_cats = st.session_state.original_data['Category']
                    current_cats = df_edit['Category']
                    changed_count = (original_cats != current_cats).sum()
                    
                    if changed_count > 0:
                        st.info(f"📊 Summary: {changed_count} transactions have been recategorized")
                        
                        # Show category changes summary
                        changes_summary = []
                        for idx in df_edit.index:
                            if original_cats.loc[idx] != current_cats.loc[idx]:
                                changes_summary.append({
                                    'Transaction': df_edit.loc[idx].get('Description', 'N/A')[:30] + '...',
                                    'From': original_cats.loc[idx],
                                    'To': current_cats.loc[idx]
                                })
                        
                        if changes_summary:
                            changes_df = pd.DataFrame(changes_summary)
                            with st.expander("View All Changes"):
                                st.dataframe(changes_df, use_container_width=True)
        
        else:
            st.warning("No transactions match the current filters.")
    
    else:
        st.error("No 'Category' column found in the data. Please run categorization first.")
    
    return df_edit

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .step-header {
        font-size: 1.5rem;
        color: #2e8b57;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def create_download_link(df, filename, link_text):
    """Create a download link for a dataframe"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

def plot_transaction_summary(df):
    """Create comprehensive visualizations for transaction data"""
    try:
        # Debug: Show data info
        st.write("**Debug Info:**")
        st.write(f"Data shape: {df.shape}")
        st.write(f"Columns: {list(df.columns)}")
        st.write("Sample data:")
        st.dataframe(df.head(3), use_container_width=True)
        
        # Ensure we have the required columns
        if 'Amount' not in df.columns:
            st.error("Amount column not found in the data")
            st.write("Available columns:", list(df.columns))
            return
        
        # Convert Amount to numeric if it's not already
        df = df.copy()  # Work with a copy to avoid modifying original
        
        # Clean amount column - handle different formats
        df['Amount'] = df['Amount'].astype(str).str.replace(',', '').str.replace('₹', '').str.strip()
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        
        # Remove any NaN values
        original_count = len(df)
        df = df.dropna(subset=['Amount'])
        if len(df) < original_count:
            st.warning(f"Removed {original_count - len(df)} rows with invalid amounts")
        
        if df.empty:
            st.error("No valid transaction data after cleaning")
            return
        
        # Separate expenses and income (assuming negative amounts are expenses)
        expenses_df = df[df['Amount'] < 0].copy()
        income_df = df[df['Amount'] >= 0].copy()
        
        if not expenses_df.empty:
            expenses_df['Amount'] = expenses_df['Amount'].abs()  # Make expenses positive for better visualization
        
        # Summary metrics
        st.subheader("📊 Financial Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        total_expenses = expenses_df['Amount'].sum() if not expenses_df.empty else 0
        total_income = income_df['Amount'].sum() if not income_df.empty else 0
        net_balance = total_income - total_expenses
        total_transactions = len(df)
        
        with col1:
            st.metric("Total Expenses", f"₹{total_expenses:,.2f}")
        with col2:
            st.metric("Total Income", f"₹{total_income:,.2f}")
        with col3:
            st.metric("Net Balance", f"₹{net_balance:,.2f}")
        with col4:
            st.metric("Total Transactions", f"{total_transactions:,}")
        
        # Main visualizations
        if 'Category' in df.columns and not expenses_df.empty:
            # Row 1: Category Analysis
            st.subheader("💰 Category Analysis")
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart for expense categories (only expenses)
                expense_by_category = expenses_df.groupby('Category')['Amount'].sum().reset_index()
                expense_by_category = expense_by_category.sort_values('Amount', ascending=False)
                
                fig_pie = px.pie(
                    expense_by_category, 
                    values='Amount', 
                    names='Category',
                    title="💸 Expense Distribution by Category"
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Top categories bar chart
                top_categories = expenses_df.groupby('Category')['Amount'].sum().reset_index()
                top_categories = top_categories.sort_values('Amount', ascending=True).tail(10)
                
                fig_bar = px.bar(
                    top_categories, 
                    x='Amount', 
                    y='Category',
                    title="🔝 Top 10 Expense Categories",
                    orientation='h'
                )
                fig_bar.update_layout(height=400)
                st.plotly_chart(fig_bar, use_container_width=True)
        
        elif 'Category' not in df.columns:
            st.info("Category column not found. Please run categorization first to see category analysis.")
        
        # Time-based Analysis
        st.subheader("📈 Monthly Expense Trends")
        
        # Try to find date columns
        date_columns = []
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['date', 'time', 'transaction_date', 'txn_date']):
                date_columns.append(col)
        
        if date_columns:
            date_col = date_columns[0]
            st.info(f"Using '{date_col}' column for time analysis")
            
            try:
                # Convert to datetime
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                valid_dates = df.dropna(subset=[date_col])
                
                if not valid_dates.empty and not expenses_df.empty:
                    # For expenses, we need to merge with date info
                    expenses_with_dates = expenses_df.merge(
                        df[['Amount', date_col]].reset_index(), 
                        left_index=True, 
                        right_index=True, 
                        suffixes=('', '_orig')
                    )
                    
                    if not expenses_with_dates.empty:
                        # Create year-month column
                        expenses_with_dates['YearMonth'] = expenses_with_dates[date_col].dt.to_period('M').astype(str)
                        
                        monthly_expenses = expenses_with_dates.groupby('YearMonth')['Amount'].sum().reset_index()
                        monthly_expenses = monthly_expenses.sort_values('YearMonth')
                        
                        # Line chart for monthly expenses
                        fig_line = px.line(
                            monthly_expenses,
                            x='YearMonth',
                            y='Amount',
                            title='📉 Monthly Total Expenses',
                            markers=True
                        )
                        fig_line.update_layout(
                            xaxis_title="Month",
                            yaxis_title="Total Expenses (₹)",
                            height=400,
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(fig_line, use_container_width=True)
                        
                        # Monthly statistics table
                        st.subheader("📋 Monthly Summary")
                        monthly_stats = monthly_expenses.copy()
                        monthly_stats['Total Expenses'] = monthly_stats['Amount'].apply(lambda x: f"₹{x:,.2f}")
                        display_stats = monthly_stats[['YearMonth', 'Total Expenses']].rename(columns={'YearMonth': 'Month'})
                        st.dataframe(display_stats, use_container_width=True, hide_index=True)
                    else:
                        st.info("No expense data with valid dates found")
                else:
                    st.info("No valid dates found in the data")
                        
            except Exception as date_error:
                st.warning(f"Could not process date column '{date_col}': {str(date_error)}")
        
        else:
            st.warning("No date column found. Expected column names: 'Date', 'Transaction_Date', 'Txn_Date', etc.")
            st.write("Available columns:", list(df.columns))
        
        # Detailed breakdown
        if 'Category' in df.columns:
            st.subheader("📄 Detailed Category Breakdown")
            category_summary = df.groupby('Category').agg({
                'Amount': ['sum', 'count', 'mean']
            }).round(2)
            category_summary.columns = ['Total Amount', 'Transaction Count', 'Average Amount']
            category_summary = category_summary.sort_values('Total Amount')
            st.dataframe(category_summary, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error creating visualizations: {str(e)}")
        import traceback
        st.error(f"Full error: {traceback.format_exc()}")

def main():
    st.markdown('<h1 class="main-header">🏦 Bank Statement Analyzer</h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'categorized_data' not in st.session_state:
        st.session_state.categorized_data = None
    if 'original_data' not in st.session_state:
        st.session_state.original_data = None
    if 'edited_data' not in st.session_state:
        st.session_state.edited_data = None
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Upload & Process", "Edit Categories", "Analytics Dashboard"])
    
    # Debug info in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Debug Info:**")
    st.sidebar.write(f"Categorized data: {'✅' if st.session_state.categorized_data is not None else '❌'}")
    st.sidebar.write(f"Original data: {'✅' if st.session_state.original_data is not None else '❌'}")
    st.sidebar.write(f"Edited data: {'✅' if st.session_state.edited_data is not None else '❌'}")
    
    if st.session_state.categorized_data is not None:
        st.sidebar.write(f"Data shape: {st.session_state.categorized_data.shape}")
    
    # Add clear data button
    if st.sidebar.button("🗑️ Clear All Data"):
        st.session_state.categorized_data = None
        st.session_state.original_data = None
        st.session_state.edited_data = None
        st.sidebar.success("All data cleared!")
    
    if page == "Upload & Process":
        st.markdown('<div class="step-header">📄 Step 1: Upload Bank Statement PDF</div>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file", 
            type="pdf",
            help="Upload your bank statement PDF file"
        )
        
        if uploaded_file is not None:
            # Create temporary directories
            temp_dir = tempfile.mkdtemp()
            pdf_path = os.path.join(temp_dir, uploaded_file.name)
            csv_path = os.path.join(temp_dir, "bank_transactions.csv")
            categorized_csv_path = os.path.join(temp_dir, "categorized_bank_transactions.csv")
            
            # Save uploaded file
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✅ File uploaded successfully: {uploaded_file.name}")
            
            # Processing options
            st.markdown('<div class="step-header">⚙️ Processing Options</div>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                extract_tables = st.checkbox("Extract Tables from PDF", value=True)
            with col2:
                categorize_trans = st.checkbox("Categorize Transactions", value=True)
            # with col3:
            #     run_analysis = st.checkbox("Run FAQ Analysis", value=False)  # Commented out
            
            if st.button("🚀 Start Processing", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Step 1: Extract tables
                    if extract_tables:
                        status_text.text("Step 1: Extracting tables from PDF...")
                        progress_bar.progress(20)
                        extract_pdf_to_csv(pdf_path, csv_path)
                        st.markdown('<div class="success-box">✅ Step 1 Complete: Tables extracted successfully</div>', unsafe_allow_html=True)
                        
                        if os.path.exists(csv_path):
                            # Display extracted data
                            df_raw = pd.read_csv(csv_path)
                            st.subheader("📊 Extracted Transaction Data")
                            st.dataframe(df_raw.head(10), use_container_width=True)
                            st.info(f"Total transactions extracted: {len(df_raw)}")
                            
                            # Download link for raw data
                            st.markdown(create_download_link(df_raw, "bank_transactions.csv", "📥 Download Raw Data"), unsafe_allow_html=True)
                        
                        progress_bar.progress(40)
                    
                    # Step 2: Categorize transactions
                    if categorize_trans and os.path.exists(csv_path):
                        status_text.text("Step 2: Categorizing transactions...")
                        progress_bar.progress(60)
                        categorize_transactions(csv_path, categorized_csv_path)
                        st.markdown('<div class="success-box">✅ Step 2 Complete: Transactions categorized successfully</div>', unsafe_allow_html=True)
                        
                        if os.path.exists(categorized_csv_path):
                            # Display categorized data
                            df_categorized = pd.read_csv(categorized_csv_path)
                            st.subheader("🏷️ Categorized Transaction Data")
                            st.dataframe(df_categorized.head(10), use_container_width=True)
                            
                            # Download link for categorized data
                            st.markdown(create_download_link(df_categorized, "categorized_transactions.csv", "📥 Download Categorized Data"), unsafe_allow_html=True)
                            
                            # Store in session state for analytics and editing
                            st.session_state.categorized_data = df_categorized
                            st.session_state.original_data = df_categorized.copy()  # Keep original for reset functionality
                        
                        progress_bar.progress(80)
                    
                    # # Step 3: FAQ Analysis (Commented out)
                    # if run_analysis and os.path.exists(categorized_csv_path):
                    #     status_text.text("Step 3: Running FAQ analysis...")
                    #     progress_bar.progress(90)
                    #     faq_results = run_faq(categorized_csv_path)
                    #     st.markdown('<div class="success-box">✅ Step 3 Complete: FAQ analysis completed</div>', unsafe_allow_html=True)
                    #     
                    #     if faq_results:
                    #         st.subheader("❓ FAQ Analysis Results")
                    #         st.write(faq_results)
                    
                    progress_bar.progress(100)
                    status_text.text("🎉 Processing complete!")
                    
                    st.balloons()
                    
                except Exception as e:
                    st.markdown(f'<div class="error-box">❌ Error during processing: {str(e)}</div>', unsafe_allow_html=True)
                    st.error("Please check your pipeline modules and try again.")
    
    elif page == "Edit Categories":
        st.markdown('<div class="step-header">✏️ Edit Transaction Categories</div>', unsafe_allow_html=True)
        
        # Check if we have categorized data
        if 'categorized_data' in st.session_state:
            df = st.session_state.categorized_data
            
            # Use edited data if available
            if 'edited_data' in st.session_state:
                df = st.session_state.edited_data
                st.info("🔄 Showing previously edited data")
            
            st.success("✅ Using categorized data from current session")
            
            # Category editing interface
            edited_df = category_editor(df)
            
        else:
            st.warning("⚠️ No categorized data found. Please process a PDF file first.")
            st.info("👆 Go to 'Upload & Process' page to analyze your bank statement first.")
    
    elif page == "Analytics Dashboard":
        st.markdown('<div class="step-header">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
        
        # Check if we have data in session state
        if 'edited_data' in st.session_state:
            df = st.session_state.edited_data
            st.success("✅ Using edited data from current session")
        elif 'categorized_data' in st.session_state:
            df = st.session_state.categorized_data
            st.success("✅ Using categorized data from current session")
        else:
            # Option to upload a CSV directly
            st.info("No processed data found in current session. You can upload a CSV file directly:")
            uploaded_csv = st.file_uploader("Upload a CSV file", type="csv")
            
            if uploaded_csv is not None:
                df = pd.read_csv(uploaded_csv)
                st.success("✅ CSV file loaded successfully")
            else:
                st.warning("Please process a PDF file first or upload a CSV file to view analytics.")
                return
        
        # Display analytics
        if 'df' in locals():
            st.subheader("📈 Transaction Analytics")
            
            # Filter options
            st.sidebar.markdown("### Filters")
            
            # Date filter if date column exists
            date_columns = [col for col in df.columns if 'date' in col.lower() or 'Date' in col]
            if date_columns:
                date_col = st.sidebar.selectbox("Select Date Column", date_columns)
                try:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                    date_range = st.sidebar.date_input(
                        "Select Date Range",
                        value=(df[date_col].min().date(), df[date_col].max().date()),
                        min_value=df[date_col].min().date(),
                        max_value=df[date_col].max().date()
                    )
                    df = df[(df[date_col].dt.date >= date_range[0]) & (df[date_col].dt.date <= date_range[1])]
                except:
                    pass
            
            # Category filter
            if 'Category' in df.columns:
                categories = st.sidebar.multiselect(
                    "Select Categories",
                    options=df['Category'].unique(),
                    default=df['Category'].unique()
                )
                df = df[df['Category'].isin(categories)]
            
            # Display filtered data info
            st.info(f"Showing {len(df)} transactions after applying filters")
            
            # Generate plots
            plot_transaction_summary(df)
            
            # Raw data view
            if st.checkbox("Show Raw Data"):
                st.subheader("📋 Raw Data")
                st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()