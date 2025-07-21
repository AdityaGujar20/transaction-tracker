import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import json
from datetime import datetime

# Import your existing modules
from src.pdf_processor import extract_bank_statement_table, clean_and_format_data
from src.categorizer import BatchTransactionCategorizer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data/processed', exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process the PDF
            result = process_bank_statement(filepath, filename)
            if result['success']:
                return redirect(url_for('results', csv_file=result['csv_file']))
            else:
                flash(f"Error processing file: {result['error']}")
                return redirect(url_for('index'))
                
        except Exception as e:
            flash(f"Error processing file: {str(e)}")
            return redirect(url_for('index'))
    
    flash('Invalid file type. Please upload a PDF file.')
    return redirect(url_for('index'))

def process_bank_statement(pdf_path, filename):
    """Process bank statement PDF and return categorized results"""
    try:
        # Step 1: Extract transactions from PDF
        print("Extracting transactions from PDF...")
        df = extract_bank_statement_table(pdf_path)
        df = clean_and_format_data(df)
        
        if df.empty:
            return {'success': False, 'error': 'No transactions found in PDF'}
        
        # Save extracted CSV
        base_name = filename.split('.')[0]
        csv_path = f"data/processed/{base_name}_extracted.csv"
        df.to_csv(csv_path, index=False)
        
        # Step 2: Categorize transactions
        print("Categorizing transactions...")
        OPENAI_API_KEY = "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"
        
        categorizer = BatchTransactionCategorizer(OPENAI_API_KEY, model_name="gpt-3.5-turbo")
        
        # Convert to JSON format
        transactions_json = categorizer.csv_to_json(csv_path)
        
        # Categorize transactions
        categorization_results = categorizer.batch_categorize_all_transactions(
            transactions_json, batch_size=20
        )
        
        # Apply categories to dataframe
        categories = []
        for index in range(len(df)):
            category = categorization_results.get(index, "Miscellaneous")
            categories.append(category)
        
        df['Category'] = categories
        
        # Save categorized CSV
        categorized_csv_path = f"data/processed/{base_name}_categorized.csv"
        df.to_csv(categorized_csv_path, index=False)
        
        # Clean up uploaded file
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return {
            'success': True, 
            'csv_file': f"{base_name}_categorized.csv",
            'total_transactions': len(df)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/results/<csv_file>')
def results(csv_file):
    try:
        # Load the categorized data
        csv_path = f"data/processed/{csv_file}"
        df = pd.read_csv(csv_path)
        
        # Convert date column
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Prepare summary statistics
        summary_stats = prepare_summary_stats(df)
        
        # Prepare chart data
        chart_data = prepare_chart_data(df)
        
        return render_template('results.html', 
                             summary_stats=summary_stats,
                             chart_data=json.dumps(chart_data),
                             csv_file=csv_file)
                             
    except Exception as e:
        flash(f"Error loading results: {str(e)}")
        return redirect(url_for('index'))

def prepare_summary_stats(df):
    """Prepare summary statistics for the dashboard"""
    
    # Category-wise spending
    category_spending = df.groupby('Category').agg({
        'Withdrawal(Dr)': 'sum',
        'Deposit(Cr)': 'sum',
        'Date': 'count'
    }).rename(columns={'Date': 'Transaction_Count'}).round(2)
    
    # Overall statistics
    total_withdrawals = df['Withdrawal(Dr)'].sum()
    total_deposits = df['Deposit(Cr)'].sum()
    total_transactions = len(df)
    date_range = f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}"
    
    # Top spending categories
    top_categories = category_spending.nlargest(5, 'Withdrawal(Dr)')
    
    # Monthly spending trend
    df['YearMonth'] = df['Date'].dt.to_period('M')
    monthly_spending = df.groupby('YearMonth')['Withdrawal(Dr)'].sum().round(2)
    
    return {
        'total_withdrawals': total_withdrawals,
        'total_deposits': total_deposits,
        'total_transactions': total_transactions,
        'date_range': date_range,
        'category_spending': category_spending.to_dict('index'),
        'top_categories': top_categories.to_dict('index'),
        'monthly_spending': {str(k): v for k, v in monthly_spending.items()}
    }

def prepare_chart_data(df):
    """Prepare data for charts"""
    
    # Pie chart data - Category wise spending
    category_spending = df.groupby('Category')['Withdrawal(Dr)'].sum().round(2)
    pie_data = {
        'labels': category_spending.index.tolist(),
        'values': category_spending.values.tolist()
    }
    
    # Monthly trend data
    df['YearMonth'] = df['Date'].dt.to_period('M')
    monthly_data = df.groupby('YearMonth').agg({
        'Withdrawal(Dr)': 'sum',
        'Deposit(Cr)': 'sum'
    }).round(2)
    
    line_data = {
        'labels': [str(x) for x in monthly_data.index.tolist()],
        'withdrawals': monthly_data['Withdrawal(Dr)'].tolist(),
        'deposits': monthly_data['Deposit(Cr)'].tolist()
    }
    
    # Top 10 transactions
    top_transactions = df.nlargest(10, 'Withdrawal(Dr)')[
        ['Date', 'Narration', 'Withdrawal(Dr)', 'Category']
    ].copy()
    top_transactions['Date'] = top_transactions['Date'].dt.strftime('%Y-%m-%d')
    
    return {
        'pie_data': pie_data,
        'line_data': line_data,
        'top_transactions': top_transactions.to_dict('records')
    }

@app.route('/api/transaction-details/<csv_file>')
def transaction_details(csv_file):
    """API endpoint for detailed transaction data"""
    try:
        csv_path = f"data/processed/{csv_file}"
        df = pd.read_csv(csv_path)
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated_data = df.iloc[start:end].to_dict('records')
        
        return jsonify({
            'data': paginated_data,
            'total': len(df),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(df) + per_page - 1) // per_page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
