// Global variables
let transactionData = [];
let categoryChart = null;
let balanceChart = null;
let monthlyChart = null;
let currentTransactionFilter = 'all';

// Color palette for charts
const colors = [
    '#2d7d32', '#388e3c', '#4caf50', '#66bb6a', '#81c784',
    '#a5d6a7', '#c8e6c9', '#16537e', '#1976d2', '#42a5f5',
    '#64b5f6', '#90caf9', '#bbdefb', '#e3f2fd', '#f3e5f5'
];

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
});

// Load transaction data from JSON file
async function loadDashboardData() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    const errorMessage = document.getElementById('errorMessage');
    
    try {
        loadingOverlay.style.display = 'flex';
        
        // Use the FastAPI endpoint instead of direct file path
        const response = await fetch('/data/processed/categorized_transactions.json');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        transactionData = await response.json();
        
        if (!transactionData || transactionData.length === 0) {
            throw new Error('No transaction data available');
        }
        
        console.log('Loaded transaction data:', transactionData.length, 'transactions');
        
        // Process and display data
        updateSummaryCards();
        createCategoryChart();
        createBalanceChart();
        createMonthlyChart();
        updateCategoriesTable();
        updateRecentTransactions();
        
        loadingOverlay.style.display = 'none';
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        loadingOverlay.style.display = 'none';
        errorMessage.style.display = 'block';
    }
}

// Update summary cards with calculated totals
function updateSummaryCards() {
    const totalIncome = transactionData.reduce((sum, t) => sum + (t['Deposit(Cr)'] || 0), 0);
    const totalExpenses = transactionData.reduce((sum, t) => sum + (t['Withdrawal(Dr)'] || 0), 0);
    const netBalance = totalIncome - totalExpenses;
    const totalTransactions = transactionData.length;
    
    document.getElementById('totalIncome').textContent = formatCurrency(totalIncome);
    document.getElementById('totalExpenses').textContent = formatCurrency(totalExpenses);
    document.getElementById('netBalance').textContent = formatCurrency(netBalance);
    document.getElementById('totalTransactions').textContent = totalTransactions.toLocaleString();
    
    // Update net balance color
    const balanceElement = document.getElementById('netBalance');
    if (netBalance >= 0) {
        balanceElement.style.color = '#28a745';
    } else {
        balanceElement.style.color = '#dc3545';
    }
}

// Create category spending pie chart
function createCategoryChart() {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    // Calculate spending by category (only expenses)
    const categoryData = {};
    transactionData.forEach(transaction => {
        const category = transaction.Category || 'Uncategorized';
        const amount = transaction['Withdrawal(Dr)'] || 0;
        
        if (amount > 0) {
            categoryData[category] = (categoryData[category] || 0) + amount;
        }
    });
    
    // Sort by amount and get top categories
    const sortedCategories = Object.entries(categoryData)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 10);
    
    const labels = sortedCategories.map(([category]) => category);
    const data = sortedCategories.map(([,amount]) => amount);
    const backgroundColors = colors.slice(0, labels.length);
    
    // Destroy existing chart
    if (categoryChart) {
        categoryChart.destroy();
    }
    
    categoryChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${formatCurrency(context.raw)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    // Create custom legend
    createCategoryLegend(labels, backgroundColors, data);
}

// Create custom legend for category chart
function createCategoryLegend(labels, colors, data) {
    const legendContainer = document.getElementById('categoryLegend');
    legendContainer.innerHTML = '';
    
    const total = data.reduce((a, b) => a + b, 0);
    
    labels.forEach((label, index) => {
        const percentage = ((data[index] / total) * 100).toFixed(1);
        
        const legendItem = document.createElement('div');
        legendItem.className = 'legend-item';
        legendItem.innerHTML = `
            <div class="legend-color" style="background-color: ${colors[index]}"></div>
            <span>${label} (${percentage}%)</span>
        `;
        legendContainer.appendChild(legendItem);
    });
}

