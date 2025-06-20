import importlib
import pandas as pd
import warnings
import os
import shutil
import argparse
import sys

code_path = r'\\azshfs.intel.com\AZAnalysis$\1272_MAODATA\Config\PDE\dagarcia\PAS_CODE'

print(f"Adding code path: {code_path}")

sys.path.append(code_path)

try:
    import Class_PAS_Data_Extract
    import Class_PAS_Product
    import Class_PAS_Email
    import Class_PAS_Graph
    print("Package imported successfully!")
except ImportError as e:
    print(f"Failed to import package. Error: {e}")

warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
pd.options.mode.chained_assignment = None

# plotPaths = "plots/"
plotPaths = r'\\shuser-Prod.intel.com\shProduser$\dagarcia\PAS_GRAPH\Plots'

key_file = r'\\shuser-Prod.intel.com\shProduser$\dagarcia\keys\secret.key'
credential_file = r'\\shuser-Prod.intel.com\shProduser$\dagarcia\EncryptedCredentials\credentials.encrypted'
# config_file = r'\\azshfs.intel.com\AZAnalysis$\1272_MAODATA\Config\PDE\dagarcia\PAS_CONFIG\P1275_Config.xlsx'

Server = "smtpauth.intel.com"
Port = "587"
UserEmail = "david.a.garcia@intel.com"

def read_excel_to_dataframe(file_path, sheet_name, halt_on_error=True):
    """
    Reads a specific worksheet from an Excel file into a Pandas DataFrame.

    Parameters:
    - file_path (str): The path to the Excel file.
    - sheet_name (str or int): The name or index of the worksheet to load.
    - halt_on_error (bool): Flag indicating whether to halt execution on error.
                            If False, the function will return None on error.

    Returns:
    - DataFrame or None: The DataFrame if successful, or None if an error occurs and halt_on_error is False.
    """
    try:
        # Attempt to read the specified worksheet into a DataFrame
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        return df
    except Exception as e:
        # Handle the error based on the halt_on_error flag
        if halt_on_error:
            print(f"Error reading {file_path}, sheet {sheet_name}: {e}")
            raise  # Re-raise the exception to halt execution
        else:
            print(f"Error reading {file_path}, sheet {sheet_name}: {e}. Returning None.")
            return None

def main():

    # Entry point for the script
    if os.path.exists(plotPaths):
        for filename in os.listdir(plotPaths):
            file_path = os.path.join(plotPaths, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        os.makedirs(plotPaths)


    pas_config = read_excel_to_dataframe(config_file, 'PlotConfig', halt_on_error=True)
    email_config = read_excel_to_dataframe(config_file, 'EmailConfig', halt_on_error=True)
    reticle_config = read_excel_to_dataframe(config_file, 'ReticleConfig', halt_on_error=False)

    dataengine = Class_PAS_Data_Extract.PASDataEngine()
    
    tech = pas_config['Technology'].values[0]

    email = Class_PAS_Email.EmailUpdate(
        server = Server,
        port = Port,
        email = UserEmail,
        key_file=key_file, 
        credential_file=credential_file, 
        email_config=email_config,
        plot_folder=plotPaths,
        subject=f"NPI PAS Update - {tech}",
        debug=False)

    if  pas_config is not None:
        unique_combos = pas_config.groupby(['PRODUCT', 'FAB_PROD', 'RET_PROD'])['COMMIT'].max().reset_index()

        products = unique_combos.set_index('PRODUCT').to_dict(orient='index')
        
        for product, details in products.items():
            print(f"Processing Product: {product}")
            print(f"    FAB_PROD: {details['FAB_PROD']}, RET_PROD: {details['RET_PROD']}, COMMIT: {details['COMMIT']}")
            
            prod = Class_PAS_Product.Product(product, products[product],  dataengine, ret_version=reticle_config, lots=None, debug_flag=False)
            
            currentProd = pas_config[pas_config['PRODUCT']==product]
            for idx, row in currentProd.iterrows():
                print(f"        Adding Lot: {row['LOT']}, Title: {row['TITLE']}")
                prod.add_lot(row['LOT'], row['TITLE'])
                
            prod.build_plot_data()
            
            myGraph = Class_PAS_Graph.PASPlot(prod,plotPaths)
            myGraph.make_plot()        
            
            email.addProduct(product, prod.plot_data_raw)

    if email_flag:
        email.send_email()
    else:
        print("Email flag is set to False. No email will be sent.")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="PAS Graphs Script")
    parser.add_argument('--config', type=str, help='Path to the config Excel file')
    parser.add_argument('--email', type=str, help='True/False Flag to send email', default='False')
    args = parser.parse_args()

    global email_Flag

    email_flag = False

    if args.email.lower() == 'true':
        email_flag = True

    

    global config_file

    if args.config:
        config_file = args.config
    else:
        print("No config parameter passed.  Using default config.")
        config_file = r'\\azshfs.intel.com\AZAnalysis$\1272_MAODATA\Config\PDE\dagarcia\PAS_CONFIG\P1275_Config_DEBUG.xlsx'

    print(f"Using config file: {config_file}")
    main()
    # main()