
# you also need to download this file: https://github.com/luis-almeida/unveil/blob/master/jquery.unveil.js
# and place it in the same directory as this python file with the name "jquery.unveil.js"

import os
from io import BytesIO

from flask import Flask, Response, request, abort, render_template_string, send_from_directory
from PIL import Image

app = Flask(__name__)

WIDTH = 640
HEIGHT = 640

TEMPLATE = '''
<!DOCTYPE html>
<html>
    <head>
        <title></title>
        <meta charset="utf-8"/>
        <style>
        body {
            margin: 0;
            background-color: #333;
        }
        .image {
            display: block;
            margin: 2em auto;
            background-color: #444;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
        }
        img {
            display: block;
        }
        </style>
        <script src="https://code.jquery.com/jquery-1.10.2.min.js" charset="utf-8"></script>
        <script src="jquery.unveil.js" charset="utf-8"></script>
        <script>
            $(document).ready(function() {
                $('img').unveil();
            });
        </script>
    </head>
    <body>
        {% for image in images %}
            <a class="image" href="{{ image.src }}" style="width: {{ image.width }}px; height: {{ image.height }}px">
                <img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="{{ image.src }}?w={{ image.width }}&amp;h={{ image.height }}" width="{{ image.width }}" height="{{ image.height }}" />
            </a>
        {% endfor %}
    </body>
'''

@app.route('/<path:filename>')
def image(filename):
    try:
        w = int(request.args['w'])
        h = int(request.args['h'])
    except (KeyError, ValueError):
        return send_from_directory('.', filename)

    try:
        im = Image.open(filename)
        im.thumbnail((w, h), Image.ANTIALIAS)
        io = BytesIO()
        im.save(io, format='JPEG')
        return Response(io.getvalue(), mimetype='image/jpeg')

    except IOError:
        abort(404)

    return send_from_directory('.', filename)



@app.route('/')
def index():
    images = []
    for root, dirs, files in os.walk('.'):
        for filename in [os.path.join(root, name) for name in files]:
            if not filename.endswith('.jpg'):
                continue
            im = Image.open(filename)
            w, h = im.size
            aspect = 1.0*w/h
            if aspect > 1.0*WIDTH/HEIGHT:
                width = min(w, WIDTH)
                height = width/aspect
            else:
                height = min(h, HEIGHT)
                width = height*aspect
            images.append({
                'width': int(width),
                'height': int(height),
                'src': filename
            })

    return render_template_string(TEMPLATE, **{
        'images': images
    })



if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port="3000")
