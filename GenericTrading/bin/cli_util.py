'''
Created on Nov 20, 2017

@author: zorindev
'''
import base64
import time

def encode(key, clear):
    enc = []
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc))

def decode(key, enc):
    dec = []
    enc = base64.urlsafe_b64decode(enc)
    for i in range(len(enc)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
        dec.append(dec_c)
    return "".join(dec)

if __name__ == "__main__":
    
    key = str(int(time.time()))
    key = "q6SjmqCXma8qJpipJaYpp6XpJY"
    username = encode(key, "zorindev")
    password = encode(key, "we1sderedse")
    
    print username, " : ", password
    
    
    
    