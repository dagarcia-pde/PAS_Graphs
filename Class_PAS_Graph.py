from Class_PAS_Data_Extract import PASDataEngine
import pandas as pd
from cryptography.fernet import Fernet

class PASPlot:
    def __init__(self,input_file,email_file,ret_vers_file, key_file, cred_file, debug=False):
        self.debug = debug
        self.get_credentials(key_file, cred_file)
        
        self.input_file = self.read_excel_file(input_file)
        self.ret_vers_file = self.read_excel_file(ret_vers_file)
        self.extractEngine = PASDataEngine()

    def get_reticleData(self):
        distinct_retProds = self.input_df[['FAB_PROD','RET_PROD']].drop_duplicates()    
        imo_data = self.extractEngine.extract_reticleData(distinct_retProds)
    
    def get_lotflowData(self):
        for index,row in self.input_file.iterrows():
            product = row['PRODUCT']
            title = row['TITLE']
            lot = row['LOT']
            commit = row['COMMIT']
            fab_prod = row['FAB_PROD']
            ret_prod = row['RET_PROD']        
            
            print(f'Product = {product}, title = {title}, lot = {lot}, commit = {commit}')
            
            self.extractEngine.extract_lotflow(lot=lot,
                                          npi=product, 
                                          title=title, 
                                          fab_prod=fab_prod,
                                          ret_prod=ret_prod,
                                          data_source='F32_PROD_XEUS')
            
        
    
    def read_excel_file(self,file_path):
        """
        Function to read the Excel file and return a pandas DataFrame.
        """
        try:
            df = pd.read_excel(file_path)
            return df
        except Exception as e:
            print("Error reading Excel file:", e)
            return None
        
    def get_credentials(self, key_file, credential_file):
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
        self.UserName = credentials[0]
        self.PassWord = credentials[1]      
        
        pass

    def display(self):
        print(f"Name: {self.name}, Value: {self.value}")

    def update_value(self, new_value):
        self.value = new_value
        print(f"Value updated to: {self.value}")