import streamlit as st
import pandas as pd
import tempfile
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Import your existing processor class
try:
    from processor.tab_cat_merged import BankStatementProcessor
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False

# Load environment variables
load_dotenv()

# Custom CSS for beautiful styling
def load_custom_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Styles */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    .main-header h1 {
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        font-size: 1.2rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Card Styles */
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        border-left: 5px solid #667eea;
        margin: 1rem 0;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    .upload-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(240, 147, 251, 0.3);
    }
    
    .config-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(79, 172, 254, 0.3);
    }
    
    .results-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        border-top: 5px solid #43e97b;
        margin: 1rem 0;
    }
    
    /* Status Messages */
    .status-success {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: 500;
    }
    
    .status-processing {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: 500;
    }
    
    /* Metric Cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 3px 15px rgba(0,0,0,0.1);
        text-align: center;
        margin: 0.5rem 0;
        border-bottom: 3px solid #667eea;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin: 0.5rem 0 0 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Button Styles */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Instructions */
    .instructions-card {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        box-shadow: 0 10px 30px rgba(252, 182, 159, 0.3);
    }
    
    .instructions-card h3 {
        color: #8b4513;
        margin-bottom: 1rem;
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Data Editor Styling */
    .stDataEditor {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    /* Alert Styling */
    .element-container .alert {
        border-radius: 10px;
        border: none;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

def create_header():
    st.markdown("""
    <div class="main-header">
        <h1>💳 Bank Statement Categorizer</h1>
        <p>Transform your financial data with AI-powered transaction categorization</p>
    </div>
    """, unsafe_allow_html=True)

def check_api_key():
    """Check if API key is available from environment variables only"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("""
        🔑 **OpenAI API Key Required**
        
        Please set your OpenAI API key as an environment variable:
        ```bash
        export OPENAI_API_KEY="your-api-key-here"
        ```
        
        Or add it to your `.env` file:
        ```
        OPENAI_API_KEY=your-api-key-here
        ```
        """)
        return None
    return api_key

def create_upload_section():
    st.markdown("""
    <div class="upload-card">
        <h3>📤 Upload Your Bank Statement</h3>
        <p>Drag and drop your PDF file or click to browse</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "",
        type="pdf",
        help="Upload your bank statement in PDF format",
        label_visibility="collapsed"
    )
    
    return uploaded_file

def create_config_section():
    st.markdown("""
    <div class="config-card">
        <h3>⚙️ Processing Configuration</h3>
        <p>Customize your processing settings</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        model_choice = st.selectbox(
            "🤖 AI Model",
            ["gpt-3.5-turbo", "gpt-4", "gpt-4.1"],
            index=0,
            help="Choose the OpenAI model for categorization"
        )
    
    with col2:
        batch_size = st.slider(
            "📦 Batch Size",
            min_value=5,
            max_value=50,
            value=20,
            help="Number of transactions to process per API call"
        )
    
    return model_choice, batch_size

def create_processing_options():
    st.markdown("### 🎛️ Display Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        show_raw_data = st.checkbox("📋 Show extracted raw data", value=False)
        show_summary = st.checkbox("📊 Show category summary", value=True)
    
    with col2:
        show_charts = st.checkbox("📈 Show interactive charts", value=True)
        show_comparison = st.checkbox("📅 Show monthly comparison", value=True)
    
    return show_raw_data, show_summary, show_charts, show_comparison

def create_metric_cards(df):
    """Create beautiful metric cards"""
    col1, col2, col3, col4 = st.columns(4)
    
    total_transactions = len(df)
    total_withdrawals = df['Withdrawal(Dr)'].sum()
    total_deposits = df['Deposit(Cr)'].sum()
    unique_categories = df['Category'].nunique()
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_transactions}</div>
            <div class="metric-label">Total Transactions</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">₹{total_withdrawals:,.0f}</div>
            <div class="metric-label">Total Spent</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">₹{total_deposits:,.0f}</div>
            <div class="metric-label">Total Received</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{unique_categories}</div>
            <div class="metric-label">Categories Used</div>
        </div>
        """, unsafe_allow_html=True)

def create_interactive_charts(df):
    """Create beautiful interactive charts"""
    
    # Category distribution pie chart
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🍰 Transaction Distribution by Category")
        category_counts = df['Category'].value_counts()
        
        fig_pie = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(
            font=dict(family="Inter", size=12),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.markdown("#### 💰 Spending by Category")
        spending_data = df[df['Withdrawal(Dr)'] > 0].groupby('Category')['Withdrawal(Dr)'].sum().sort_values(ascending=True)
        
        fig_bar = px.bar(
            x=spending_data.values,
            y=spending_data.index,
            orientation='h',
            title="",
            color=spending_data.values,
            color_continuous_scale='viridis'
        )
        fig_bar.update_layout(
            font=dict(family="Inter", size=12),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=400,
            showlegend=False,
            xaxis_title="Amount (₹)",
            yaxis_title="Category"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

def create_monthly_analysis(df):
    """Create monthly analysis charts"""
    if 'Date' not in df.columns:
        return
        
    df['Year-Month'] = df['Date'].dt.strftime('%Y-%m')
    
    # Monthly spending trend
    st.markdown("#### 📈 Monthly Spending Trend")
    monthly_spending = df[df['Withdrawal(Dr)'] > 0].groupby('Year-Month')['Withdrawal(Dr)'].sum().reset_index()
    monthly_spending = monthly_spending.sort_values('Year-Month')
    
    fig_trend = px.line(
        monthly_spending,
        x='Year-Month',
        y='Withdrawal(Dr)',
        title="",
        markers=True,
        line_shape='spline'
    )
    fig_trend.update_traces(line_color='#667eea', marker_color='#764ba2')
    fig_trend.update_layout(
        font=dict(family="Inter", size=12),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=300,
        xaxis_title="Month",
        yaxis_title="Amount (₹)"
    )
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # Category heatmap by month
    st.markdown("#### 🔥 Category Activity Heatmap")
    monthly_category = df.groupby(['Year-Month', 'Category']).size().unstack(fill_value=0)
    
    if not monthly_category.empty:
        fig_heatmap = px.imshow(
            monthly_category.T,
            title="",
            color_continuous_scale='viridis',
            aspect='auto'
        )
        fig_heatmap.update_layout(
            font=dict(family="Inter", size=12),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=400,
            xaxis_title="Month",
            yaxis_title="Category"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

def create_instructions():
    st.markdown("""
    <div class="instructions-card">
        <h3>📋 How to Use This App</h3>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-top: 1rem;">
            <div>
                <h4>🔧 Setup</h4>
                <ul>
                    <li>Set your OpenAI API key as environment variable</li>
                    <li>Ensure your bank statement is in PDF format</li>
                    <li>Choose your preferred AI model and settings</li>
                </ul>
            </div>
            
            <div>
                <h4>📤 Process</h4>
                <ul>
                    <li>Upload your bank statement PDF</li>
                    <li>Click "Process Statement" to start</li>
                    <li>Wait for AI categorization to complete</li>
                </ul>
            </div>
            
            <div>
                <h4>✏️ Review & Edit</h4>
                <ul>
                    <li>Review categorized transactions</li>
                    <li>Edit categories using dropdown menus</li>
                    <li>View updated summaries and charts</li>
                </ul>
            </div>
            
            <div>
                <h4>💾 Export</h4>
                <ul>
                    <li>Download results as CSV or JSON</li>
                    <li>All manual corrections included</li>
                    <li>Ready for further analysis</li>
                </ul>
            </div>
        </div>
        
        <div style="margin-top: 2rem; padding: 1rem; background: rgba(255,255,255,0.3); border-radius: 10px;">
            <h4>🏷️ Available Categories</h4>
            <p><strong>Food & Dining</strong> • <strong>Transportation</strong> • <strong>Shopping</strong> • <strong>Healthcare</strong> • <strong>Entertainment</strong> • <strong>Utilities & Bills</strong> • <strong>Financial Services</strong> • <strong>Personal Care</strong> • <strong>Education</strong> • <strong>Transfer/Refund</strong> • <strong>Miscellaneous</strong></p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="Bank Statement Categorizer",
        page_icon="💳",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Load custom CSS
    load_custom_css()
    
    # Create beautiful header
    create_header()
    
    # Check for API key
    api_key = check_api_key()
    
    if not api_key:
        create_instructions()
        return
    
    # Initialize session state
    if 'df_processed' not in st.session_state:
        st.session_state.df_processed = None
    if 'processor' not in st.session_state:
        st.session_state.processor = None
    
    # Main content layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = create_upload_section()
        if uploaded_file:
            st.markdown(f"""
            <div class="status-success">
                ✅ File uploaded successfully: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        model_choice, batch_size = create_config_section()
    
    # Processing options
    st.markdown("---")
    show_raw_data, show_summary, show_charts, show_comparison = create_processing_options()
    
    # Process button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        process_button = st.button(
            "🚀 Process Bank Statement",
            type="primary",
            disabled=not uploaded_file or not PROCESSOR_AVAILABLE,
            use_container_width=True
        )
    
    # Processing section
    if process_button and uploaded_file and api_key and PROCESSOR_AVAILABLE:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_pdf_path = tmp_file.name
        
        try:
            # Progress tracking
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            # Processing steps with beautiful status messages
            status_text.markdown('<div class="status-processing">🔧 Initializing AI processor...</div>', unsafe_allow_html=True)
            progress_bar.progress(10)
            
            processor = BankStatementProcessor(api_key, model_name=model_choice)
            st.session_state.processor = processor
            
            status_text.markdown('<div class="status-processing">📄 Extracting transactions from PDF...</div>', unsafe_allow_html=True)
            progress_bar.progress(30)
            
            try:
                df = processor.extract_bank_statement_table(tmp_pdf_path)
                df = processor.clean_and_format_data(df)
                
                if df.empty:
                    status_text.markdown('<div class="status-processing">🔄 Trying alternative extraction method...</div>', unsafe_allow_html=True)
                    df = processor.extract_transactions_regex(tmp_pdf_path)
                    df = processor.clean_and_format_data(df)
                    
            except Exception as e:
                status_text.markdown('<div class="status-processing">🔄 Trying alternative extraction method...</div>', unsafe_allow_html=True)
                df = processor.extract_transactions_regex(tmp_pdf_path)
                df = processor.clean_and_format_data(df)
            
            if df.empty:
                st.error("❌ No transactions found in the PDF. Please check the PDF format.")
                return
            
            st.markdown(f"""
            <div class="status-success">
                ✅ Successfully extracted {len(df)} transactions
            </div>
            """, unsafe_allow_html=True)
            progress_bar.progress(50)
            
            if show_raw_data:
                st.markdown("### 📋 Extracted Raw Data")
                st.dataframe(df, use_container_width=True)
            
            status_text.markdown('<div class="status-processing">🔄 Preparing data for AI categorization...</div>', unsafe_allow_html=True)
            progress_bar.progress(60)
            
            transactions_json = processor.df_to_json_for_categorization(df)
            
            status_text.markdown('<div class="status-processing">🤖 AI is categorizing your transactions...</div>', unsafe_allow_html=True)
            progress_bar.progress(70)
            
            categorization_results = processor.batch_categorize_all_transactions(
                transactions_json, 
                batch_size=batch_size
            )
            
            status_text.markdown('<div class="status-processing">📊 Finalizing results...</div>', unsafe_allow_html=True)
            progress_bar.progress(90)
            
            categories = []
            for index in range(len(df)):
                category = categorization_results.get(index, "Miscellaneous")
                categories.append(category)
            
            df['Category'] = categories
            st.session_state.df_processed = df.copy()
            
            progress_bar.progress(100)
            status_text.markdown('<div class="status-success">✅ Processing completed successfully!</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"❌ An error occurred during processing: {str(e)}")
            
        finally:
            if os.path.exists(tmp_pdf_path):
                os.unlink(tmp_pdf_path)
    
    # Display results
    if st.session_state.df_processed is not None:
        df = st.session_state.df_processed.copy()
        processor = st.session_state.processor
        
        st.markdown("---")
        st.markdown("## 🎉 Your Categorized Transactions")
        
        # Metric cards
        create_metric_cards(df)
        
        # Interactive charts
        if show_charts:
            st.markdown("---")
            st.markdown("## 📊 Visual Analytics")
            create_interactive_charts(df)
        
        # Monthly analysis
        if show_comparison:
            st.markdown("---")
            st.markdown("## 📈 Monthly Analysis")
            create_monthly_analysis(df)
        
        # Editable transactions table
        st.markdown("---")
        st.markdown("## 📝 Review & Edit Transactions")
        
        st.markdown("""
        <div class="results-card">
            <h4>💡 Pro Tip</h4>
            <p>Click on any category in the table below to correct misclassifications. Your changes will automatically update all summaries and charts!</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Filter controls
        df['Year-Month'] = df['Date'].dt.strftime('%Y-%m')
        unique_periods = sorted(df['Year-Month'].unique(), reverse=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            view_type = st.selectbox("📅 View", ["All Transactions", "By Month"], index=0)
        
        with col2:
            if view_type == "By Month":
                selected_period = st.selectbox("Select Period", ["All"] + unique_periods, index=0)
            else:
                selected_period = "All"
        
        with col3:
            transactions_per_page = st.selectbox("Rows per page", [25, 50, 100, "All"], index=0)
        
        # Filter dataframe
        if view_type == "By Month" and selected_period != "All":
            filtered_df = df[df['Year-Month'] == selected_period].copy()
        else:
            filtered_df = df.copy()
        
        # Prepare editable dataframe
        editable_df = filtered_df.copy()
        editable_df = editable_df.drop(columns=['Chq/Ref No', 'Year-Month'], errors='ignore')
        editable_df['Date'] = editable_df['Date'].dt.strftime('%d-%m-%Y')
        
        # Create the editable data editor
        edited_df = st.data_editor(
            editable_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic" if transactions_per_page == "All" else transactions_per_page,
            column_config={
                "Date": st.column_config.TextColumn("Date", disabled=True, width="small"),
                "Description": st.column_config.TextColumn("Description", disabled=True, width="large"),
                "Withdrawal(Dr)": st.column_config.NumberColumn("Withdrawal", disabled=True, format="₹%.2f", width="medium"),
                "Deposit(Cr)": st.column_config.NumberColumn("Deposit", disabled=True, format="₹%.2f", width="medium"),
                "Balance": st.column_config.NumberColumn("Balance", disabled=True, format="₹%.2f", width="medium"),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=processor.categories if processor else [
                        "Food & Dining", "Transportation", "Shopping", "Healthcare",
                        "Entertainment", "Utilities & Bills", "Financial Services",
                        "Personal Care", "Education", "Transfer/Refund", "Miscellaneous"
                    ],
                    width="medium",
                    required=True
                )
            },
            key="transaction_editor"
        )
        
        # Update categories if changed
        if not edited_df.equals(editable_df):
            category_changes = edited_df['Category'] != editable_df['Category']
            if category_changes.any():
                for idx, new_category in zip(filtered_df.index, edited_df['Category']):
                    st.session_state.df_processed.loc[idx, 'Category'] = new_category
                
                st.markdown('<div class="status-success">✅ Categories updated successfully!</div>', unsafe_allow_html=True)
                st.rerun()
        
        # Download section
        st.markdown("---")
        st.markdown("## 💾 Export Your Results")
        
        col1, col2, col3 = st.columns(3)
        
        final_df = st.session_state.df_processed.copy()
        
        with col1:
            csv_data = final_df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name=f"categorized_transactions_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            json_data = final_df.to_json(orient='records', date_format='iso', indent=2)
            st.download_button(
                label="📄 Download JSON",
                data=json_data,
                file_name=f"categorized_transactions_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            excel_data = final_df.to_excel(index=False, engine='openpyxl')
            st.download_button(
                label="📊 Download Excel",
                data=excel_data,
                file_name=f"categorized_transactions_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    else:
        # Show instructions when no data is processed
        create_instructions()

if __name__ == "__main__":
    if not PROCESSOR_AVAILABLE:
        st.error("""
        ❌ **BankStatementProcessor not found!**
        
        Please ensure you have the processor file in the correct location and update the import statement.
        """)
    else:
        main()