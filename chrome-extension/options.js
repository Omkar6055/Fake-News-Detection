// OpenFactVerification Chrome Extension Options JavaScript
// Handles settings page functionality and configuration management

class FactCheckOptions {
  constructor() {
    this.defaultConfig = {
      backendURL: 'http://localhost:2025',
      geminiApiKey: '',
      serperApiKey: '',
      maxClaims: 10,
      timeoutSeconds: 120,
      enableAnalytics: false,
      enableAutoHighlight: true,
      showQuickCheckButton: true,
      customPrompt: '',
      enableDebugMode: false
    };
    
    this.currentConfig = { ...this.defaultConfig };
    this.init();
  }

  async init() {
    await this.loadSettings();
    this.setupEventListeners();
    this.populateForm();
    this.testConnection();
  }

  setupEventListeners() {
    // Save settings
    document.getElementById('saveSettings').addEventListener('click', () => this.saveSettings());
    
    // Reset settings
    document.getElementById('resetSettings').addEventListener('click', () => this.resetSettings());
    
    // Export/Import settings
    document.getElementById('exportSettings').addEventListener('click', () => this.exportSettings());
    document.getElementById('importSettings').addEventListener('click', () => this.importSettings());
    document.getElementById('importFile').addEventListener('change', (e) => this.handleImportFile(e));
    
    // Test connection
    document.getElementById('testConnectionBtn').addEventListener('click', () => this.testConnection());
    
    // Password visibility toggles
    document.querySelectorAll('.toggle-visibility').forEach(btn => {
      btn.addEventListener('click', (e) => this.togglePasswordVisibility(e));
    });
    
    // Copy code buttons
    document.querySelectorAll('.copy-code').forEach(btn => {
      btn.addEventListener('click', (e) => this.copyCode(e));
    });
    
    // Real-time validation
    document.getElementById('backendUrl').addEventListener('blur', () => this.validateUrl());
    document.getElementById('maxClaims').addEventListener('change', () => this.validateMaxClaims());
    document.getElementById('timeoutSeconds').addEventListener('change', () => this.validateTimeout());
    
    // Auto-save on change (with debounce)
    this.setupAutoSave();
  }

