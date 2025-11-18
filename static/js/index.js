class SignLanguageApp {
    constructor() {
        this.video = document.getElementById('video');
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.startBtn = document.getElementById('startBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.captureBtn = document.getElementById('captureBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.clearHistoryBtn = document.getElementById('clearHistoryBtn');
        this.translationText = document.getElementById('translationText');
        this.confidenceValue = document.getElementById('confidenceValue');
        this.currentSign = document.getElementById('currentSign');
        this.historyList = document.getElementById('historyList');
        this.cameraStatus = document.getElementById('cameraStatus');
        
        this.stream = null;
        this.isProcessing = false;
        this.captureInterval = null;
        
        this.init();
    }
    
    init() {
        this.startBtn.addEventListener('click', () => this.startCamera());
        this.stopBtn.addEventListener('click', () => this.stopCamera());
        this.captureBtn.addEventListener('click', () => this.captureAndTranslate());
        this.clearBtn.addEventListener('click', () => this.clearTranslation());
        this.clearHistoryBtn.addEventListener('click', () => this.clearHistory());
        
        // Set up canvas size
        this.canvas.width = 640;
        this.canvas.height = 480;
        
        this.checkCameraSupport();
    }
    
    checkCameraSupport() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert('Your browser does not support camera access. Please use a modern browser like Chrome or Firefox.');
            this.startBtn.disabled = true;
        }
    }
    
    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user' // Use front camera
                },
                audio: false 
            });
            
            this.video.srcObject = this.stream;
            this.video.play();
            
            this.startBtn.disabled = true;
            this.stopBtn.disabled = false;
            this.captureBtn.disabled = false;
            this.cameraStatus.textContent = 'Camera on';
            this.cameraStatus.style.color = 'green';
            
            // Start auto-capture every 3 seconds
            this.startAutoCapture();
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Cannot access camera: ' + error.message);
        }
    }
    
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        this.stopAutoCapture();
        
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.captureBtn.disabled = true;
        this.cameraStatus.textContent = 'Camera off';
        this.cameraStatus.style.color = 'red';
        
        this.video.srcObject = null;
    }
    
    startAutoCapture() {
        // Capture and translate every 3 seconds
        this.captureInterval = setInterval(() => {
            if (!this.isProcessing) {
                this.captureAndTranslate();
            }
        }, 3000);
    }
    
    stopAutoCapture() {
        if (this.captureInterval) {
            clearInterval(this.captureInterval);
            this.captureInterval = null;
        }
    }
    
    async captureAndTranslate() {
        if (!this.stream || this.isProcessing) return;
        
        this.isProcessing = true;
        this.captureBtn.disabled = true;
        this.captureBtn.textContent = 'Processing...';
        
        try {
            // Draw video frame to canvas
            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            
            // Calculate ROI coordinates (center of video)
            const roiWidth = 300;
            const roiHeight = 300;
            const roiX = (this.canvas.width - roiWidth) / 2;
            const roiY = (this.canvas.height - roiHeight) / 2;
            
            // Extract ROI from canvas
            const roiImageData = this.ctx.getImageData(roiX, roiY, roiWidth, roiHeight);
            
            // Create a temporary canvas for the ROI
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = roiWidth;
            tempCanvas.height = roiHeight;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.putImageData(roiImageData, 0, 0);
            
            // Convert to base64
            const imageData = tempCanvas.toDataURL('image/jpeg');
            
            // Send to backend for translation
            const response = await fetch('/api/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ image: imageData })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.translationText.textContent = result.translation;
                this.confidenceValue.textContent = `${Math.round(result.confidence * 100)}%`;
                this.currentSign.textContent = result.sign;
                
                // Update confidence color based on value
                const confidence = result.confidence * 100;
                this.confidenceValue.style.color = confidence > 70 ? 'green' : 
                                                  confidence > 40 ? 'orange' : 'red';
                
                // Update history
                this.updateHistory();
            } else {
                this.currentSign.textContent = 'No sign detected';
            }
            
        } catch (error) {
            console.error('Error processing frame:', error);
            alert('Error processing image: ' + error.message);
        } finally {
            this.isProcessing = false;
            this.captureBtn.disabled = false;
            this.captureBtn.textContent = 'Capture & Translate';
        }
    }
    
    async clearTranslation() {
        try {
            const response = await fetch('/api/translation', {
                method: 'DELETE'
            });
            
            const result = await response.json();
            if (result.success) {
                this.translationText.textContent = '';
                this.confidenceValue.textContent = '0%';
                this.currentSign.textContent = 'None';
            }
        } catch (error) {
            console.error('Error clearing translation:', error);
        }
    }
    
    async updateHistory() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();
            
            this.historyList.innerHTML = '';
            data.history.slice(-5).reverse().forEach(item => {
                const historyItem = document.createElement('div');
                historyItem.className = 'history-item';
                historyItem.textContent = `${new Date(item.timestamp * 1000).toLocaleTimeString()}: ${item.text}`;
                this.historyList.appendChild(historyItem);
            });
        } catch (error) {
            console.error('Error fetching history:', error);
        }
    }
    
    async clearHistory() {
        try {
            const response = await fetch('/api/history', {
                method: 'DELETE'
            });
            
            const result = await response.json();
            if (result.success) {
                this.historyList.innerHTML = '';
            }
        } catch (error) {
            console.error('Error clearing history:', error);
        }
    }
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new SignLanguageApp();
});