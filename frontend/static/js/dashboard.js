// Global variables
let transactionData = [];
let categoryChart = null;
let balanceChart = null;
let monthlyChart = null;
let currentTransactionFilter = 'all';
let dashboardStats = {};

// Enhanced color palette for charts
const colors = [
    '#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe',
    '#43e97b', '#38f9d7', '#ffecd2', '#fcb69f', '#a8edea', '#fed6e3',
    '#d299c2', '#fef9d7', '#667eea', '#764ba2', '#f093fb', '#f5576c'
];

// Chart.js default configurations
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = '#6b7280';

// Allow SPA-like mounting without full reload
window.__DASHBOARD_DATA = window.__DASHBOARD_DATA || null;
window.mountDashboard = async function mountDashboard(options = {}) {
    initializeDashboard();
    setupEventListeners();
    if (window.__DASHBOARD_DATA && !options.forceReload) {
        transactionData = window.__DASHBOARD_DATA;
        await processAndDisplayData();
    } else {
        await loadDashboardData();
    }
};

// Auto-mount only on native page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.dashboard-container')) {
        window.mountDashboard();
    }
});

// Initialize dashboard components
function initializeDashboard() {
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
}

// Setup event listeners
function setupEventListeners() {
    // Back button functionality
    const backBtn = document.getElementById('backBtn');
    if (backBtn) {
        backBtn.addEventListener('click', handleBackNavigation);
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 'r':
                    e.preventDefault();
                    refreshDashboard();
                    break;
                case 'h':
                    e.preventDefault();
                    window.location.href = '/';
                    break;
            }
        }
    });

    // Add resize listener for responsive charts
    window.addEventListener('resize', debounce(handleResize, 300));
}

// Navigate back to home page
function handleBackNavigation(e) {
    e.preventDefault();
    
    // Add a small delay to show user feedback
    const backBtn = e.target.closest('button');
    const originalContent = backBtn.innerHTML;
    
    backBtn.innerHTML = `
        <svg viewBox="0 0 24 24" style="width: 16px; height: 16px;">
            <path d="m12 19-7-7 7-7"></path>
            <path d="m19 12H5"></path>
        </svg>
        Going back...
    `;
    backBtn.disabled = true;
    
    // Navigate after a short delay for visual feedback
    setTimeout(() => {
        window.location.href = '/';
    }, 200);
}



function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function handleResize() {
    // Resize charts if they exist
    [categoryChart, balanceChart, monthlyChart].forEach(chart => {
        if (chart) {
            chart.resize();
        }
    });
}



// Load transaction data with enhanced error handling
async function loadDashboardData() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    const errorMessage = document.getElementById('errorMessage');
    
    try {
        showLoadingState(true);
        
        // Fetch data with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
        
        const response = await fetch('/data/processed/categorized_transactions.json', {
            signal: controller.signal,
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        console.log('📊 Raw data received:', data);
        console.log('📊 Data type:', typeof data);
        console.log('📊 Is array:', Array.isArray(data));
        console.log('📊 Data length:', data ? data.length : 'undefined');
        
        if (!data || !Array.isArray(data) || data.length === 0) {
            console.error('❌ Data validation failed:', { data, isArray: Array.isArray(data), length: data?.length });
            throw new Error('No transaction data available');
        }
        
        transactionData = data;
        
        console.log(`✅ Loaded ${transactionData.length} transactions`);
        console.log('📊 Sample transaction:', transactionData[0]);
        
        // Process and display data with smooth animations
        await processAndDisplayData();
        
        showLoadingState(false);
        showNotification('Dashboard loaded successfully', 'success');
        
    } catch (error) {
        console.error('❌ Dashboard loading failed:', error);
        console.error('❌ Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        showLoadingState(false);
        
        if (error.name === 'AbortError') {
            showError('Request timed out. Please check your connection.');
        } else if (error.message.includes('HTTP 404')) {
            showError('Transaction data not found. Please upload your bank statement first.');
        } else {
            showError(`Failed to load data: ${error.message}`);
        }
    }
}

// Process and display data with animations
async function processAndDisplayData() {
    // Calculate dashboard stats
    calculateDashboardStats();
    
    // Update components with staggered animation
    const updates = [
        () => updateSummaryCards(),
        () => updateQuickStats(),
        () => createCategoryChart(),
        () => createBalanceChart(),
        () => createMonthlyChart(),
        () => updateCategoriesTable(),
        () => updateRecentTransactions()
    ];
    
    for (let i = 0; i < updates.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 100));
        updates[i]();
    }
}

