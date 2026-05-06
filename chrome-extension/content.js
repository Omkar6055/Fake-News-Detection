// Content script for OpenFactVerification Chrome Extension
// Handles text selection, page interaction, fact-check modal display, and screen capture

class FactCheckContentScript {
  constructor() {
    this.selectedText = '';
    this.factCheckModal = null;
    this.isModalOpen = false;
    this.highlightedClaims = [];
    
    // Screen capture properties
    this.isSelecting = false;
    this.isDrawing = false;
    this.selectionOverlay = null;
    this.startX = 0;
    this.startY = 0;
    this.endX = 0;
    this.endY = 0;
    this.currentSelection = null;
    
    this.init();
  }

  init() {
    this.setupTextSelection();
    this.setupMessageListener();
    this.createFactCheckModal();
  }

  setupTextSelection() {
    // Add double-click handler for quick fact-checking
    document.addEventListener('dblclick', (event) => {
      const selection = window.getSelection();
      const selectedText = selection.toString().trim();
      
      if (selectedText.length > 10) { // Only fact-check substantial text
        this.selectedText = selectedText;
        this.showQuickFactCheckButton(event.clientX, event.clientY);
      }
    });

    // Handle text selection changes
    document.addEventListener('selectionchange', () => {
      const selection = window.getSelection();
      this.selectedText = selection.toString().trim();
      
      // Hide quick button if no selection
      if (!this.selectedText) {
        this.hideQuickFactCheckButton();
      }
    });

    // Hide quick button on click outside
    document.addEventListener('click', (event) => {
      if (!event.target.closest('.factcheck-quick-button')) {
        this.hideQuickFactCheckButton();
      }
    });
  }

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      switch (request.action) {
        case 'showFactCheckModal':
          this.selectedText = request.text;
          this.showFactCheckModal();
          sendResponse({ success: true });
          break;
          
        case 'highlightClaims':
          this.highlightClaimsOnPage(request.claims);
          sendResponse({ success: true });
          break;
          
        case 'clearHighlights':
          this.clearHighlights();
          sendResponse({ success: true });
          break;

        case 'startScreenSelection':
          console.log('Content script: Starting screen selection');
          this.startScreenSelection();
          sendResponse({ success: true });
          break;
      }
    });
  }

  showQuickFactCheckButton(x, y) {
    // Remove existing button
    this.hideQuickFactCheckButton();

    // Create quick fact-check button
    const button = document.createElement('div');
    button.className = 'factcheck-quick-button';
    button.innerHTML = `
      <div class="factcheck-button-content">
        <span class="factcheck-icon">📋</span>
        <span class="factcheck-text">Fact Check</span>
      </div>
    `;

    button.style.cssText = `
      position: fixed;
      left: ${x + 10}px;
      top: ${y - 40}px;
      z-index: 10000;
      background: #007bff;
      color: white;
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      box-shadow: 0 2px 10px rgba(0,0,0,0.2);
      animation: factcheck-fade-in 0.2s ease-out;
    `;

    button.addEventListener('click', () => {
      this.showFactCheckModal();
      this.hideQuickFactCheckButton();
    });

    document.body.appendChild(button);

    // Auto-hide after 5 seconds
    setTimeout(() => {
      this.hideQuickFactCheckButton();
    }, 5000);
  }

  hideQuickFactCheckButton() {
    const existingButton = document.querySelector('.factcheck-quick-button');
    if (existingButton) {
      existingButton.remove();
    }
  }

  createFactCheckModal() {
    // Create modal container
    const modal = document.createElement('div');
    modal.className = 'factcheck-modal-overlay';
    modal.innerHTML = `
      <div class="factcheck-modal">
        <div class="factcheck-modal-header">
          <h3>Fact Check Results</h3>
          <button class="factcheck-modal-close">&times;</button>
        </div>
        <div class="factcheck-modal-content">
          <div class="factcheck-loading">
            <div class="factcheck-spinner"></div>
            <p>Analyzing claims and retrieving evidence...</p>
          </div>
          <div class="factcheck-results" style="display: none;"></div>
          <div class="factcheck-error" style="display: none;"></div>
        </div>
      </div>
    `;

    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      z-index: 10000;
      display: none;
      align-items: center;
      justify-content: center;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    `;

    // Add event listeners
    modal.querySelector('.factcheck-modal-close').addEventListener('click', () => {
      this.hideFactCheckModal();
    });

    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        this.hideFactCheckModal();
      }
    });

    document.body.appendChild(modal);
    this.factCheckModal = modal;
  }

  // Polling helper for content script (mirrors popup.js)
  async pollForResult(jobId, timeoutMs = 130000) {
    const start = Date.now();
    const POLL_INTERVAL = 3000;
    const PROGRESS_MSGS = [
      'Decomposing claims…',
      'Checking worthiness…',
      'Generating queries…',
      'Retrieving evidence…',
      'Verifying claims…',
      'Almost done…'
    ];
    let msgIdx = 0;
    const loadingP = this.factCheckModal?.querySelector('.factcheck-loading p');

    while (Date.now() - start < timeoutMs) {
      await new Promise(r => setTimeout(r, POLL_INTERVAL));
      if (loadingP) {
        loadingP.textContent = PROGRESS_MSGS[msgIdx % PROGRESS_MSGS.length];
        msgIdx++;
      }

      let pollResp;
      try {
        pollResp = await chrome.runtime.sendMessage({ action: 'pollJob', jobId });
      } catch (e) { continue; }

      if (!pollResp || pollResp.status === 'not_found') continue;
      if (pollResp.status === 'done') return { success: true, data: pollResp.result };
      if (pollResp.status === 'error') return { success: false, error: pollResp.error };
    }
    return { success: false, error: 'Timed out waiting for fact-check result.' };
  }

  async showFactCheckModal() {
    if (!this.selectedText) return;

    this.factCheckModal.style.display = 'flex';
    this.isModalOpen = true;

    // Show loading state
    this.factCheckModal.querySelector('.factcheck-loading').style.display = 'block';
    this.factCheckModal.querySelector('.factcheck-results').style.display = 'none';
    this.factCheckModal.querySelector('.factcheck-error').style.display = 'none';

    try {
      // Step 1: queue the job, get jobId immediately
      const initResp = await chrome.runtime.sendMessage({
        action: 'factCheck',
        text: this.selectedText
      });

      if (!initResp || !initResp.success || !initResp.jobId) {
        this.displayError(initResp?.error || 'Failed to start fact-check');
        return;
      }

      // Step 2: poll until done
      const response = await this.pollForResult(initResp.jobId);

      if (response.success) {
        const data = response.data?.data || response.data;
        this.displayResults(data);
      } else {
        this.displayError(response.error);
      }
    } catch (error) {
      this.displayError(error.message);
    }
  }

  hideFactCheckModal() {
    if (this.factCheckModal) {
      this.factCheckModal.style.display = 'none';
      this.isModalOpen = false;
    }
  }

  displayResults(results) {
    const loadingElement = this.factCheckModal.querySelector('.factcheck-loading');
    const resultsElement = this.factCheckModal.querySelector('.factcheck-results');
    const errorElement = this.factCheckModal.querySelector('.factcheck-error');

    loadingElement.style.display = 'none';
    errorElement.style.display = 'none';
    resultsElement.style.display = 'block';

    // Generate results HTML
    const summary = results.summary || {};
    const claims = results.claim_detail || [];

    resultsElement.innerHTML = `
      <div class="factcheck-summary">
        <div class="factcheck-score">
          <div class="score-value">${(summary.factuality * 100).toFixed(1)}%</div>
          <div class="score-label">Factuality Score</div>
        </div>
        <div class="factcheck-stats">
          <div class="stat-item">
            <span class="stat-value">${summary.num_claims || 0}</span>
            <span class="stat-label">Claims</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">${summary.num_supported_claims || 0}</span>
            <span class="stat-label">Supported</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">${summary.num_refuted_claims || 0}</span>
            <span class="stat-label">Refuted</span>
          </div>
        </div>
      </div>
      <div class="factcheck-claims">
        ${claims.map(claim => this.renderClaim(claim)).join('')}
      </div>
    `;
  }

  displayResultsInModal(results) {
    // Show the fact check modal with results (for screen capture)
    this.factCheckModal.style.display = 'flex';
    this.isModalOpen = true;
    this.displayResults(results);
  }

  renderClaim(claim) {
    const factualityClass = this.getFactualityClass(claim.factuality);
    const factualityText = this.getFactualityText(claim.factuality);

    return `
      <div class="factcheck-claim ${factualityClass}">
        <div class="claim-header">
          <span class="claim-status">${factualityText}</span>
          <span class="claim-text">"${claim.claim}"</span>
        </div>
        <div class="claim-details">
          <div class="claim-reason">
            <strong>Check-worthy:</strong> ${claim.checkworthy_reason}
          </div>
          ${claim.evidences && claim.evidences.length > 0 ? `
            <div class="claim-evidences">
              <strong>Evidence:</strong>
              <ul>
                ${claim.evidences.slice(0, 3).map(evidence => `
                  <li>
                    <a href="${evidence.url}" target="_blank">${evidence.title}</a>
                    <span class="evidence-relationship ${evidence.relationship.toLowerCase()}">${evidence.relationship}</span>
                  </li>
                `).join('')}
              </ul>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  getFactualityClass(factuality) {
    if (typeof factuality === 'string') return 'not-checked';
    if (factuality >= 0.8) return 'supported';
    if (factuality >= 0.5) return 'controversial';
    return 'refuted';
  }

  getFactualityText(factuality) {
    if (typeof factuality === 'string') return 'Not Checked';
    if (factuality >= 0.8) return 'Supported';
    if (factuality >= 0.5) return 'Controversial';
    return 'Refuted';
  }

  displayError(error) {
    const loadingElement = this.factCheckModal.querySelector('.factcheck-loading');
    const resultsElement = this.factCheckModal.querySelector('.factcheck-results');
    const errorElement = this.factCheckModal.querySelector('.factcheck-error');

    loadingElement.style.display = 'none';
    resultsElement.style.display = 'none';
    errorElement.style.display = 'block';

    errorElement.innerHTML = `
      <div class="error-content">
        <h4>Error</h4>
        <p>${error}</p>
        <p class="error-suggestion">
          Make sure the OpenFactVerification backend server is running on localhost:2024
        </p>
      </div>
    `;
  }

  highlightClaimsOnPage(claims) {
    // Clear existing highlights
    this.clearHighlights();

    claims.forEach((claim, index) => {
      const text = claim.claim;
      const factualityClass = this.getFactualityClass(claim.factuality);
      
      // Use TreeWalker to find text nodes
      const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        null,
        false
      );

      const textNodes = [];
      let node;
      while (node = walker.nextNode()) {
        textNodes.push(node);
      }

      // Find and highlight matching text
      textNodes.forEach(textNode => {
        const content = textNode.textContent;
        if (content.includes(text)) {
          const parent = textNode.parentNode;
          const highlighted = document.createElement('span');
          highlighted.className = `factcheck-highlight ${factualityClass}`;
          highlighted.innerHTML = content.replace(text, `<mark class="factcheck-claim-highlight">${text}</mark>`);
          parent.replaceChild(highlighted, textNode);
          this.highlightedClaims.push(highlighted);
        }
      });
    });
  }

  clearHighlights() {
    this.highlightedClaims.forEach(highlight => {
      const parent = highlight.parentNode;
      const textNode = document.createTextNode(highlight.textContent);
      parent.replaceChild(textNode, highlight);
    });
    this.highlightedClaims = [];
  }

  // Screen Capture Methods
  async startScreenSelection() {
    console.log('startScreenSelection called in content script');
    if (this.isSelecting) {
      console.log('Already selecting, returning');
      return;
    }

    try {
      // Create selection overlay first
      console.log('Creating selection overlay');
      this.createSelectionOverlay();
      this.isSelecting = true;
      
      // Show instructions
      this.showScreenInstructions();
      
    } catch (error) {
      console.error('Error starting screen selection:', error);
      this.showScreenError('Failed to start screen capture: ' + error.message);
    }
  }

  createSelectionOverlay() {
    // Remove existing overlay if any
    this.removeSelectionOverlay();

    // Create overlay container
    const overlay = document.createElement('div');
    overlay.id = 'factcheck-screen-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.3);
      z-index: 999999;
      cursor: crosshair;
      user-select: none;
    `;

    // Create selection rectangle
    const selectionRect = document.createElement('div');
    selectionRect.id = 'factcheck-selection-rect';
    selectionRect.style.cssText = `
      position: absolute;
      border: 2px dashed #007bff;
      background: rgba(0, 123, 255, 0.1);
      display: none;
      pointer-events: none;
    `;

    overlay.appendChild(selectionRect);
    document.body.appendChild(overlay);
    this.selectionOverlay = overlay;

    // Add event listeners
    overlay.addEventListener('mousedown', (e) => this.onScreenMouseDown(e));
    overlay.addEventListener('mousemove', (e) => this.onScreenMouseMove(e));
    overlay.addEventListener('mouseup', (e) => this.onScreenMouseUp(e));
    overlay.addEventListener('keydown', (e) => this.onScreenKeyDown(e));
    
    // Make overlay focusable for keyboard events
    overlay.tabIndex = -1;
    overlay.focus();
  }

  onScreenMouseDown(e) {
    if (!this.isSelecting) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    this.isDrawing = true;
    this.startX = e.clientX;
    this.startY = e.clientY;
    this.endX = e.clientX;
    this.endY = e.clientY;
    
    const selectionRect = document.getElementById('factcheck-selection-rect');
    if (selectionRect) {
      selectionRect.style.display = 'block';
      selectionRect.style.left = this.startX + 'px';
      selectionRect.style.top = this.startY + 'px';
      selectionRect.style.width = '0px';
      selectionRect.style.height = '0px';
    }
  }

  onScreenMouseMove(e) {
    if (!this.isSelecting || !this.isDrawing) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    this.endX = e.clientX;
    this.endY = e.clientY;
    
    const selectionRect = document.getElementById('factcheck-selection-rect');
    if (selectionRect && selectionRect.style.display === 'block') {
      const left = Math.min(this.startX, this.endX);
      const top = Math.min(this.startY, this.endY);
      const width = Math.abs(this.endX - this.startX);
      const height = Math.abs(this.endY - this.startY);
      
      selectionRect.style.left = left + 'px';
      selectionRect.style.top = top + 'px';
      selectionRect.style.width = width + 'px';
      selectionRect.style.height = height + 'px';
    }
  }

  async onScreenMouseUp(e) {
    if (!this.isSelecting || !this.isDrawing) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    this.isDrawing = false; // Stop drawing/tracking
    
    const width = Math.abs(this.endX - this.startX);
    const height = Math.abs(this.endY - this.startY);
    
    // Minimum selection size
    if (width < 10 || height < 10) {
      this.showScreenError('Please select a larger area (minimum 10x10 pixels)');
      return;
    }

    // Calculate selection bounds
    const left = Math.min(this.startX, this.endX);
    const top = Math.min(this.startY, this.endY);
    
    this.currentSelection = {
      x: left,
      y: top,
      width: width,
      height: height
    };

    console.log('Selection completed:', this.currentSelection);
    
    // Show confirmation dialog
    this.showScreenConfirmationDialog();
  }

  onScreenKeyDown(e) {
    if (e.key === 'Escape') {
      this.cancelScreenSelection();
    }
  }

  showScreenInstructions() {
    const instructions = document.createElement('div');
    instructions.id = 'factcheck-instructions';
    instructions.style.cssText = `
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: #007bff;
      color: white;
      padding: 12px 20px;
      border-radius: 6px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      z-index: 1000000;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      text-align: center;
    `;
    instructions.innerHTML = `
      📷 <strong>Click and drag</strong> to select an area • <strong>Release</strong> to confirm • Press <strong>ESC</strong> to cancel
    `;
    
    document.body.appendChild(instructions);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
      if (instructions.parentNode) {
        instructions.remove();
      }
    }, 5000);
  }

  showScreenConfirmationDialog() {
    const dialog = document.createElement('div');
    dialog.id = 'factcheck-confirmation';
    dialog.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      z-index: 1000001;
      text-align: center;
      min-width: 300px;
    `;
    
    dialog.innerHTML = `
      <h3 style="margin: 0 0 12px 0; color: #333;">Capture Selected Area?</h3>
      <p style="margin: 0 0 20px 0; color: #666; font-size: 14px;">
        This will capture the selected screen area and analyze it for factual claims.
      </p>
      <div style="display: flex; gap: 12px; justify-content: center;">
        <button id="factcheck-capture-btn" style="
          background: #007bff;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        ">📷 Capture & Analyze</button>
        <button id="factcheck-cancel-btn" style="
          background: #6c757d;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        ">Cancel</button>
      </div>
    `;
    
    document.body.appendChild(dialog);
    
    // Add event listeners
    document.getElementById('factcheck-capture-btn').addEventListener('click', () => {
      dialog.remove();
      this.captureScreenSelection();
    });
    
    document.getElementById('factcheck-cancel-btn').addEventListener('click', () => {
      dialog.remove();
      this.cancelScreenSelection();
    });
  }

  async captureScreenSelection() {
    try {
      this.showScreenProcessingIndicator();
      
      console.log('Starting screenshot capture process...');
      console.log('Selection area:', this.currentSelection);
      
      // Request screen capture permission and get stream
      const response = await chrome.runtime.sendMessage({ action: 'captureScreen' });
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to get screen capture permission');
      }
      
      console.log('Got screen capture permission, creating screenshot...');
      
      // Use the screen capture API to get actual screenshot
      const canvas = await this.captureScreenshotWithAPI(response.streamId);
      
      // Convert canvas to base64 image data
      const imageData = canvas.toDataURL('image/png');
      
      console.log('Screenshot captured, sending for processing...');
      
      // Send to background script for processing
      const processResponse = await chrome.runtime.sendMessage({
        action: 'processScreenshot',
        imageData: imageData
      });
      
      this.removeSelectionOverlay();
      
      if (processResponse.success) {
        this.displayResultsInModal(processResponse.data);
      } else {
        this.showScreenError(processResponse.error || 'Failed to process screenshot');
      }
      
    } catch (error) {
      console.error('Error capturing selection:', error);
      this.showScreenError('Failed to capture screen area: ' + error.message);
      this.removeSelectionOverlay();
    }
  }

  async captureScreenshotWithAPI(streamId) {
    return new Promise((resolve, reject) => {
      console.log('Creating video element for screen capture...');
      
      // Create video element to capture the screen
      const video = document.createElement('video');
      video.style.position = 'absolute';
      video.style.top = '-10000px';
      video.style.left = '-10000px';
      video.style.width = '1px';
      video.style.height = '1px';
      video.style.opacity = '0';
      document.body.appendChild(video);
      
      // Get media stream using the stream ID
      navigator.mediaDevices.getUserMedia({
        video: {
          mandatory: {
            chromeMediaSource: 'desktop',
            chromeMediaSourceId: streamId,
            maxWidth: screen.width,
            maxHeight: screen.height
          }
        }
      }).then(stream => {
        console.log('Got media stream, setting up video...');
        video.srcObject = stream;
        video.play();
        
        video.addEventListener('loadedmetadata', () => {
          console.log('Video metadata loaded, dimensions:', video.videoWidth, 'x', video.videoHeight);
          
          // Wait for video to be ready
          setTimeout(() => {
            try {
              // Create canvas for the selected area only
              const canvas = document.createElement('canvas');
              const ctx = canvas.getContext('2d');
              
              canvas.width = this.currentSelection.width;
              canvas.height = this.currentSelection.height;
              
              console.log('Canvas created:', canvas.width, 'x', canvas.height);
              console.log('Capturing from video area:', {
                sourceX: this.currentSelection.x,
                sourceY: this.currentSelection.y,
                sourceWidth: this.currentSelection.width,
                sourceHeight: this.currentSelection.height
              });
              
              // Calculate scale factor to match video dimensions to screen
              const scaleX = video.videoWidth / window.screen.width;
              const scaleY = video.videoHeight / window.screen.height;
              
              console.log('Scale factors:', { scaleX, scaleY });
              
              // Draw only the selected portion from the video to canvas
              ctx.drawImage(
                video,
                this.currentSelection.x * scaleX,  // source x
                this.currentSelection.y * scaleY,  // source y
                this.currentSelection.width * scaleX,  // source width
                this.currentSelection.height * scaleY, // source height
                0, 0,  // destination x, y
                this.currentSelection.width,   // destination width
                this.currentSelection.height   // destination height
              );
              
              console.log('Screenshot captured successfully');
              
              // Cleanup
              stream.getTracks().forEach(track => track.stop());
              document.body.removeChild(video);
              
              resolve(canvas);
            } catch (drawError) {
              console.error('Error drawing to canvas:', drawError);
              stream.getTracks().forEach(track => track.stop());
              document.body.removeChild(video);
              reject(drawError);
            }
          }, 500); // Give more time for video to stabilize
        });
        
        video.addEventListener('error', (error) => {
          console.error('Video error:', error);
          stream.getTracks().forEach(track => track.stop());
          document.body.removeChild(video);
          reject(error);
        });
        
      }).catch(error => {
        console.error('Failed to get media stream:', error);
        document.body.removeChild(video);
        reject(error);
      });
    });
  }

  showScreenProcessingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'factcheck-processing';
    indicator.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      z-index: 1000001;
      text-align: center;
    `;
    
    indicator.innerHTML = `
      <div style="margin-bottom: 12px;">
        <div style="
          width: 24px;
          height: 24px;
          border: 3px solid #f3f3f3;
          border-top: 3px solid #007bff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin: 0 auto;
        "></div>
      </div>
      <p style="margin: 0; color: #333;">Processing screenshot...</p>
    `;
    
    // Add CSS animation
    if (!document.getElementById('factcheck-spin-style')) {
      const style = document.createElement('style');
      style.id = 'factcheck-spin-style';
      style.textContent = `
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `;
      document.head.appendChild(style);
    }
    
    document.body.appendChild(indicator);
  }

  showScreenError(message) {
    this.removeSelectionOverlay();
    
    const error = document.createElement('div');
    error.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #dc3545;
      color: white;
      padding: 12px 20px;
      border-radius: 6px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      z-index: 1000000;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    error.textContent = message;
    
    document.body.appendChild(error);
    
    setTimeout(() => {
      if (error.parentNode) {
        error.remove();
      }
    }, 5000);
  }

  cancelScreenSelection() {
    this.removeSelectionOverlay();
  }

  removeSelectionOverlay() {
    this.isSelecting = false;
    this.isDrawing = false; // Reset drawing state
    
    // Remove overlay
    if (this.selectionOverlay) {
      this.selectionOverlay.remove();
      this.selectionOverlay = null;
    }
    
    // Reset selection coordinates
    this.startX = 0;
    this.startY = 0;
    this.endX = 0;
    this.endY = 0;
    this.currentSelection = null;
    
    // Remove instructions
    const instructions = document.getElementById('factcheck-instructions');
    if (instructions) instructions.remove();
    
    // Remove confirmation dialog
    const confirmation = document.getElementById('factcheck-confirmation');
    if (confirmation) confirmation.remove();
    
    // Remove processing indicator
    const processing = document.getElementById('factcheck-processing');
    if (processing) processing.remove();
  }
}

// Initialize content script
const factCheckContentScript = new FactCheckContentScript();

// Make it globally available for screen capture integration
window.factCheckContentScript = factCheckContentScript;

// Add fade-in animation keyframes
const style = document.createElement('style');
style.textContent = `
  @keyframes factcheck-fade-in {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;
document.head.appendChild(style);