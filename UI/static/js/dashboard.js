/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * PROFETA Universal Dashboard - Main JavaScript
 * ═══════════════════════════════════════════════════════════════════════════════
 * 
 * Dashboard interattiva per il monitoraggio di PROFETA Universal v5.0
 * 
 * BilliDynamics™ 2026 - All Rights Reserved
 * ═══════════════════════════════════════════════════════════════════════════════
 */

'use strict';

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const CONFIG = {
    API_BASE: '',  // Same origin
    REFRESH_INTERVAL: 30000,  // 30 seconds
    PREDICTIONS_LIMIT: 100,   // Rows per page
    CHART_POINTS: 50,         // Points in sparkline
    DATE_FORMAT: {
        full: { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' },
        short: { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' },
        time: { hour: '2-digit', minute: '2-digit', second: '2-digit' }
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// STATE MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

const state = {
    status: null,
    config: null,
    predictionsCsv: null,
    predictionsJson: null,
    activeTab: 'overview',
    refreshTimer: null,
    lastUpdate: null
};

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Fetch JSON from API with error handling
 */
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${CONFIG.API_BASE}${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        return null;
    }
}

/**
 * Format number with precision
 */
function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) return '—';
    if (typeof value !== 'number') return value;
    
    if (Math.abs(value) >= 1e6) {
        return (value / 1e6).toFixed(2) + 'M';
    }
    if (Math.abs(value) >= 1e3) {
        return (value / 1e3).toFixed(2) + 'K';
    }
    if (Math.abs(value) < 0.0001 && value !== 0) {
        return value.toExponential(2);
    }
    return value.toFixed(decimals);
}

/**
 * Format percentage
 */
function formatPercent(value, decimals = 2) {
    if (value === null || value === undefined) return '—';
    return (value * 100).toFixed(decimals) + '%';
}

/**
 * Format timestamp
 */
function formatTimestamp(timestamp, format = 'full') {
    if (!timestamp) return '—';
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('it-IT', CONFIG.DATE_FORMAT[format]);
    } catch {
        return timestamp;
    }
}

/**
 * Get signal class for CSS
 */
function getSignalClass(signal) {
    const signalMap = {
        'STRONG_BUY': 'strong-buy',
        'BUY': 'buy',
        'HOLD': 'hold',
        'SELL': 'sell',
        'STRONG_SELL': 'strong-sell'
    };
    return signalMap[signal] || 'hold';
}

/**
 * Get class badge CSS class
 */
function getClassBadgeClass(cls) {
    return (cls || '').toLowerCase();
}

/**
 * Create element with attributes
 */
function createElement(tag, attrs = {}, children = []) {
    const el = document.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => {
        if (key === 'className') {
            el.className = value;
        } else if (key === 'innerHTML') {
            el.innerHTML = value;
        } else if (key === 'textContent') {
            el.textContent = value;
        } else if (key.startsWith('data')) {
            el.setAttribute(key.replace(/([A-Z])/g, '-$1').toLowerCase(), value);
        } else {
            el.setAttribute(key, value);
        }
    });
    children.forEach(child => {
        if (typeof child === 'string') {
            el.appendChild(document.createTextNode(child));
        } else if (child) {
            el.appendChild(child);
        }
    });
    return el;
}

/**
 * Debounce function
 */
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

// ═══════════════════════════════════════════════════════════════════════════════
// DATA FETCHING
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Fetch all data from APIs
 */
async function fetchAllData() {
    console.log('[Dashboard] Fetching data...');
    
    const [status, config, predictionsCsv, predictionsJson] = await Promise.all([
        fetchAPI('/api/status'),
        fetchAPI('/api/config'),
        fetchAPI('/api/predictions/csv'),
        fetchAPI('/api/predictions/json?limit=1000')
    ]);
    
    state.status = status;
    state.config = config;
    state.predictionsCsv = predictionsCsv;
    state.predictionsJson = predictionsJson;
    state.lastUpdate = new Date();
    
    console.log('[Dashboard] Data fetched:', { status, config: !!config, csv: !!predictionsCsv, json: !!predictionsJson });
    
    return { status, config, predictionsCsv, predictionsJson };
}

