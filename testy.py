import base64

def convert(image):
    f = open(image)
    data = f.read()
    f.close()

    string = base64.b64encode(data)
    encoded = data.encode("base64")
    print encoded
    print "####################################################################"
    print string
    return string
    
def decode(string):
    convert = base64.b64decode(string)
    print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    print convert
    t = open("example.jpg", "w+")
    t.write(convert)
    t.close()

if __name__ == "__main__":
    jangle = convert("test.jpg")
    decode(jangle)
    
