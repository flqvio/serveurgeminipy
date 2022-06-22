import ssl
import socket
from datetime import datetime
import logging
import time
import traceback
from urllib import parse
from servgemini import settings
from servgemini.gemini import GeminiRequest, GeminiResponse, GeminiException
import sys

# création du logger pour les logs de connexion
logger = logging.getLogger('gemini')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Création du formatter pour la date
formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s')

# ajout du format de date
ch.setFormatter(formatter)
logger.addHandler(ch)

# Création d'un socket pour le serveur
serverSocket = socket.socket()
serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serverSocket.bind((settings['BIND'], settings['PORT']))

# socket mis en écoute pour le serveur
serverSocket.listen()
print(f"\r\nservtest écoute sur {settings['BIND']}:{settings['PORT']}.\r\n")

while(True):
    # acceptation de la connexion par le serveur
    (clientConnection, clientAddress) = serverSocket.accept()
    
    # mise en place de la connexion sécurisée avec SSL
    secureClientSocket = ssl.wrap_socket(clientConnection, 
                                        server_side=True, 
                                        ca_certs="/home/flavio/gemini/certificate/fullchain.pem", 
                                        certfile="/home/flavio/gemini/certificate/cert.pem",
                                        keyfile="/home/flavio/gemini/certificate/key.pem", 
                                        cert_reqs=ssl.CERT_NONE,
                                        ssl_version=ssl.PROTOCOL_TLSv1_2)

    url = secureClientSocket.recv(1024).rstrip().decode('UTF-8')
    try:
        req = GeminiRequest(url)
        response = req.dispatch()
        secureClientSocket.send(response.header)
        if response.body is not None:
            logger.info(f"{response.status}\t{url}")
            secureClientSocket.sendall(response.body)
        secureClientSocket.close()

    except GeminiException as e:
        response = e.response()
        secureClientSocket.sendall(response.header)
        logger.error(f"\t{response.status}\t{url}")
        secureClientSocket.close()
    