// Background service worker for OpenFactVerification Chrome Extension
// Handles API communication and manages extension lifecycle
//
// FIX: MV3 service workers are terminated after ~30s of inactivity.
// Long fact-check requests (60-120s) cause the message channel to close
// before sendResponse() is called, resulting in the "channel closed" error.
// Solution: job-queue polling pattern — popup sends request, gets a jobId
// immediately, then polls every 3s via a cheap 'pollJob' message.

// ---- Job store (survives service-worker restarts via chrome.storage) ----
const JOB_STORE_KEY = 'fc_jobs';

async function saveJob(jobId, data) {
  const store = await getJobStore();
  store[jobId] = data;
  await chrome.storage.local.set({ [JOB_STORE_KEY]: store });
}

async function getJob(jobId) {
  const store = await getJobStore();
  return store[jobId] || null;
}

async function getJobStore() {
  const result = await chrome.storage.local.get(JOB_STORE_KEY);
  return result[JOB_STORE_KEY] || {};
}

async function cleanOldJobs() {
  const store = await getJobStore();
  const cutoff = Date.now() - 30 * 60 * 1000; // 30 min TTL
  for (const id of Object.keys(store)) {
    if (store[id].createdAt < cutoff) delete store[id];
  }
  await chrome.storage.local.set({ [JOB_STORE_KEY]: store });
}

class FactCheckAPI {
  constructor() {
    this.baseURL = 'http://127.0.0.1:2025';
    this.isConnected = false;
  }

  async init() {
    // Remove ALL storage config loading
    // Just test connection directly
    console.log('=== INIT CALLED, URL:', this.baseURL);
    await this.testConnection();
  }

  async getStoredConfig() {
    return new Promise((resolve) => {
      chrome.storage.sync.get(['apiConfig'], (result) => {
        resolve(result.apiConfig || {
          backendURL: 'http://localhost:2025',
          geminiApiKey: '',
          serperApiKey: ''
        });
      });
    });
  }

  async testConnection() {
    console.log('=== NEW VERSION RUNNING ===');
    console.log('URL:', this.baseURL);
    console.log('Testing connection to:', this.baseURL);
    try {
      console.log('Attempting fetch...');
      console.log('Fetch starting at:', Date.now());
      const response = await fetch(
        `${this.baseURL}/health`, {
        method: 'GET',
        mode: 'cors',
        cache: 'no-cache'
      });
      console.log('Response received:', response.status);
      console.log('Response ok:', response.ok);
      const data = await response.json();
      console.log('Response data:', data);
      this.isConnected = response.ok;
      return this.isConnected;
    } catch (error) {
      console.error('FETCH FAILED - Error name:', error.name);
      console.error('FETCH FAILED - Error message:', error.message);
      console.error('FETCH FAILED - Full error:', error);
      this.isConnected = false;
      return false;
    }
  }

  async factCheck(text) {
    if (!this.isConnected) {
      throw new Error('Backend service not available. Please ensure the fact-check server is running.');
    }

    // Use AbortController with 120-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
      const response = await fetch(`${this.baseURL}/api/factcheck`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text, type: 'text' }),
        signal: controller.signal,
        mode: 'cors',
        cache: 'no-cache'
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Backend API returned:', result);
      return result;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Request timed out after 120 seconds. The server is still processing — please try again.');
      }
      console.error('Fact-check API error:', error);
      throw error;
    }
  }

  async factCheckFile(fileData, fileType) {
    if (!this.isConnected) {
      throw new Error('Backend service not available. Please ensure the fact-check server is running.');
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
      // Validate file data
      if (!fileData || !fileData.base64Data) {
        throw new Error('Invalid file data received');
      }
      
      console.log('📋 File data validation:', {
        hasBase64Data: !!fileData.base64Data,
        base64Length: fileData.base64Data.length,
        fileName: fileData.name,
        fileType: fileData.type
      });
      
      // Convert base64 to blob
      const base64Data = fileData.base64Data;
      const base64Content = base64Data.split(',')[1]; // Remove data:image/png;base64, prefix
      
      if (!base64Content) {
        throw new Error('Invalid base64 data format');
      }
      
      // Convert base64 to binary
      const binaryString = atob(base64Content);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      // Create blob and file
      const blob = new Blob([bytes], { type: fileData.type });
      const file = new File([blob], fileData.name, { 
        type: fileData.type,
        lastModified: Date.now()
      });
      
      console.log('🔄 Reconstructed file:', {
        name: file.name,
        type: file.type,
        size: file.size,
        originalSize: fileData.size
      });
      
      // Validate reconstructed file
      if (file.size === 0) {
        throw new Error('File appears to be empty after reconstruction');
      }
      
      if (file.size !== fileData.size) {
        console.warn('⚠️ File size mismatch:', {
          original: fileData.size,
          reconstructed: file.size
        });
      }
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', fileType);

      console.log('📤 Sending file to backend:', {
        name: file.name,
        type: file.type,
        size: file.size,
        fileType: fileType
      });

      const response = await fetch(`${this.baseURL}/api/factcheck-file`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        mode: 'cors',
        cache: 'no-cache'
      });
      clearTimeout(timeoutId);

      console.log('📥 Backend response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Backend error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      console.log('✅ File fact-check successful:', result);
      return result;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('File request timed out after 120 seconds.');
      }
      console.error('File fact-check API error:', error);
      throw error;
    }
  }


}

