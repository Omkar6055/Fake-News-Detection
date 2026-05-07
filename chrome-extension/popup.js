// OpenFactVerification Chrome Extension Popup JavaScript
// Matches the main Python application UI design

class FactCheckPopup {
  constructor() {
    this.currentResults = null;
    this.isProcessing = false;
    this.elapsedTimer = null;
    
    this.init();
  }

  async init() {
    this.setupEventListeners();
    this.checkConnectionStatus();
    this.loadPastedTextIfAvailable();
  }

  setupEventListeners() {
    // Text input actions
    document.getElementById('factCheckTextButton').addEventListener('click', () => this.factCheckText());

    // Results actions
    document.getElementById('copyResultsButton').addEventListener('click', () => this.copyResults());
    document.getElementById('clearResultsButton').addEventListener('click', () => this.clearResults());
    document.getElementById('retryButton').addEventListener('click', () => this.retryLastAction());

    // Settings and navigation
    document.getElementById('settingsLink').addEventListener('click', () => this.openSettings());
    document.getElementById('helpLink').addEventListener('click', () => this.showHelp());

    // Auto-resize textarea
    const textInput = document.getElementById('textInput');
    textInput.addEventListener('input', () => this.autoResizeTextarea(textInput));
  }

  async checkConnectionStatus() {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');

    try {
      // Read backend URL from storage (supports both local and production)
      const stored = await new Promise(resolve =>
        chrome.storage.sync.get(['apiConfig'], r => resolve(r.apiConfig || {}))
      );
      const backendURL = (stored.backendURL || 'http://localhost:2025').replace(/\/$/, '');

      const response = await fetch(`${backendURL}/health`);
      const data = await response.json();
      
      if (data.status === "ok") {
        statusDot.className = 'status-dot connected';
        statusText.textContent = '🟢 Connected';
      } else {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = '🔴 Disconnected';
      }
    } catch (error) {
      statusDot.className = 'status-dot disconnected';
      statusText.textContent = '🔴 Disconnected';
    }
  }

