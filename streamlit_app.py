import streamlit as st
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
import base64


# Create application title
st.title("OpenCV Deep Learning based Face Detection")

# List of example images
example_images = [
    "sample/faces.jpg",
    "sample/dog.jpg",
    "sample/Tamarindo_Beach.jpg"
    
    # Add more images here
]

# Add a select box for examples
example_selection = st.selectbox("Choose an example image:", ["None"] + example_images)

# Handling of example selection
if example_selection != "None":
    # Load the selected example image
    image_source = cv2.imread(example_selection, cv2.IMREAD_COLOR)
else:
    # File uploader for user's own image
    img_file_buffer = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png"])
    if img_file_buffer is not None:
        raw_bytes = np.asarray(bytearray(img_file_buffer.read()), dtype=np.uint8)
        image_source = cv2.imdecode(raw_bytes, cv2.IMREAD_COLOR)
    else:
        # If no input provided
        st.text("Please upload an image or select an example.")
        st.stop()

def histogram_equalization(image):
    rgb_img = image

    # convert from RGB color-space to YCrCb
    ycrcb_img = cv2.cvtColor(rgb_img, cv2.COLOR_BGR2YCrCb)

    # equalize the histogram of the Y channel
    ycrcb_img[:, :, 0] = cv2.equalizeHist(ycrcb_img[:, :, 0])

    # convert back to RGB color-space from YCrCb
    equalized_img = cv2.cvtColor(ycrcb_img, cv2.COLOR_YCrCb2BGR)
    return equalized_img

def adjust_gamma(image, gamma=1.5):
    invGamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** invGamma * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(image, table)
    

    
with st.sidebar:
    st.title("Modify original image to improve facial detection confidence")
   
    # Checkbox for equalization
    hist_on = st.checkbox("Equalize brightness", help="Histogram equalization spreads out intensity values, normally adding contrast to an image.") 
    if hist_on:
        image = histogram_equalization(image_source)
    else: 
        image = image_source
    
    # Gamma Correction Slider
    gamma = st.slider("Amount of gamma/exposure correction", min_value=0.0, max_value=2.0, step=.1, value=1.0, help="gamma")
    image = adjust_gamma(image, gamma)
    
    # Create Slider 
    kernel_size = st.slider("Blurring Kernel Size", min_value=0, max_value=100, step=1, value=0,  label_visibility="visible", help="Some blurring can help reduce noise and fine details, so the detection algorithm can focus on key facial features.")
    
    # Pre-Preprocessing Code
    if kernel_size > 3:
        image = cv2.blur(image, (kernel_size, kernel_size))

# Function to load the DNN model.
@st.cache_resource()
def load_model():
    modelFile = "res10_300x300_ssd_iter_140000_fp16.caffemodel"
    configFile = "deploy.prototxt"
    net = cv2.dnn.readNetFromCaffe(configFile, modelFile)
    return net

# Function for detecting faces in an image.
def detectFaceOpenCVDnn(net, frame):
    # Create a blob from the image and apply some pre-processing.
    blob = cv2.dnn.blobFromImage(
        frame,
        1.0,
        (300, 300),
        [104, 117, 123],
        False,
        False,
    )
    # Set the blob as input to the model.
    net.setInput(blob)
    # Get Detections.
    detections = net.forward()
    return detections


# Function for annotating the image with bounding boxes for each detected face.
def process_detections(frame, detections, conf_threshold=0.5):
    bboxes = []
    frame_h = frame.shape[0]
    frame_w = frame.shape[1]
    # Loop over all detections and draw bounding boxes around each face.
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            x1 = int(detections[0, 0, i, 3] * frame_w)
            y1 = int(detections[0, 0, i, 4] * frame_h)
            x2 = int(detections[0, 0, i, 5] * frame_w)
            y2 = int(detections[0, 0, i, 6] * frame_h)
            bboxes.append([x1, y1, x2, y2])
            bb_line_thickness = max(1, int(round(frame_h / 200)))
            # Draw bounding boxes around detected faces.
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), bb_line_thickness, cv2.LINE_8)
    return frame, bboxes


# Function to generate a download link for output file.
def get_image_download_link(img, filename, text):
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    href = f'<a href="data:file/txt;base64,{img_str}" download="{filename}">{text}</a>'
    return href

# Create placeholders to display input and output images.
placeholders = st.columns(2)

# Display Input image in the first placeholder.
placeholders[0].image(image, channels="BGR")
placeholders[0].text("Processed Input Image")

with st.sidebar:
    # Create a Slider and get the threshold from the slider.
    conf_threshold = st.slider("SET Confidence Threshold", min_value=0.0, max_value=1.0, step=0.01, value=0.5, label_visibility="visible", help="The higher the confidence threshold, the more certain a face has been detected. Aim for 0.9+")

# call the load_model function for model loading.
net = load_model()

# Call the face detection model to detect faces in the image.
detections = detectFaceOpenCVDnn(net, image)

# Process the detections based on the current confidence threshold.
out_image, _ = process_detections(image_source, detections, conf_threshold=conf_threshold)

# Display Detected faces.
placeholders[1].image(out_image, channels="BGR")
placeholders[1].text("Original Image with Detections")

# Convert opencv image to PIL.
out_image = Image.fromarray(out_image[:, :, ::-1])
# Create a link for downloading the output file.
st.markdown(get_image_download_link(out_image, "face_output.jpg", "Download Output Image"), unsafe_allow_html=True)