// Initialize API instance
const factCheckAPI = new FactCheckAPI();

// Extension lifecycle
chrome.runtime.onStartup.addListener(() => {
  factCheckAPI.init();
});

chrome.runtime.onInstalled.addListener(() => {
  factCheckAPI.init();
  
  // Set default configuration
  chrome.storage.sync.set({
    apiConfig: {
      backendURL: 'http://localhost:2025',
      geminiApiKey: '',
      serperApiKey: ''
    }
  });
  
  // Create context menu for selected text
  chrome.contextMenus.create({
    id: "factcheck-selection",
    title: "Fact-check selected text",
    contexts: ["selection"]
  });
});

// ---- Job-queue polling message handler ----
// FIX: Instead of holding the message channel open for 60-120s (which causes
// "channel closed" errors in MV3 service workers), we:
//  1. Receive the request → create a job → immediately return { jobId }
//  2. Run the actual API call asynchronously and save the result in storage
//  3. Popup polls every 3s with { action: 'pollJob', jobId } until status === 'done'
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('🔍 Background received:', request.action);

  // ---- Lightweight synchronous actions (no long-polling needed) ----
  if (request.action === 'testConnection') {
    factCheckAPI.testConnection().then(connected => {
      sendResponse({ success: true, connected });
    }).catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (request.action === 'updateConfig') {
    chrome.storage.sync.set({ apiConfig: request.config }).then(() => {
      factCheckAPI.baseURL = request.config.backendURL;
      factCheckAPI.testConnection();
      sendResponse({ success: true });
    });
    return true;
  }

  if (request.action === 'getConfig') {
    factCheckAPI.getStoredConfig().then(config => {
      sendResponse({ success: true, config });
    });
    return true;
  }

  // ---- pollJob: popup asks if a queued job is finished ----
  if (request.action === 'pollJob') {
    getJob(request.jobId).then(job => {
      if (!job) {
        sendResponse({ status: 'not_found' });
      } else {
        sendResponse({ status: job.status, result: job.result, error: job.error });
      }
    });
    return true;
  }

  // ---- Long-running actions: enqueue and return jobId immediately ----
  if (request.action === 'factCheck' || request.action === 'factCheckFile') {
    const jobId = `job_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    // Save initial pending state immediately so pollJob can find it
    saveJob(jobId, { status: 'pending', createdAt: Date.now() }).then(() => {
      sendResponse({ success: true, jobId }); // Return jobId right away
    });

    // Run the actual work asynchronously (does NOT block sendResponse)
    (async () => {
      try {
        let result;
        if (request.action === 'factCheck') {
          console.log('🚀 Starting factCheck job', jobId);
          result = await factCheckAPI.factCheck(request.text);
        } else {
          console.log('🚀 Starting factCheckFile job', jobId);
          result = await factCheckAPI.factCheckFile(request.fileData, request.fileType);
        }
        await saveJob(jobId, { status: 'done', result, createdAt: Date.now() });
        console.log('✅ Job', jobId, 'completed');
      } catch (err) {
        console.error('❌ Job', jobId, 'failed:', err);
        await saveJob(jobId, { status: 'error', error: err.message, createdAt: Date.now() });
      }
      cleanOldJobs();
    })();

    return true; // Keep channel open just long enough for the first sendResponse
  }

  // Unknown action
  sendResponse({ success: false, error: 'Unknown action: ' + request.action });
  return false;
});

// Context menu click handler
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "factcheck-selection" && info.selectionText) {
    // Send message to content script to show fact-check modal
    chrome.tabs.sendMessage(tab.id, {
      action: "showFactCheckModal",
      text: info.selectionText
    });
  }
});

// Badge management
function updateBadge(tabId, factCheckResults) {
  if (factCheckResults && factCheckResults.summary) {
    const factuality = factCheckResults.summary.factuality;
    let badgeText = '';
    let badgeColor = '#666666';

    if (factuality >= 0.8) {
      badgeText = '✓';
      badgeColor = '#28a745';
    } else if (factuality >= 0.5) {
      badgeText = '?';
      badgeColor = '#ffc107';
    } else if (factuality > 0) {
      badgeText = '!';
      badgeColor = '#dc3545';
    }

    chrome.action.setBadgeText({ text: badgeText, tabId: tabId });
    chrome.action.setBadgeBackgroundColor({ color: badgeColor, tabId: tabId });
  }
}

// Clear badge when tab changes
chrome.tabs.onActivated.addListener((activeInfo) => {
  chrome.action.setBadgeText({ text: '', tabId: activeInfo.tabId });
});

// Open extension in a detached window to prevent closing on blur
chrome.action.onClicked.addListener((tab) => {
  chrome.windows.create({
    url: chrome.runtime.getURL('popup.html'),
    type: 'popup',
    width: 480,
    height: 600,
    focused: true
  });
});