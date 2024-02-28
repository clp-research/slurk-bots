import base64

def encode_image_to_base64(image_path):
    try:
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read())
            return encoded_string.decode('utf-8')  # Convert bytes to a UTF-8 string
    except FileNotFoundError:
        return None


if __name__=='__main__':
    # Example usage
    image_path = 'data/sequences/legend_description.png'
    base64_string = encode_image_to_base64(image_path)
    print(base64_string)