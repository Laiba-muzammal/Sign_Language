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

load_dotenv()

app = Flask(__name__)

# Initialize Roboflow Predictor
roboflow_api_key = os.getenv('ROBOFLOW_API_KEY')
model_id = os.getenv('ROBOFLOW_MODEL_ID')
version_number = os.getenv('ROBOFLOW_VERSION')

predictor = RoboflowPredictor(roboflow_api_key, model_id, version_number)

translation_history = []
translate=""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/translate', methods=['POST'])
def translate_image():

    global current_translation
    
    try:
        data= request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image provided'}), 400

        image_data = data['image'].split(",")[1]
        image_bytes = base64.b64decode(image_data)

        image = Image.open(io.BytesIO(image_bytes))
        open_cv_image = np.array(image ,cv2.COLOR_RGB2BGR)
       
        sign, confidience = predictor.predict(open_cv_image)

        response = {
            'translation': current_translation,
            'success': False,
            'confidence': 0
        }

        if sign and confidience >0.6:
            response['translation'] = current_translation
            response['success'] = True
            response['confidence'] = confidience

            if sign.lower() == 'space':
                current_translation += " "
            elif sign.lower() == 'clear':
                current_translation = ""
            else:
                current_translation += sign + " "

            if current_translation.strip():
                translation_history.append({
                    'text': current_translation,
                    'timestamp': time.time(),
                    'confidence': response['confidence']
                })

            response['translation'] = current_translation

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/history', methods=['GET', 'DELETE'])
def get_history():

    global translation_history
    if request.method == 'GET':
        return jsonify({'history': translation_history})
    
    elif request.method == 'DELETE':
        translation_history.clear()
        return jsonify({'message': 'Translation history cleared'}), 200
    
@app.route('/api/debug/camera', methods=['GET'])
def debug_camera():
    try:
        test_image= np.zeros((300,300,3), dtype=np.uint8)
        cv2.putText(test_image, "DEBUG", (50,150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 3)
        roi = extract_roi((50, 50, 200, 200), test_image)

        return jsonify({
            ' status': 'Camera utils working',
            'image_shape': str(test_image.shape),
            'roi_shape': str(roi.shape) if roi is not None else 'None'
        })

    except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/translate', methods=['GET','POST','DELETE'])
def manage_translation():
    global current_translation
    if request.method == 'GET':
        return jsonify({ 'current_translation': current_translation,
            'history': translation_history[-10:] })
    
    elif request.method == 'POST':
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        current_translation = data['text']
        return jsonify({'message': 'Translation updated', 'translation': current_translation})
    
    elif request.method == 'DELETE':
        current_translation = ""
        return jsonify({'message': 'Translation cleared'}), 200

@app.route('/api/debug/test', methods=['GET'])
def debug_test():
    try:
        test_image= np.zeros((300,300,3), dtype=np.uint8)
        cv2.putText(test_image, "TEST", (50,150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 3)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)