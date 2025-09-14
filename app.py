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