// Create balance trend line chart
function createBalanceChart() {
    const ctx = document.getElementById('balanceChart').getContext('2d');
    
    // Sort transactions by date
    const sortedData = [...transactionData].sort((a, b) => new Date(a.Date) - new Date(b.Date));
    
    const labels = sortedData.map(t => formatDate(t.Date));
    const balanceData = sortedData.map(t => t.Balance || 0);
    
    // Destroy existing chart
    if (balanceChart) {
        balanceChart.destroy();
    }
    
    balanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Balance',
                data: balanceData,
                borderColor: '#2d7d32',
                backgroundColor: 'rgba(45, 125, 50, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#2d7d32',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    display: true,
                    ticks: {
                        maxTicksLimit: 10
                    }
                },
                y: {
                    display: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Balance: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            }
        }
    });
}

// Create monthly income vs expenses chart
function createMonthlyChart() {
    const ctx = document.getElementById('monthlyChart').getContext('2d');
    
    // Group data by month
    const monthlyData = {};
    
    transactionData.forEach(transaction => {
        const date = new Date(transaction.Date);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        
        if (!monthlyData[monthKey]) {
            monthlyData[monthKey] = { income: 0, expenses: 0 };
        }
        
        monthlyData[monthKey].income += transaction['Deposit(Cr)'] || 0;
        monthlyData[monthKey].expenses += transaction['Withdrawal(Dr)'] || 0;
    });
    
    // Sort by month
    const sortedMonths = Object.keys(monthlyData).sort();
    const labels = sortedMonths.map(month => {
        const [year, monthNum] = month.split('-');
        return new Date(year, monthNum - 1).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    });
    
    const incomeData = sortedMonths.map(month => monthlyData[month].income);
    const expenseData = sortedMonths.map(month => monthlyData[month].expenses);
    
    // Destroy existing chart
    if (monthlyChart) {
        monthlyChart.destroy();
    }
    
    monthlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Income',
                    data: incomeData,
                    backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    borderColor: '#28a745',
                    borderWidth: 2
                },
                {
                    label: 'Expenses',
                    data: expenseData,
                    backgroundColor: 'rgba(220, 53, 69, 0.8)',
                    borderColor: '#dc3545',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    display: true
                },
                y: {
                    display: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            }
        }
    });
}

