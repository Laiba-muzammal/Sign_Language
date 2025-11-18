import requests
import cv2
import os
import tempfile

class RoboFlowPredictor:
    def __init__(self, api_key, model_id,version_number):
        self.api_key=api_key
        self.model_id=model_id
        self.version_number=version_number
        self.api_url= f"https://detect.roboflow.com/{model_id}/{version_number}"
        self.params={"api_key":api_key}

    def predict_frame(self,frame):
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path=temp_file.name
                cv2.imwrite(temp_path, frame)

                with open(temp_path,"rb") as image_file:
                    response=requests.post(
                        self.api_url,
                        params=self.params,
                        files={"file":image_file}
                    )

                    os.unlink(temp_path)

                    if response.status_code==200:
                        return self.parse_predication(response.json())
                    else:
                        print (f"API ERROR: {response.status_code}-{response.text}")
                        return None, 0
                    
        except Exception as e:
            print(f"Predication error: {e}")
            return None ,0
        
    def parse_prediction(self,predication_data):
        if not predication_data or "predications" not in predication_data:
            return None,0
        
        predication=predication_data["predications"]
        if not predication:
            return None, 0
        
        best_predication=max(predication, key=lambda x:x["confidience"])
        return best_predication["class"], best_predication["confidience"]