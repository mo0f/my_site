# When running locally install requirements using
# pip3 install -t lib -r requirements.txt

# [START app]
import logging
import base64, re

from flask import Flask, jsonify, request, render_template
import sys
from io import BytesIO
from PIL import Image

#Repackage these 2.
from cloud_utils import mnist_prediction
import numpy as np
from googleapiclient import discovery

app = Flask(__name__)

service = discovery.build('ml', 'v1')

@app.route('/')
def index():
    return render_template('homepage.html')

# {'loss': 0.10061083, 'global_step': 20000, 'accuracy': 0.9701}
@app.route('/draw', methods=['GET', 'POST'])
def draw():
    if request.method == 'POST':
        print("waiting on post")
        dataURI = request.data.decode('UTF-8')
        image_data = re.sub('^data:image/png;base64,', '', dataURI)
        im = Image.open(BytesIO(base64.b64decode(image_data)))
        im.thumbnail((28,28), Image.ANTIALIAS)
        #buffered = BytesIO()
        #im.save(buffered, format="PNG")
        #img_str = base64.b64encode(buffered.getvalue())
        # rbgt = 4channels for pixel
        # Eventually make this output 0 or 1 per RBG value
        #pixels = list(im.getdata())
        pixels = list(im.getdata())
        # Turn pixels to B&W if they are over $threshold value.
        threshold = 150
        # Color value seems to be stored in the transparency channel.
        # But will summate over all just incase.
        # Is it possible to have thumbnail set PNG to a different mode?
        b_w = list(map(lambda rgb: 1 if sum(rgb) >= threshold else 0, pixels))
        # Now send the array off to the ML tool and return it.
        #pred = task.make_prediction(b_w)
        data = np.array(b_w)
        data.shape = (28,28)
        data = data.tolist()
        req = {"instances": [{"x": data}]}
        prediction = mnist_prediction(service, req)
        print(prediction)
        predicted_class = prediction['predictions'][0]['classes']
        return jsonify(prediction=predicted_class)
    return render_template('digits.html')
    # Potentially add another POST where we add the user corrected result to an
    # "ON DEMAND" First Generation MYSQL instance. Or just regular DB hosted in a bucket?

@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500
# [END app]