from cryptography.fernet import Fernet
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

class EmailUpdate:
    def __init__(self, server, port, email, key_file, credential_file, email_config, debug=False):
        self.debug = debug
        self.server = server
        self.port = port
        self.email = email
        self.username, self.password = self.decrypt_credentials(key_file, credential_file)
        
    
    def getemails(self, email_config):
        email_addresses = email_config['Email'].to_list()
        if self.debug:
            email_addresses = email_config.loc[email_config['Debug'] == True, 'Email'].to_list()
        return email_addresses 
    
    def send_email(self, subject, body, to_email):    
        x=1
        
    def decrypt_credentials(key_file, credential_file):
        # Read the key from the key file
        with open(key_file, 'rb') as file:
            key = file.read()

        # Initialize the Fernet object with the key
        cipher = Fernet(key)

        # Read the encrypted credentials from the credential file
        with open(credential_file, 'rb') as file:
            encrypted_credentials = file.read()

        # Decrypt the credentials
        decrypted_credentials = cipher.decrypt(encrypted_credentials).decode()

        # Parse the decrypted credentials
        credentials = decrypted_credentials.split(',')
        
        return credentials[0], credentials[1]
        


    def buidTable(self):
        x=1
    
    def buildEmail(self):
        
    