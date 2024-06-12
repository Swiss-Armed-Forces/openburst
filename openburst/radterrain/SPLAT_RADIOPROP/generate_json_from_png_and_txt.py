"""
generates a json file from PNG and TXT 
called by radterrain.py to send the Splat! propagation image and text to client
"""

import json
import base64


ENCODING = "utf-8"
IMAGE_NAME = "height_profile.png"
JSON_NAME = "tmp.json"
TXT_NAME = "TX_-to-RX_.txt"

# read the png file
with open(IMAGE_NAME, "rb") as imageFile:
    png_bytes = base64.b64encode(imageFile.read())

with open(TXT_NAME, "rb") as f:
    TXT_CONTENTS = str(f.read())


# # convert it to json
# decode these bytes to text
# result: string (in utf-8)
base64_string = png_bytes.decode(ENCODING)

# optional: doing stuff with the data
# result here: some dict
raw_data = {IMAGE_NAME: base64_string, TXT_NAME: TXT_CONTENTS}

# now: encoding the data to json
# result: string
json_data = json.dumps(raw_data, indent=2)

with open(JSON_NAME, "w") as another_open_file:
    another_open_file.write(json_data)