// Calculate dashboard statistics
function calculateDashboardStats() {
    const parseAmt = (v) => (typeof v === 'number' ? v : parseFloat(String(v || '0').toString().replace(/,/g, ''))) || 0;
    const toDate = (d) => new Date(d);

    const totalIncome = transactionData.reduce((sum, t) => sum + parseAmt(t['Deposit(Cr)']), 0);
    const totalExpenses = transactionData.reduce((sum, t) => sum + parseAmt(t['Withdrawal(Dr)']), 0);
    const netBalance = totalIncome - totalExpenses;

    // Average transaction (non-zero), both credits and debits absolute
    const amounts = transactionData
        .map(t => Math.abs(parseAmt(t['Deposit(Cr)']) || parseAmt(t['Withdrawal(Dr)'])))
        .filter(a => a > 0);
    const avgTransaction = amounts.length ? amounts.reduce((a,b)=>a+b,0) / amounts.length : 0;

    // Determine period
    const dates = transactionData
        .map(t => toDate(t.Date))
        .filter(d => !isNaN(d.getTime()))
        .sort((a,b)=>a-b);
    const period = dates.length
        ? `${dates[0].toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })} – ${dates[dates.length-1].toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}`
        : '-';

    // Month buckets for trend
    const ym = (d) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
    const monthAgg = {};
    transactionData.forEach(t => {
        const d = toDate(t.Date);
        if (isNaN(d)) return;
        const key = ym(d);
        if (!monthAgg[key]) monthAgg[key] = { income: 0, expenses: 0, count: 0 };
        monthAgg[key].income += parseAmt(t['Deposit(Cr)']);
        monthAgg[key].expenses += parseAmt(t['Withdrawal(Dr)']);
        monthAgg[key].count += 1;
    });
    const months = Object.keys(monthAgg).sort();
    const last = months[months.length-1];
    const prev = months[months.length-2];
    const pct = (curr, prev) => {
        if (!prev) return 0;
        if (prev === 0) return curr > 0 ? 100 : 0;
        return ((curr - prev) / prev) * 100;
    };
    const incomeTrend = last ? pct(monthAgg[last].income, prev ? monthAgg[prev].income : 0) : 0;
    const expenseTrend = last ? pct(monthAgg[last].expenses, prev ? monthAgg[prev].expenses : 0) : 0;
    const transactionsTrend = last ? (monthAgg[last].count - (prev ? monthAgg[prev].count : 0)) : 0;
    const balanceTrend = incomeTrend - expenseTrend; // lightweight proxy

    dashboardStats = {
        totalIncome, totalExpenses, netBalance,
        avgTransaction, period,
        incomeTrend, expenseTrend, balanceTrend, transactionsTrend,
        months, monthAgg
    };
}

// Update top summary cards
function updateSummaryCards() {
    const setText = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
    setText('totalIncome', formatCurrency(dashboardStats.totalIncome));
    setText('totalExpenses', formatCurrency(dashboardStats.totalExpenses));
    setText('netBalance', formatCurrency(dashboardStats.netBalance));
    setText('totalTransactions', transactionData.length.toLocaleString());

    // Trends
    const incomeEl = document.getElementById('incomeTrend');
    if (incomeEl) applyTrend(incomeEl, dashboardStats.incomeTrend);
    const expenseEl = document.getElementById('expenseTrend');
    if (expenseEl) applyTrend(expenseEl, dashboardStats.expenseTrend, /*invertNegative*/ true);
    const balanceEl = document.getElementById('balanceTrend');
    if (balanceEl) applyTrend(balanceEl, dashboardStats.balanceTrend);
    const txEl = document.getElementById('transactionsTrend');
    if (txEl) applyTrend(txEl, dashboardStats.transactionsTrend, false, true);
}

function applyTrend(element, value, invertNegative = false, absolute = false) {
    const v = absolute ? value : Math.round(value * 10) / 10;
    const isPositive = invertNegative ? value < 0 : value >= 0;
    element.classList.remove('positive', 'negative');
    element.classList.add(isPositive ? 'positive' : 'negative');
    const arrowUp = '<svg viewBox="0 0 24 24"><path d="M7 14l5-5 5 5"></path></svg>';
    const arrowDown = '<svg viewBox="0 0 24 24"><path d="M7 10l5 5 5-5"></path></svg>';
    element.innerHTML = `${isPositive ? arrowUp : arrowDown}${absolute ? (value >=0 ? '+' : '') + value : ((isPositive ? '+' : '') + Math.abs(v).toFixed(1) + '%')}`;
}

// Quick stats bar
function updateQuickStats() {
    const dp = document.getElementById('dataPeriod');
    if (dp) dp.textContent = dashboardStats.period;
    const avg = document.getElementById('avgTransaction');
    if (avg) avg.textContent = formatCurrency(dashboardStats.avgTransaction);
}

