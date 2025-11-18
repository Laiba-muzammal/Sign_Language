from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import base64
import io
from PIL import Image
import time
import os
from dotenv import load_dotenv
from camera_utils import extract_roi, draw_roi, frame_to_base64
from roboflow_integration import RoboflowPredictor

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize Roboflow predictor
roboflow_api_key = os.getenv('ROBOFLOW_API_KEY')
model_id = os.getenv('ROBOFLOW_MODEL_ID')
version_number = os.getenv('ROBOFLOW_VERSION')

predictor = RoboflowPredictor(roboflow_api_key, model_id, version_number)

# Store translation history
translation_history = []
current_translation = ""

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/translate', methods=['POST'])
def translate_image():
    """API endpoint to translate sign language image"""
    global current_translation
    
    try:
        # Get image data from request
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Extract base64 image data
        image_data = data['image'].split(',')[1]  # Remove data:image/jpeg;base64,
        image_bytes = base64.b64decode(image_data)
        
        # Convert to OpenCV format
        image = Image.open(io.BytesIO(image_bytes))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Process image and get prediction
        sign, confidence = predictor.predict_frame(frame)
        
        response_data = {
            'translation': current_translation,
            'success': False,
            'confidence': 0
        }
        
        if sign and confidence > 0.6:  # Confidence threshold
            response_data['sign'] = sign
            response_data['confidence'] = confidence
            response_data['success'] = True
            
            if sign.lower() == 'space':
                current_translation += " "
            elif sign.lower() == 'clear':
                current_translation = ""
            else:
                current_translation += sign + " "
            
            # Add to history if we have a meaningful translation
            if current_translation.strip():
                translation_history.append({
                    'text': current_translation,
                    'timestamp': time.time(),
                    'confidence': confidence
                })
            
            response_data['translation'] = current_translation
            
        return jsonify(response_data)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/translation', methods=['GET', 'POST', 'DELETE'])
def manage_translation():
    """API endpoint to get, update, or clear translation"""
    global current_translation
    
    if request.method == 'GET':
        return jsonify({
            'current_translation': current_translation,
            'history': translation_history[-10:]  # Last 10 translations
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        if data and 'text' in data:
            current_translation = data['text']
            return jsonify({'success': True, 'translation': current_translation})
        return jsonify({'error': 'No text provided'}), 400
    
    elif request.method == 'DELETE':
        current_translation = ""
        return jsonify({'success': True, 'message': 'Translation cleared'})

@app.route('/api/history', methods=['GET', 'DELETE'])
def manage_history():
    """API endpoint to get or clear history"""
    global translation_history
    
    if request.method == 'GET':
        return jsonify({'history': translation_history})
    
    elif request.method == 'DELETE':
        translation_history = []
        return jsonify({'success': True, 'message': 'History cleared'})

@app.route('/api/debug/test', methods=['GET'])
def debug_test():
    """Test endpoint to check if API is working"""
    try:
        # Create a test image
        test_image = np.zeros((300, 300, 3), dtype=np.uint8)
        cv2.putText(test_image, "TEST", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 5)
        
        # Test prediction
        sign, confidence = predictor.predict_frame(test_image)
        
        return jsonify({
            'status': 'API is working',
            'test_prediction': sign,
            'confidence': confidence,
            'model_id': model_id,
            'api_key_set': bool(roboflow_api_key)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/camera', methods=['GET'])
def debug_camera():
    """Test if camera utils are working"""
    try:
        # Create a test image
        test_image = np.zeros((300, 300, 3), dtype=np.uint8)
        cv2.putText(test_image, "DEBUG", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
        
        # Test ROI extraction
        roi = extract_roi(test_image, (50, 50, 200, 200))
        
        return jsonify({
            'status': 'Camera utils working',
            'image_shape': str(test_image.shape),
            'roi_shape': str(roi.shape) if roi is not None else 'None'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)