  setupAutoSave() {
    let saveTimeout;
    const inputs = document.querySelectorAll('.setting-input, .setting-textarea, .setting-checkbox');
    
    inputs.forEach(input => {
      input.addEventListener('change', () => {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
          this.saveSettings(true); // Silent save
        }, 1000);
      });
    });
  }

  async loadSettings() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'getConfig' });
      if (response.success) {
        this.currentConfig = { ...this.defaultConfig, ...response.config };
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
      this.showStatus('Failed to load settings', 'error');
    }
  }

  populateForm() {
    // Populate input fields
    document.getElementById('backendUrl').value = this.currentConfig.backendURL || '';
    document.getElementById('geminiApiKey').value = this.currentConfig.geminiApiKey || '';
    document.getElementById('serperApiKey').value = this.currentConfig.serperApiKey || '';
    document.getElementById('maxClaims').value = this.currentConfig.maxClaims || 10;
    document.getElementById('timeoutSeconds').value = this.currentConfig.timeoutSeconds || 120;
    document.getElementById('customPrompt').value = this.currentConfig.customPrompt || '';
    
    // Populate checkboxes
    document.getElementById('enableAnalytics').checked = this.currentConfig.enableAnalytics || false;
    document.getElementById('enableAutoHighlight').checked = this.currentConfig.enableAutoHighlight !== false;
    document.getElementById('showQuickCheckButton').checked = this.currentConfig.showQuickCheckButton !== false;
    document.getElementById('enableDebugMode').checked = this.currentConfig.enableDebugMode || false;
  }

  async saveSettings(silent = false) {
    try {
      // Collect form data
      const config = {
        backendURL: document.getElementById('backendUrl').value.trim() || this.defaultConfig.backendURL,
        geminiApiKey: document.getElementById('geminiApiKey').value.trim(),
        serperApiKey: document.getElementById('serperApiKey').value.trim(),
        maxClaims: parseInt(document.getElementById('maxClaims').value) || this.defaultConfig.maxClaims,
        timeoutSeconds: parseInt(document.getElementById('timeoutSeconds').value) || this.defaultConfig.timeoutSeconds,
        enableAnalytics: document.getElementById('enableAnalytics').checked,
        enableAutoHighlight: document.getElementById('enableAutoHighlight').checked,
        showQuickCheckButton: document.getElementById('showQuickCheckButton').checked,
        customPrompt: document.getElementById('customPrompt').value.trim(),
        enableDebugMode: document.getElementById('enableDebugMode').checked
      };

      // Validate required fields
      if (!config.geminiApiKey) {
        this.showStatus('Gemini API Key is required for the extension to work properly', 'error');
        return;
      }

      // Save to background script
      const response = await chrome.runtime.sendMessage({
        action: 'updateConfig',
        config: config
      });

      if (response.success) {
        this.currentConfig = config;
        if (!silent) {
          this.showStatus('Settings saved successfully!', 'success');
        }
      } else {
        throw new Error(response.error || 'Failed to save settings');
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      this.showStatus('Failed to save settings: ' + error.message, 'error');
    }
  }

  async resetSettings() {
    if (confirm('Are you sure you want to reset all settings to default values?')) {
      this.currentConfig = { ...this.defaultConfig };
      this.populateForm();
      await this.saveSettings();
      this.showStatus('Settings reset to defaults', 'info');
    }
  }

  exportSettings() {
    const configData = {
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      config: this.currentConfig
    };

    const blob = new Blob([JSON.stringify(configData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `openfactverification-config-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    this.showStatus('Configuration exported successfully', 'success');
  }

  importSettings() {
    document.getElementById('importFile').click();
  }

  async handleImportFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const text = await file.text();
      const importedData = JSON.parse(text);
      
      if (!importedData.config) {
        throw new Error('Invalid configuration file format');
      }

      // Merge with defaults to ensure all required fields exist
      this.currentConfig = { ...this.defaultConfig, ...importedData.config };
      this.populateForm();
      await this.saveSettings();
      
      this.showStatus('Configuration imported successfully', 'success');
    } catch (error) {
      console.error('Failed to import settings:', error);
      this.showStatus('Failed to import configuration: ' + error.message, 'error');
    } finally {
      // Clear the file input
      event.target.value = '';
    }
  }

  async testConnection() {
    const testBtn = document.getElementById('testConnectionBtn');
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    // Update UI for testing state
    testBtn.disabled = true;
    testBtn.textContent = 'Testing...';
    statusIndicator.className = 'status-indicator testing';
    statusText.textContent = 'Testing connection...';

    try {
      const response = await chrome.runtime.sendMessage({ action: 'testConnection' });
      
      if (response.success && response.connected) {
        statusIndicator.className = 'status-indicator connected';
        statusText.textContent = 'Connected successfully';
        this.showStatus('Backend connection successful!', 'success');
      } else {
        statusIndicator.className = 'status-indicator disconnected';
        statusText.textContent = 'Connection failed';
        this.showStatus('Cannot connect to backend server. Make sure it\'s running on the configured URL.', 'error');
      }
    } catch (error) {
      statusIndicator.className = 'status-indicator disconnected';
      statusText.textContent = 'Connection error';
      this.showStatus('Connection test failed: ' + error.message, 'error');
    } finally {
      testBtn.disabled = false;
      testBtn.textContent = 'Test Connection';
    }
  }

  togglePasswordVisibility(event) {
    const button = event.target;
    const targetId = button.dataset.target;
    const input = document.getElementById(targetId);
    
    if (input.type === 'password') {
      input.type = 'text';
      button.textContent = '🙈';
    } else {
      input.type = 'password';
      button.textContent = '👁️';
    }
  }

  async copyCode(event) {
    const button = event.target;
    const code = button.dataset.copy;
    
    try {
      await navigator.clipboard.writeText(code);
      const originalText = button.textContent;
      button.textContent = '✓';
      setTimeout(() => {
        button.textContent = originalText;
      }, 2000);
    } catch (error) {
      console.error('Failed to copy code:', error);
    }
  }

  validateUrl() {
    const urlInput = document.getElementById('backendUrl');
    const url = urlInput.value.trim();
    
    if (url && !this.isValidUrl(url)) {
      urlInput.style.borderColor = '#dc3545';
      this.showStatus('Please enter a valid URL (e.g., http://localhost:2025)', 'error');
      return false;
    } else {
      urlInput.style.borderColor = '#e9ecef';
      return true;
    }
  }

  validateMaxClaims() {
    const input = document.getElementById('maxClaims');
    const value = parseInt(input.value);
    
    if (value < 1 || value > 50) {
      input.style.borderColor = '#dc3545';
      this.showStatus('Maximum claims must be between 1 and 50', 'error');
      return false;
    } else {
      input.style.borderColor = '#e9ecef';
      return true;
    }
  }

  validateTimeout() {
    const input = document.getElementById('timeoutSeconds');
    const value = parseInt(input.value);
    
    if (value < 30 || value > 300) {
      input.style.borderColor = '#dc3545';
      this.showStatus('Timeout must be between 30 and 300 seconds', 'error');
      return false;
    } else {
      input.style.borderColor = '#e9ecef';
      return true;
    }
  }

  isValidUrl(string) {
    try {
      const url = new URL(string);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (_) {
      return false;
    }
  }

  showStatus(message, type) {
    const statusMessage = document.getElementById('statusMessage');
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.style.display = 'block';

    // Auto-hide after 5 seconds
    setTimeout(() => {
      statusMessage.style.display = 'none';
    }, 5000);
  }
}

// Initialize options page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new FactCheckOptions();
});