// Create Category chart and legend
function createCategoryChart() {
    const canvas = document.getElementById('categoryChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Aggregate expenses by category (only debits)
    const categoryData = {};
    transactionData.forEach(t => {
        const cat = t.Category || 'Uncategorized';
        const amt = Math.max(0, (t['Withdrawal(Dr)'] || 0));
        if (amt > 0) categoryData[cat] = (categoryData[cat] || 0) + amt;
    });
    const entries = Object.entries(categoryData).sort((a,b)=>b[1]-a[1]).slice(0, 10);
    const labels = entries.map(e=>e[0]);
    const data = entries.map(e=>e[1]);
    const backgroundColors = colors.slice(0, labels.length);

    if (categoryChart) categoryChart.destroy();
    categoryChart = new Chart(ctx, {
        type: 'pie',
        data: { labels, datasets: [{ data, backgroundColor: backgroundColors, borderWidth: 2, borderColor: '#ffffff' }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (context) => {
                    const total = context.dataset.data.reduce((a,b)=>a+b,0);
                    const pct = total ? ((context.raw/total)*100).toFixed(1) : 0;
                    return `${context.label}: ${formatCurrency(context.raw)} (${pct}%)`;
                }}}
            }
        }
    });
    createCategoryLegend(labels, backgroundColors, data);
}

function createCategoryLegend(labels, colorsArr, data) {
    const legendContainer = document.getElementById('categoryLegend');
    if (!legendContainer) return;
    legendContainer.innerHTML = '';
    const total = data.reduce((a,b)=>a+b,0);
    labels.forEach((label, i) => {
        const pct = total ? ((data[i]/total)*100).toFixed(1) : 0;
        const div = document.createElement('div');
        div.className = 'legend-item';
        div.innerHTML = `<div class="legend-color" style="background-color:${colorsArr[i]}"></div><span>${label} (${pct}%)</span>`;
        legendContainer.appendChild(div);
    });
}

// Balance chart with time range filter
function createBalanceChart() {
    const canvas = document.getElementById('balanceChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const sorted = [...transactionData].sort((a,b)=> new Date(a.Date) - new Date(b.Date));
    const labels = sorted.map(t => formatDate(t.Date));
    const balances = sorted.map(t => (t.Balance || 0));

    if (balanceChart) balanceChart.destroy();
    balanceChart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets: [{
            label: 'Balance', data: balances,
            borderColor: '#2d7d32', backgroundColor: 'rgba(45,125,50,0.1)',
            borderWidth: 3, fill: true, tension: 0.35,
            pointBackgroundColor: '#2d7d32', pointBorderColor: '#ffffff', pointBorderWidth: 2, pointRadius: 3, pointHoverRadius: 5
        }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                x: { display: true, ticks: { maxTicksLimit: 10 } },
                y: { display: true, ticks: { callback: (v)=>formatCurrency(v) } }
            },
            plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx)=>`Balance: ${formatCurrency(ctx.raw)}` } } }
        }
    });
}

function updateTimeRange() {
    const sel = document.getElementById('timeRange');
    if (!sel || !balanceChart) return;
    const value = sel.value;
    let filtered = [...transactionData];
    if (value !== 'all') {
        const days = parseInt(value, 10);
        const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - days);
        filtered = transactionData.filter(t => new Date(t.Date) >= cutoff);
    }
    const sorted = filtered.sort((a,b)=> new Date(a.Date) - new Date(b.Date));
    balanceChart.data.labels = sorted.map(t => formatDate(t.Date));
    balanceChart.data.datasets[0].data = sorted.map(t => (t.Balance || 0));
    balanceChart.update();
}

// Monthly income vs expenses chart
function createMonthlyChart() {
    const canvas = document.getElementById('monthlyChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const monthKeys = dashboardStats.months;
    const incomes = monthKeys.map(m => dashboardStats.monthAgg[m].income);
    const expenses = monthKeys.map(m => dashboardStats.monthAgg[m].expenses);
    const labels = monthKeys.map(m => {
        const [y, mo] = m.split('-');
        return new Date(parseInt(y,10), parseInt(mo,10)-1).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
    });

    if (monthlyChart) monthlyChart.destroy();
    monthlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Income', data: incomes, backgroundColor: 'rgba(40,167,69,0.8)', borderColor: '#28a745', borderWidth: 2 },
                { label: 'Expenses', data: expenses, backgroundColor: 'rgba(220,53,69,0.8)', borderColor: '#dc3545', borderWidth: 2 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: true, position: 'top' }, tooltip: { callbacks: { label: (c)=>`${c.dataset.label}: ${formatCurrency(c.raw)}` } } },
            scales: { x: { display: true }, y: { display: true, ticks: { callback: (v)=>formatCurrency(v) } } }
        }
    });
}