// ═══════════════════════════════════════════════════════════════════════════════
// HEADER RENDERING
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Update header status
 */
function updateHeader() {
    const status = state.status;
    
    // Update status indicator
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    
    if (status && status.config_loaded) {
        statusDot.className = 'status-dot';
        statusText.textContent = 'SISTEMA ONLINE';
    } else {
        statusDot.className = 'status-dot warning';
        statusText.textContent = 'CONFIG NON TROVATA';
    }
    
    // Update uptime
    const uptimeEl = document.getElementById('uptime');
    if (uptimeEl && status) {
        uptimeEl.textContent = status.uptime || '00:00:00';
    }
    
    // Update last prediction time
    const lastPredEl = document.getElementById('last-prediction');
    if (lastPredEl && status) {
        lastPredEl.textContent = formatTimestamp(status.last_prediction_time, 'short');
    }
}

/**
 * Update clock
 */
function updateClock() {
    const clockEl = document.getElementById('header-clock');
    if (clockEl) {
        clockEl.textContent = new Date().toLocaleString('it-IT', CONFIG.DATE_FORMAT.time);
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// METRICS RENDERING
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render metrics cards
 */
function renderMetrics() {
    const container = document.getElementById('metrics-container');
    if (!container) return;
    
    const json = state.predictionsJson;
    const csv = state.predictionsCsv;
    
    if (!json && !csv) {
        container.innerHTML = '<div class="loading"><div class="loading-spinner"></div><span class="loading-text">Caricamento metriche...</span></div>';
        return;
    }
    
    const metrics = json?.metrics || {};
    const metadata = json?.metadata || {};
    const stats = csv?.statistics || {};
    
    const regression = metrics.regression || {};
    const classification = metrics.classification || {};
    
    // Build metrics cards
    const cards = [
        {
            label: 'R² Score',
            value: formatNumber(regression.r2, 4),
            subtitle: 'Coefficiente determinazione',
            class: regression.r2 > 0.8 ? 'positive' : regression.r2 > 0.5 ? '' : 'negative'
        },
        {
            label: 'RMSE',
            value: formatNumber(regression.rmse, 2),
            subtitle: 'Root Mean Square Error',
            class: ''
        },
        {
            label: 'MAE',
            value: formatNumber(regression.mae, 2),
            subtitle: 'Mean Absolute Error',
            class: ''
        },
        {
            label: 'MAPE',
            value: formatPercent(regression.mape, 4),
            subtitle: 'Mean Absolute % Error',
            class: regression.mape < 0.01 ? 'positive' : ''
        },
        {
            label: 'Accuracy',
            value: formatPercent(classification.accuracy, 2),
            subtitle: 'Classificazione',
            class: classification.accuracy > 0.5 ? 'positive' : 'negative'
        },
        {
            label: 'F1 Score',
            value: formatNumber(classification.f1, 4),
            subtitle: 'Precisione/Recall bilanciato',
            class: classification.f1 > 0.5 ? 'positive' : ''
        },
        {
            label: 'Modelli Ensemble',
            value: metadata.num_models || '—',
            subtitle: `Versione ${metadata.version || 'N/A'}`,
            class: 'accent'
        },
        {
            label: 'Previsioni Totali',
            value: formatNumber(json?.predictions_count || csv?.total || 0, 0),
            subtitle: formatTimestamp(metadata.generated, 'short'),
            class: 'accent'
        }
    ];
    
    container.innerHTML = cards.map((card, i) => `
        <div class="metric-card animate-fadeIn stagger-${i % 5 + 1}">
            <span class="metric-label">${card.label}</span>
            <span class="metric-value ${card.class}">${card.value}</span>
            <span class="metric-subtitle">${card.subtitle}</span>
        </div>
    `).join('');
}

// ═══════════════════════════════════════════════════════════════════════════════
// SIGNALS SUMMARY
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render signals summary
 */
function renderSignalsSummary() {
    const container = document.getElementById('signals-summary');
    if (!container) return;
    
    const json = state.predictionsJson;
    const csv = state.predictionsCsv;
    
    const signals = json?.signals_summary || csv?.statistics?.signals_distribution || {};
    const total = Object.values(signals).reduce((a, b) => a + b, 0);
    
    if (total === 0) {
        container.innerHTML = '<div class="loading-text">Nessun segnale disponibile</div>';
        return;
    }
    
    const signalOrder = ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'];
    const signalLabels = {
        'STRONG_BUY': 'Strong Buy',
        'BUY': 'Buy',
        'HOLD': 'Hold',
        'SELL': 'Sell',
        'STRONG_SELL': 'Strong Sell'
    };
    
    container.innerHTML = `
        <div class="prob-bar-container">
            ${signalOrder.map(signal => {
                const count = signals[signal] || 0;
                const percent = total > 0 ? (count / total) * 100 : 0;
                return `
                    <div class="prob-bar">
                        <span class="prob-bar-label">${signalLabels[signal]}</span>
                        <div class="prob-bar-track">
                            <div class="prob-bar-fill ${getSignalClass(signal)}" style="width: ${percent}%"></div>
                        </div>
                        <span class="prob-bar-value">${count} (${percent.toFixed(1)}%)</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════════
// LATEST PREDICTION WIDGET
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render latest prediction
 */
function renderLatestPrediction() {
    const container = document.getElementById('latest-prediction');
    if (!container) return;
    
    const csv = state.predictionsCsv;
    const data = csv?.data || [];
    
    if (data.length === 0) {
        container.innerHTML = '<div class="loading-text">Nessuna previsione disponibile</div>';
        return;
    }
    
    // Get latest prediction
    const latest = data[data.length - 1];
    
    // Class probabilities
    const probs = latest.class_probs || { DOWN: 0.33, FLAT: 0.34, UP: 0.33 };
    
    container.innerHTML = `
        <div class="flex flex-col gap-lg">
            <!-- Main Value -->
            <div class="text-center">
                <div class="metric-label mb-md">VALORE PREDETTO</div>
                <div class="metric-value accent" style="font-size: 2.5rem;">
                    ${formatNumber(latest.predicted_value, 2)}
                </div>
                <div class="metric-subtitle mt-md">
                    ${formatTimestamp(latest.timestamp, 'full')}
                </div>
            </div>
            
            <!-- Signal Badge -->
            <div class="text-center">
                <span class="signal-badge ${getSignalClass(latest.signal)}" style="font-size: 1rem; padding: 8px 24px;">
                    ${latest.signal || 'N/A'}
                </span>
            </div>
            
            <!-- Confidence Gauge -->
            <div class="gauge-container">
                <div class="gauge">
                    <div class="gauge-bg"></div>
                    <div class="gauge-fill"></div>
                    <div class="gauge-needle" id="confidence-needle"></div>
                    <div class="gauge-center"></div>
                </div>
                <div class="gauge-value">${formatPercent(latest.confidence, 1)}</div>
                <div class="gauge-label">Confidence</div>
            </div>
            
            <!-- Class Probabilities -->
            <div class="prob-bar-container">
                <div class="prob-bar">
                    <span class="prob-bar-label">UP</span>
                    <div class="prob-bar-track">
                        <div class="prob-bar-fill up" style="width: ${(probs.UP || 0) * 100}%"></div>
                    </div>
                    <span class="prob-bar-value">${formatPercent(probs.UP, 1)}</span>
                </div>
                <div class="prob-bar">
                    <span class="prob-bar-label">FLAT</span>
                    <div class="prob-bar-track">
                        <div class="prob-bar-fill flat" style="width: ${(probs.FLAT || 0) * 100}%"></div>
                    </div>
                    <span class="prob-bar-value">${formatPercent(probs.FLAT, 1)}</span>
                </div>
                <div class="prob-bar">
                    <span class="prob-bar-label">DOWN</span>
                    <div class="prob-bar-track">
                        <div class="prob-bar-fill down" style="width: ${(probs.DOWN || 0) * 100}%"></div>
                    </div>
                    <span class="prob-bar-value">${formatPercent(probs.DOWN, 1)}</span>
                </div>
            </div>
            
            <!-- Additional Info -->
            <div class="grid grid-2 gap-md" style="margin-top: var(--space-md);">
                <div class="metric-card" style="padding: var(--space-md);">
                    <span class="metric-label">Change %</span>
                    <span class="metric-value ${latest.change_pct >= 0 ? 'positive' : 'negative'}" style="font-size: 1.2rem;">
                        ${formatPercent(latest.change_pct, 4)}
                    </span>
                </div>
                <div class="metric-card" style="padding: var(--space-md);">
                    <span class="metric-label">Agreement</span>
                    <span class="metric-value ${latest.agreement ? 'positive' : 'negative'}" style="font-size: 1.2rem;">
                        ${latest.agreement ? '✓ YES' : '✗ NO'}
                    </span>
                </div>
            </div>
        </div>
    `;
    
    // Animate needle
    setTimeout(() => {
        const needle = document.getElementById('confidence-needle');
        if (needle) {
            // Confidence goes from -1 (sell) to +1 (buy), needle rotates from -90 to +90
            const direction = latest.direction || 0;
            const confidence = latest.confidence || 0;
            const rotation = direction * confidence * 90;
            needle.style.transform = `translateX(-50%) rotate(${rotation}deg)`;
        }
    }, 100);
}

// ═══════════════════════════════════════════════════════════════════════════════
// FULL CSV VIEWER - Professional Visualization
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render the complete CSV viewer with all rows and columns
 */
function renderFullCSVViewer() {
    const wrapper = document.getElementById('csv-table-wrapper');
    if (!wrapper) return;
    
    const csv = state.predictionsCsv;
    const data = csv?.data || [];
    
    if (data.length === 0) {
        wrapper.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
                <span class="loading-text">Caricamento dati CSV...</span>
            </div>
        `;
        return;
    }
    
    // Update header stats
    const filenameEl = document.getElementById('csv-filename');
    const totalRowsEl = document.getElementById('csv-total-rows');
    const totalColsEl = document.getElementById('csv-total-cols');
    const lastUpdateEl = document.getElementById('csv-last-update');
    
    if (filenameEl && csv?.path) {
        const filename = csv.path.split('/').pop();
        filenameEl.textContent = filename;
    }
    
    if (totalRowsEl) {
        totalRowsEl.textContent = data.length.toLocaleString();
    }
    
    // Get column names from first row
    const columns = data.length > 0 ? Object.keys(data[0]) : [];
    
    if (totalColsEl) {
        totalColsEl.textContent = columns.length;
    }
    
    if (lastUpdateEl && csv?.statistics?.last_timestamp) {
        lastUpdateEl.textContent = formatTimestamp(csv.statistics.last_timestamp, 'short');
    }
    
    // Build table HTML
    const tableHTML = buildCSVTable(data, columns);
    wrapper.innerHTML = tableHTML;
}

/**
 * Build the CSV table HTML with professional styling
 */
function buildCSVTable(data, columns) {
    // Column display configuration
    const columnConfig = {
        'timestamp': { label: 'TIMESTAMP', class: 'col-timestamp', width: '160px' },
        'predicted_value': { label: 'VALORE PREDETTO', class: 'col-number col-predicted', width: '140px' },
        'change_pct': { label: 'CHANGE %', class: 'col-number col-change', width: '100px' },
        'class': { label: 'CLASSE', class: 'col-class', width: '80px' },
        'class_probs': { label: 'PROBABILITÀ', class: 'col-probs', width: '120px' },
        'cls_confidence': { label: 'CLS CONF.', class: 'col-number', width: '90px' },
        'direction': { label: 'DIR', class: 'col-number', width: '50px' },
        'confidence': { label: 'CONFIDENCE', class: 'col-confidence', width: '140px' },
        'agreement': { label: 'AGR', class: 'col-agreement', width: '50px' },
        'signal': { label: 'SEGNALE', class: 'col-signal', width: '120px' },
        'signal_strength': { label: 'STRENGTH', class: 'col-number', width: '90px' }
    };
    
    // Build header
    let headerHTML = '<tr><th class="row-index">#</th>';
    columns.forEach((col, idx) => {
        const config = columnConfig[col] || { label: col.toUpperCase(), class: '', width: 'auto' };
        headerHTML += `<th style="min-width: ${config.width}"><span class="col-index">${idx + 1}</span>${config.label}</th>`;
    });
    headerHTML += '</tr>';
    
    // Build rows (all rows, no limit)
    let bodyHTML = '';
    data.forEach((row, rowIdx) => {
        bodyHTML += `<tr style="animation-delay: ${Math.min(rowIdx * 0.01, 0.5)}s">`;
        bodyHTML += `<td class="row-index">${rowIdx + 1}</td>`;
        
        columns.forEach(col => {
            const value = row[col];
            const config = columnConfig[col] || { class: '' };
            bodyHTML += `<td class="${config.class}">${formatCSVCell(col, value)}</td>`;
        });
        
        bodyHTML += '</tr>';
    });
    
    return `
        <table class="csv-table">
            <thead>${headerHTML}</thead>
            <tbody>${bodyHTML}</tbody>
        </table>
    `;
}

/**
 * Format individual CSV cell with appropriate visualization
 */
function formatCSVCell(column, value) {
    switch (column) {
        case 'timestamp':
            return formatTimestamp(value, 'short');
        
        case 'predicted_value':
            return formatNumber(value, 2);
        
        case 'change_pct':
            const changeClass = value >= 0 ? 'positive' : 'negative';
            const arrow = value >= 0 ? '▲' : '▼';
            return `<span class="${changeClass}">${arrow} ${formatPercent(Math.abs(value), 4)}</span>`;
        
        case 'class':
            const classLower = (value || 'flat').toLowerCase();
            return `<span class="class-cell ${classLower}">${value || '—'}</span>`;
        
        case 'class_probs':
            return formatClassProbs(value);
        
        case 'confidence':
        case 'cls_confidence':
        case 'signal_strength':
            return formatConfidenceBar(value);
        
        case 'direction':
            if (value === 1) return '<span style="color: var(--signal-buy);">↑ +1</span>';
            if (value === -1) return '<span style="color: var(--signal-sell);">↓ -1</span>';
            return '<span style="color: var(--signal-hold);">→ 0</span>';
        
        case 'agreement':
            if (value === true || value === 'true' || value === 'True') {
                return '<span class="agreement-icon yes">✓</span>';
            }
            return '<span class="agreement-icon no">✗</span>';
        
        case 'signal':
            return formatSignalCell(value);
        
        default:
            if (typeof value === 'number') {
                return formatNumber(value, 6);
            }
            if (typeof value === 'boolean') {
                return value ? '✓' : '✗';
            }
            return value ?? '—';
    }
}

/**
 * Format class probabilities as mini bar chart
 */
function formatClassProbs(probs) {
    if (!probs || typeof probs !== 'object') {
        return '—';
    }
    
    const down = (probs.DOWN || 0) * 100;
    const flat = (probs.FLAT || 0) * 100;
    const up = (probs.UP || 0) * 100;
    
    return `
        <div class="probs-cell" title="DOWN: ${down.toFixed(1)}% | FLAT: ${flat.toFixed(1)}% | UP: ${up.toFixed(1)}%">
            <div class="prob-segment down" style="width: ${down}%"></div>
            <div class="prob-segment flat" style="width: ${flat}%"></div>
            <div class="prob-segment up" style="width: ${up}%"></div>
        </div>
    `;
}

/**
 * Format confidence as mini progress bar
 */
function formatConfidenceBar(value) {
    if (value === null || value === undefined) return '—';
    
    const percent = Math.min(Math.abs(value) * 100, 100);
    let fillClass = 'low';
    if (percent > 50) fillClass = 'high';
    else if (percent > 20) fillClass = 'medium';
    
    return `
        <div class="confidence-cell">
            <div class="confidence-bar">
                <div class="confidence-fill ${fillClass}" style="width: ${percent}%"></div>
            </div>
            <span class="confidence-value">${formatPercent(value, 2)}</span>
        </div>
    `;
}

/**
 * Format signal cell with icon and styling
 */
function formatSignalCell(signal) {
    const signalConfig = {
        'STRONG_BUY': { class: 'strong-buy', icon: '⬆⬆', label: 'STRONG BUY' },
        'BUY': { class: 'buy', icon: '⬆', label: 'BUY' },
        'HOLD': { class: 'hold', icon: '■', label: 'HOLD' },
        'SELL': { class: 'sell', icon: '⬇', label: 'SELL' },
        'STRONG_SELL': { class: 'strong-sell', icon: '⬇⬇', label: 'STRONG SELL' }
    };
    
    const config = signalConfig[signal] || { class: 'hold', icon: '?', label: signal || '—' };
    
    return `
        <span class="signal-cell ${config.class}">
            <span class="signal-icon">${config.icon}</span>
            ${config.label}
        </span>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION VIEWER
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render configuration viewer
 */
function renderConfig() {
    const container = document.getElementById('config-viewer');
    if (!container) return;
    
    const config = state.config;
    
    if (!config || !config.sections) {
        container.innerHTML = '<div class="loading"><div class="loading-spinner"></div><span class="loading-text">Caricamento configurazione...</span></div>';
        return;
    }
    
    const sections = config.sections;
    const sectionOrder = ['SYSTEM', 'DATA', 'MODEL', 'TRAINING', 'CLASSIFICATION', 'PREDICTION', 'SCHEDULER', 'REPORT'];
    
    // Sort sections: known ones first, then alphabetically
    const sortedSections = Object.keys(sections).sort((a, b) => {
        const aIndex = sectionOrder.indexOf(a);
        const bIndex = sectionOrder.indexOf(b);
        if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
        if (aIndex !== -1) return -1;
        if (bIndex !== -1) return 1;
        return a.localeCompare(b);
    });
    
    container.innerHTML = `
        <div class="config-viewer">
            ${sortedSections.map((sectionName, i) => {
                const section = sections[sectionName];
                const params = section.parameters || {};
                const paramCount = Object.keys(params).length;
                
                return `
                    <div class="config-section ${i > 3 ? 'collapsed' : ''}" data-section="${sectionName}">
                        <div class="config-section-header" onclick="toggleConfigSection('${sectionName}')">
                            <span class="config-section-title">
                                <span class="card-title-icon">⚙</span>
                                ${sectionName}
                                <span class="text-muted" style="font-size: 0.7rem; margin-left: 8px;">(${paramCount} parametri)</span>
                            </span>
                            <span class="config-section-toggle">▼</span>
                        </div>
                        <div class="config-section-body">
                            ${Object.entries(params).map(([key, value]) => {
                                let valueClass = '';
                                let displayValue = value;
                                
                                if (value === true) {
                                    valueClass = 'boolean-true';
                                    displayValue = 'true';
                                } else if (value === false) {
                                    valueClass = 'boolean-false';
                                    displayValue = 'false';
                                } else if (typeof value === 'number') {
                                    valueClass = 'number';
                                    displayValue = formatNumber(value, 6);
                                } else if (Array.isArray(value)) {
                                    displayValue = value.join(', ');
                                } else if (value === null) {
                                    valueClass = 'text-muted';
                                    displayValue = 'null';
                                }
                                
                                return `
                                    <div class="config-param">
                                        <span class="config-param-key">${key}</span>
                                        <span class="config-param-value ${valueClass}">${displayValue}</span>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

/**
 * Toggle config section
 */
function toggleConfigSection(sectionName) {
    const section = document.querySelector(`.config-section[data-section="${sectionName}"]`);
    if (section) {
        section.classList.toggle('collapsed');
    }
}

// Make it globally accessible
window.toggleConfigSection = toggleConfigSection;

// ═══════════════════════════════════════════════════════════════════════════════
// SPARKLINE CHART
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render sparkline chart using Canvas
 */
function renderSparkline() {
    const canvas = document.getElementById('sparkline-chart');
    if (!canvas) return;
    
    const csv = state.predictionsCsv;
    const data = csv?.data || [];
    
    if (data.length === 0) return;
    
    // Take last N points
    const points = data.slice(-CONFIG.CHART_POINTS);
    const values = points.map(p => p.predicted_value);
    
    const ctx = canvas.getContext('2d');
    const width = canvas.parentElement.clientWidth;
    const height = 200;
    
    canvas.width = width * 2;  // Retina
    canvas.height = height * 2;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.scale(2, 2);
    
    // Clear
    ctx.clearRect(0, 0, width, height);
    
    // Calculate bounds
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const padding = 20;
    
    // Draw grid
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding + (height - 2 * padding) * i / 4;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }
    
    // Draw line
    ctx.strokeStyle = '#00d4ff';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    
    ctx.beginPath();
    values.forEach((value, i) => {
        const x = padding + (width - 2 * padding) * i / (values.length - 1);
        const y = padding + (height - 2 * padding) * (1 - (value - min) / range);
        
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.stroke();
    
    // Draw glow effect
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.3)';
    ctx.lineWidth = 6;
    ctx.stroke();
    
    // Draw gradient fill
    const gradient = ctx.createLinearGradient(0, padding, 0, height - padding);
    gradient.addColorStop(0, 'rgba(0, 212, 255, 0.2)');
    gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');
    
    ctx.fillStyle = gradient;
    ctx.beginPath();
    values.forEach((value, i) => {
        const x = padding + (width - 2 * padding) * i / (values.length - 1);
        const y = padding + (height - 2 * padding) * (1 - (value - min) / range);
        
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.lineTo(width - padding, height - padding);
    ctx.lineTo(padding, height - padding);
    ctx.closePath();
    ctx.fill();
    
    // Draw points
    ctx.fillStyle = '#00d4ff';
    values.forEach((value, i) => {
        const x = padding + (width - 2 * padding) * i / (values.length - 1);
        const y = padding + (height - 2 * padding) * (1 - (value - min) / range);
        
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
    });
    
    // Draw last point larger with glow
    if (values.length > 0) {
        const lastX = width - padding;
        const lastY = padding + (height - 2 * padding) * (1 - (values[values.length - 1] - min) / range);
        
        ctx.shadowColor = '#00d4ff';
        ctx.shadowBlur = 10;
        ctx.fillStyle = '#00d4ff';
        ctx.beginPath();
        ctx.arc(lastX, lastY, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
    }
    
    // Draw axis labels
    ctx.fillStyle = '#5a6b82';
    ctx.font = '10px JetBrains Mono';
    ctx.fillText(formatNumber(max, 0), 2, padding + 10);
    ctx.fillText(formatNumber(min, 0), 2, height - padding - 2);
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Switch tab
 */
function switchTab(tabId) {
    state.activeTab = tabId;
    
    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('hidden', content.id !== `tab-${tabId}`);
    });
    
    // Re-render tab-specific content
    if (tabId === 'config') {
        renderConfig();
    } else if (tabId === 'predictions') {
        renderFullCSVViewer();
    }
}

// Make it globally accessible
window.switchTab = switchTab;

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN RENDER
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render all dashboard components
 */
function renderDashboard() {
    updateHeader();
    renderMetrics();
    renderSignalsSummary();
    renderLatestPrediction();
    renderSparkline();
    
    // Render CSV viewer only if on predictions tab
    if (state.activeTab === 'predictions') {
        renderFullCSVViewer();
    }
    
    // Render config only if on config tab
    if (state.activeTab === 'config') {
        renderConfig();
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Initialize dashboard
 */
async function initDashboard() {
    console.log('[Dashboard] Initializing PROFETA Dashboard...');
    
    // Start clock
    updateClock();
    setInterval(updateClock, 1000);
    
    // Initial data fetch
    await fetchAllData();
    renderDashboard();
    
    // Setup refresh interval
    state.refreshTimer = setInterval(async () => {
        await fetchAllData();
        renderDashboard();
    }, CONFIG.REFRESH_INTERVAL);
    
    // Setup resize handler for charts
    window.addEventListener('resize', debounce(() => {
        renderSparkline();
    }, 250));
    
    // Tab click handlers
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
    
    console.log('[Dashboard] Initialization complete.');
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXPORTS (for debugging)
// ═══════════════════════════════════════════════════════════════════════════════

window.PROFETA_DASHBOARD = {
    state,
    fetchAllData,
    renderDashboard,
    CONFIG
};