  async loadPastedTextIfAvailable() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        function: () => window.getSelection().toString().trim()
      });
      
      if (results[0]?.result) {
        document.getElementById('textInput').value = results[0].result;
        this.autoResizeTextarea(document.getElementById('textInput'));
      }
    } catch (error) {
      // Ignore errors - user might be on a restricted page
    }
  }

  autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  }

  // --- Polling helper ---
  // Polls background every 3s until job is done, errors, or times out.
  async pollForResult(jobId, timeoutMs = 130000) {
    const start = Date.now();
    const POLL_INTERVAL = 3000;
    const PROGRESS_MSGS = [
      'Decomposing claims…',
      'Checking claim worthiness…',
      'Generating search queries…',
      'Retrieving web evidence…',
      'Verifying claims against sources…',
      'Calculating factuality score…',
      'Almost done…'
    ];
    let msgIdx = 0;

    while (Date.now() - start < timeoutMs) {
      await new Promise(r => setTimeout(r, POLL_INTERVAL));

      // Cycle through progress messages
      const msgEl = document.getElementById('loadingMessage');
      if (msgEl) {
        msgIdx = (msgIdx + 1) % PROGRESS_MSGS.length;
        msgEl.textContent = PROGRESS_MSGS[msgIdx];
      }

      let pollResp;
      try {
        pollResp = await chrome.runtime.sendMessage({ action: 'pollJob', jobId });
      } catch (e) {
        console.warn('Poll error:', e);
        continue; // service worker may have briefly restarted
      }

      if (!pollResp || pollResp.status === 'not_found') continue;

      if (pollResp.status === 'done') {
        // DEBUG: log the raw result from backend
        console.log('RAW RESULT FROM BACKEND:', JSON.stringify(pollResp.result));
        return { success: true, data: pollResp.result };
      }

      if (pollResp.status === 'error') {
        return { success: false, error: pollResp.error };
      }
      // still 'pending' — keep polling
    }
    return { success: false, error: 'Request timed out after 2 minutes. The backend may still be processing — please try again with shorter text.' };
  }

  async factCheckText() {
    const text = document.getElementById('textInput').value.trim();
    if (!text) {
      this.showError('Please enter text to fact-check.');
      return;
    }

    this.showLoading('Sending request…');
    this.lastAction = () => this.factCheckText();

    try {
      // Step 1: send request — get jobId immediately (no waiting)
      const initResp = await chrome.runtime.sendMessage({
        action: 'factCheck',
        text: text
      });

      if (!initResp || !initResp.success || !initResp.jobId) {
        this.showError(initResp?.error || 'Failed to queue fact-check request');
        return;
      }

      // Step 2: poll until done
      const response = await this.pollForResult(initResp.jobId);

      if (response && response.success) {
        const actualData = response.data?.data || response.data;
        // DEBUG: log exactly what the frontend will render
        console.log('ACTUAL DATA TO DISPLAY:', JSON.stringify(actualData?.summary));
        console.log('CLAIM COUNT:', actualData?.claim_detail?.length, 'claims');
        this.displayResults(actualData);
      } else {
        this.showError(response?.error || 'Failed to fact-check text');
      }
    } catch (error) {
      console.error('Error in factCheckText:', error);
      this.showError('Error during fact-checking: ' + error.message);
    }
  }

  showLoading(initialMessage = 'Connecting to fact-check server…') {
    this.isProcessing = true;
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('loadingState').style.display = 'block';
    document.getElementById('resultsDisplay').style.display = 'none';
    document.getElementById('errorState').style.display = 'none';

    // Update the loading message element if it exists
    const msgEl = document.getElementById('loadingMessage');
    if (msgEl) msgEl.textContent = initialMessage;

    this.startElapsedTimer();
  }

  startElapsedTimer() {
    let seconds = 0;
    const elapsedTimeElement = document.getElementById('elapsedTime');
    
    this.elapsedTimer = setInterval(() => {
      seconds++;
      elapsedTimeElement.textContent = seconds;
    }, 1000);
  }

  stopElapsedTimer() {
    if (this.elapsedTimer) {
      clearInterval(this.elapsedTimer);
      this.elapsedTimer = null;
    }
  }

  displayResults(results) {
    this.isProcessing = false;
    this.currentResults = results;
    this.stopElapsedTimer();

    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('resultsDisplay').style.display = 'block';
    document.getElementById('errorState').style.display = 'none';

    if (!results || typeof results !== 'object') {
      this.showError('Invalid results format received');
      return;
    }

    // Calculate actual metrics from claim data for consistency
    const claims = results.claim_detail || [];
    let actualSupportedCount = 0;
    let actualRefutedCount = 0;
    let actualControversialCount = 0;
    
    claims.forEach(claim => {
      if (claim && typeof claim.factuality !== 'undefined') {
        const category = this.getFactualityCategory(claim.factuality);
        if (category === 'supported') actualSupportedCount++;
        else if (category === 'refuted') actualRefutedCount++;
        else if (category === 'controversial') actualControversialCount++;
      }
    });

    // Update metrics bar with actual calculated values
    const summary = results.summary || {};
    const factuality = summary.factuality || 0;
    
    document.getElementById('overallCredibility').textContent = (factuality * 100).toFixed(1) + '%';
    document.getElementById('totalClaims').textContent = claims.length;
    document.getElementById('supportedClaims').textContent = actualSupportedCount;
    document.getElementById('refutedClaims').textContent = actualRefutedCount;
    document.getElementById('controversialClaims').textContent = actualControversialCount;

    // Display claims
    this.renderClaims(claims);
  }

  renderClaims(claims) {
    const claimsList = document.getElementById('claimsList');
    
    if (!claims || !Array.isArray(claims) || claims.length === 0) {
      claimsList.innerHTML = '<p style="text-align: center; color: #6c757d; font-size: 13px;">No claims found to verify.</p>';
      return;
    }

    claimsList.innerHTML = claims.map((claim, index) => {
      if (!claim) return '';
      
      const category = this.getFactualityCategory(claim.factuality);
      const statusText = this.getFactualityText(claim.factuality);
      const evidenceCount = (claim.evidences && Array.isArray(claim.evidences)) ? claim.evidences.length : 0;
      const claimText = claim.claim || 'No claim text available';
      
      return `
        <div class="claim-item ${category}">
          <div class="claim-status-badge">
            Claim ${index + 1}: ${statusText}
          </div>
          <div class="claim-text">${claimText}</div>
          <div class="claim-evidence-count">${evidenceCount} evidence(s) found</div>
        </div>
      `;
    }).filter(html => html !== '').join('');
  }

  getFactualityCategory(factuality) {
    if (typeof factuality === 'string') return 'not-checked';
    if (factuality >= 0.8) return 'supported';
    if (factuality >= 0.5) return 'controversial';
    return 'refuted';
  }

  getFactualityText(factuality) {
    if (typeof factuality === 'string') return 'Not Checked';
    if (factuality >= 0.8) return 'SUPPORTED';
    if (factuality >= 0.5) return 'CONTROVERSIAL';
    return 'REFUTED';
  }

  showError(message) {
    this.isProcessing = false;
    this.stopElapsedTimer();
    
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('resultsDisplay').style.display = 'none';
    document.getElementById('errorState').style.display = 'block';
    document.getElementById('errorMessage').textContent = message;
  }

  async copyResults() {
    if (!this.currentResults) return;

    const summary = this.currentResults.summary || {};
    const claims = this.currentResults.claim_detail || [];
    
    let report = `OpenFactVerification Report\n`;
    report += `================================\n\n`;
    report += `Overall Factuality: ${(summary.factuality * 100).toFixed(1)}%\n`;
    report += `Total Claims: ${claims.length}\n`;
    report += `Supported: ${this.currentResults.summary?.num_supported_claims || 0}\n`;
    report += `Refuted: ${this.currentResults.summary?.num_refuted_claims || 0}\n`;
    report += `Controversial: ${this.currentResults.summary?.num_controversial_claims || 0}\n\n`;
    
    if (claims.length > 0) {
      report += `Claims Analysis:\n`;
      report += `----------------\n\n`;
      
      claims.forEach((claim, index) => {
        report += `${index + 1}. "${claim.claim}"\n`;
        report += `   Status: ${this.getFactualityText(claim.factuality)}\n`;
        if (claim.evidences && claim.evidences.length > 0) {
          report += `   Evidence Found: ${claim.evidences.length} sources\n`;
        }
        report += `\n`;
      });
    }

    try {
      await navigator.clipboard.writeText(report);
      const button = document.getElementById('copyResultsButton');
      const originalText = button.textContent;
      button.textContent = '✓ Copied!';
      setTimeout(() => {
        button.textContent = originalText;
      }, 2000);
    } catch (error) {
      console.error('Failed to copy results:', error);
    }
  }

  clearResults() {
    this.currentResults = null;
    this.stopElapsedTimer();
    document.getElementById('resultsSection').style.display = 'none';
    
    // Reset metrics
    document.getElementById('overallCredibility').textContent = '--';
    document.getElementById('totalClaims').textContent = '--';
    document.getElementById('supportedClaims').textContent = '--';
    document.getElementById('refutedClaims').textContent = '--';
    document.getElementById('controversialClaims').textContent = '--';
    
    // Clear inputs
    document.getElementById('textInput').value = '';
    this.clearFile();
  }

  retryLastAction() {
    if (this.lastAction) {
      this.lastAction();
    }
  }

  openSettings() {
    chrome.runtime.openOptionsPage();
  }

  showHelp() {
    const helpWindow = window.open('', '_blank', 'width=600,height=500');
    helpWindow.document.write(`
      <html>
        <head><title>OpenFactVerification Help</title></head>
        <body style="font-family: system-ui; padding: 20px; line-height: 1.6;">
          <h2>How to Use OpenFactVerification</h2>
          
          <h3>Getting Started</h3>
          <p>1. Make sure the backend server is running (localhost:2025)</p>
          <p>2. Configure your API keys in Settings</p>
          
          <h3>Text Fact-Checking</h3>
          <p>• Enter or paste text in the Text tab</p>
          <p>• Click "Check Facts" to analyze</p>
          
          <h3>File Analysis</h3>
          <p>• Upload images or videos in the Media tab</p>
          <p>• Supports common image and video formats</p>
          
          <h3>Understanding Results</h3>
          <p>• <span style="color: #28a745;">Green</span>: Supported claims</p>
          <p>• <span style="color: #dc3545;">Red</span>: Refuted claims</p>
          <p>• <span style="color: #ffc107;">Yellow</span>: Controversial claims</p>
          
          <h3>Troubleshooting</h3>
          <p>• Ensure backend server is running on localhost:2025</p>
          <p>• Check your API keys in Settings</p>
          <p>• Some pages may be restricted for analysis</p>
        </body>
      </html>
    `);
  }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new FactCheckPopup();
});