// Update categories table
function updateCategoriesTable() {
    const tbody = document.querySelector('#categoriesTable tbody');
    tbody.innerHTML = '';
    
    // Calculate spending by category (only expenses)
    const categoryData = {};
    let totalExpenses = 0;
    
    transactionData.forEach(transaction => {
        const category = transaction.Category || 'Uncategorized';
        const amount = transaction['Withdrawal(Dr)'] || 0;
        
        if (amount > 0) {
            if (!categoryData[category]) {
                categoryData[category] = { amount: 0, count: 0 };
            }
            categoryData[category].amount += amount;
            categoryData[category].count++;
            totalExpenses += amount;
        }
    });
    
    // Sort by amount
    const sortedCategories = Object.entries(categoryData)
        .sort(([,a], [,b]) => b.amount - a.amount);
    
    sortedCategories.forEach(([category, data]) => {
        const percentage = ((data.amount / totalExpenses) * 100).toFixed(1);
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <strong>${category}</strong>
            </td>
            <td>${formatCurrency(data.amount)}</td>
            <td>${data.count}</td>
            <td>
                ${percentage}%
                <div class="percentage-bar">
                    <div class="percentage-fill" style="width: ${percentage}%"></div>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Update recent transactions
function updateRecentTransactions() {
    const container = document.getElementById('recentTransactions');
    container.innerHTML = '';
    
    // Sort transactions by date (newest first) and take last 20
    let filteredData = [...transactionData].sort((a, b) => new Date(b.Date) - new Date(a.Date));
    
    // Apply filter
    if (currentTransactionFilter === 'income') {
        filteredData = filteredData.filter(t => (t['Deposit(Cr)'] || 0) > 0);
    } else if (currentTransactionFilter === 'expense') {
        filteredData = filteredData.filter(t => (t['Withdrawal(Dr)'] || 0) > 0);
    }
    
    filteredData.slice(0, 20).forEach(transaction => {
        const isIncome = (transaction['Deposit(Cr)'] || 0) > 0;
        const amount = isIncome ? transaction['Deposit(Cr)'] : transaction['Withdrawal(Dr)'];
        
        const transactionElement = document.createElement('div');
        transactionElement.className = 'transaction-item';
        transactionElement.innerHTML = `
            <div class="transaction-info">
                <div class="transaction-category">${transaction.Category || 'Uncategorized'}</div>
                <div class="transaction-description" title="${transaction.Narration}">
                    ${transaction.Narration}
                </div>
                <div class="transaction-date">${formatDate(transaction.Date)}</div>
            </div>
            <div class="transaction-amount">
                <div class="amount-value ${isIncome ? 'income' : 'expense'}">
                    ${isIncome ? '+' : '-'}${formatCurrency(amount)}
                </div>
                <div class="amount-type">${isIncome ? 'Credit' : 'Debit'}</div>
            </div>
        `;
        container.appendChild(transactionElement);
    });
}

// Toggle chart type for category chart
function toggleChartType(type) {
    const buttons = document.querySelectorAll('[data-type]');
    buttons.forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-type="${type}"]`).classList.add('active');
    
    if (categoryChart) {
        categoryChart.config.type = type;
        categoryChart.update();
    }
}

// Toggle bar chart type
function toggleBarChart(type) {
    const buttons = document.querySelectorAll('[data-type]');
    buttons.forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-type="${type}"]`).classList.add('active');
    
    if (monthlyChart) {
        monthlyChart.config.type = type;
        monthlyChart.update();
    }
}

// Update time range for balance chart
function updateTimeRange() {
    const timeRange = document.getElementById('timeRange').value;
    let filteredData = [...transactionData];
    
    if (timeRange !== 'all') {
        const days = parseInt(timeRange);
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - days);
        
        filteredData = transactionData.filter(t => new Date(t.Date) >= cutoffDate);
    }
    
    // Update balance chart with filtered data
    const sortedData = filteredData.sort((a, b) => new Date(a.Date) - new Date(b.Date));
    const labels = sortedData.map(t => formatDate(t.Date));
    const balanceData = sortedData.map(t => t.Balance || 0);
    
    if (balanceChart) {
        balanceChart.data.labels = labels;
        balanceChart.data.datasets[0].data = balanceData;
        balanceChart.update();
    }
}

// Toggle transaction type filter
function toggleTransactionType() {
    const toggleBtn = document.getElementById('transactionToggle');
    
    if (currentTransactionFilter === 'all') {
        currentTransactionFilter = 'expense';
        toggleBtn.textContent = 'Expenses';
    } else if (currentTransactionFilter === 'expense') {
        currentTransactionFilter = 'income';
        toggleBtn.textContent = 'Income';
    } else {
        currentTransactionFilter = 'all';
        toggleBtn.textContent = 'All';
    }
    
    updateRecentTransactions();
}

// Refresh dashboard data
async function refreshDashboard() {
    const refreshBtn = document.querySelector('.refresh-btn');
    const originalText = refreshBtn.innerHTML;
    
    refreshBtn.innerHTML = `
        <div class="loading-spinner" style="width: 16px; height: 16px; margin: 0;"></div>
        Refreshing...
    `;
    refreshBtn.disabled = true;
    
    try {
        await loadDashboardData();
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
    } finally {
        refreshBtn.innerHTML = originalText;
        refreshBtn.disabled = false;
    }
}

// Utility function to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

// Utility function to format date
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}