function toggleBarChart(type) {
    if (!monthlyChart) return;
    monthlyChart.config.type = type;
    monthlyChart.update();
}

function toggleChartType(type) {
    if (!categoryChart) return;
    categoryChart.config.type = type;
    categoryChart.update();
    document.querySelectorAll('[data-type]')?.forEach(btn => btn.classList.remove('active'));
    const active = document.querySelector(`[data-type="${type}"]`);
    if (active) active.classList.add('active');
}

// Category table
function updateCategoriesTable() {
    const tbody = document.querySelector('#categoriesTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const categoryData = {};
    let totalExpenses = 0;
    transactionData.forEach(t => {
        const cat = t.Category || 'Uncategorized';
        const amt = (t['Withdrawal(Dr)'] || 0);
        if (amt > 0) {
            if (!categoryData[cat]) categoryData[cat] = { amount: 0, count: 0 };
            categoryData[cat].amount += amt;
            categoryData[cat].count += 1;
            totalExpenses += amt;
        }
    });

    const rows = Object.entries(categoryData).sort((a,b)=>b[1].amount - a[1].amount);
    rows.forEach(([cat, obj]) => {
        const percent = totalExpenses ? ((obj.amount/totalExpenses)*100).toFixed(1) : '0.0';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${cat}</strong></td>
            <td>${formatCurrency(obj.amount)}</td>
            <td>${obj.count}</td>
            <td>${percent}%
                <div class=\"percentage-bar\"><div class=\"percentage-fill\" style=\"width:${percent}%\"></div></div>
            </td>`;
        tbody.appendChild(tr);
    });
}

// Recent transactions
function updateRecentTransactions() {
    const container = document.getElementById('recentTransactions');
    if (!container) return;
    container.innerHTML = '';

    let filtered = [...transactionData].sort((a,b)=> new Date(b.Date) - new Date(a.Date));
    if (currentTransactionFilter === 'income') filtered = filtered.filter(t => (t['Deposit(Cr)'] || 0) > 0);
    if (currentTransactionFilter === 'expense') filtered = filtered.filter(t => (t['Withdrawal(Dr)'] || 0) > 0);

    filtered.slice(0, 20).forEach(t => {
        const isIncome = (t['Deposit(Cr)'] || 0) > 0;
        const amount = isIncome ? t['Deposit(Cr)'] : t['Withdrawal(Dr)'];
        const el = document.createElement('div');
        el.className = 'transaction-item';
        el.innerHTML = `
            <div class=\"transaction-info\">
                <div class=\"transaction-category\">${t.Category || 'Uncategorized'}</div>
                <div class=\"transaction-description\" title=\"${t.Narration}\">${t.Narration}</div>
                <div class=\"transaction-date\">${formatDate(t.Date)}</div>
            </div>
            <div class=\"transaction-amount\">
                <div class=\"amount-value ${isIncome ? 'income' : 'expense'}\">${isIncome ? '+' : '-'}${formatCurrency(amount)}</div>
                <div class=\"amount-type\">${isIncome ? 'Credit' : 'Debit'}</div>
            </div>`;
        container.appendChild(el);
    });
}

function toggleTransactionType() {
    const btn = document.getElementById('transactionToggle');
    if (!btn) return;
    if (currentTransactionFilter === 'all') { currentTransactionFilter = 'expense'; btn.textContent = 'Expenses'; }
    else if (currentTransactionFilter === 'expense') { currentTransactionFilter = 'income'; btn.textContent = 'Income'; }
    else { currentTransactionFilter = 'all'; btn.textContent = 'All'; }
    updateRecentTransactions();
}

// Refresh without page reload
async function refreshDashboard() {
    try {
        showLoadingState(true);
        await loadDashboardData();
    } finally {
        showLoadingState(false);
    }
}

// UI helpers
function showLoadingState(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (!overlay) return;
    overlay.style.display = show ? 'flex' : 'none';
}

function showError(message) {
    const err = document.getElementById('errorMessage');
    if (!err) return;
    err.style.display = 'block';
    const p = err.querySelector('p');
    if (p) p.textContent = message;
}

function showNotification(text, type = 'info') {
    const toast = document.createElement('div');
    toast.textContent = text;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.padding = '10px 14px';
    toast.style.background = type === 'success' ? 'rgba(45,125,50,0.9)' : 'rgba(0,0,0,0.7)';
    toast.style.color = '#fff';
    toast.style.borderRadius = '8px';
    toast.style.zIndex = 2000;
    document.body.appendChild(toast);
    setTimeout(()=> toast.remove(), 2000);
}

// Utils
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount || 0);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}