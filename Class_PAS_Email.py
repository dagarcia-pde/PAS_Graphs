from cryptography.fernet import Fernet
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path
import os
import re

class EmailUpdate:
    def __init__(self, server, port, email, key_file, credential_file, email_config, plot_folder, subject, debug=False):
        self.debug = debug
        self.server = server
        self.port = port
        self.email = email
        self.username, self.password = self.decrypt_credentials(key_file, credential_file)
        self.email_config = email_config
        self.email_addresses = self.getemails(email_config)
        self.plot_folder = plot_folder
        self.subject = subject

        self.html_body = "<html><body>"

        self.msg = EmailMessage()
        self.msg['Subject'] = self.subject
        self.msg['From'] = self.email
        self.msg['To'] = ', '.join(self.email_addresses)
        self.msg.set_content('This is a plain text body')

    def sanitize_filename(self, title):
        """
        Sanitizes a string to be safe for use as a filename by:
        - Replacing spaces with underscores
        - Removing or replacing invalid characters
        """
        # Replace spaces with underscores
        title = title.replace(' ', '_')
        
        # Remove or replace invalid characters
        # The regex below will remove any characters that are not alphanumeric, underscores, or dots
        title = re.sub(r'[^\w\.]', '', title)
        
        return title

    def getemails(self, email_config):
        email_addresses = email_config['Email'].to_list()
        if self.debug:
            email_addresses = email_config.loc[email_config['Debug'] == True, 'Email'].to_list()
        return email_addresses 
    
    def send_email(self):    
        self.html_body += "</body></html>"
        self.msg.add_alternative(self.html_body, subtype='html')

        server = smtplib.SMTP(self.server, self.port)
        server.starttls()
        server.login(self.username, self.password)
        server.send_message(self.msg)
        server.quit()
        
    def decrypt_credentials(self, key_file, credential_file):
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
    
    def addProduct(self, npi_name, plot_data):
        
        image_cid = make_msgid()
        image_cid = image_cid[1:image_cid.find('@')]

        filename = self.sanitize_filename(npi_name+'_NPI')+'.png'
        
        # Combine them into a full file path
        full_path = os.path.join(self.plot_folder, filename)        

        self.html_body += f"<p style='font-weight: bold; text-decoration: underline; font-size: 16px;'>{npi_name}</p>{self.lookAhead(plot_data)}<img src='cid:{image_cid}'>"

        with open(full_path, 'rb') as img:
            self.msg.add_related(img.read(), 'image','png', cid=image_cid)

        


    def lookAhead(self, plot_data):
        temp = plot_data

        # Filter columns with 'ACTUAL' in the title
        actual_columns = [col for col in temp.columns if 'ACTUAL' in col]

        # Find the column with the most non-missing entries
        most_entries_column = max(actual_columns, key=lambda col: temp[col].notna().sum())

        # Get the first 10 rows with missing data in the selected column
        missing_data_rows = temp[temp[most_entries_column].isna()].head(10)

        most_entries_column = most_entries_column.replace('ACTUAL', 'TREND')

        missing_data_rows = missing_data_rows[missing_data_rows['SHIP'].isna()] 

        html_table = '<p>Next 10 layer look ahead:'


        if missing_data_rows.empty:
            html_table += ' Reticles have all shipped!</p>'
        else:
            html_table += '</p>' + missing_data_rows.to_html(index=False)        

        return html_table


    