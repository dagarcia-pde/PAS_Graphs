import pandas as pd

class Lot:
    def __init__(self, npi_name, lot_number, lot_title, fab_prod, ret_prod, dataengine):
        """
        Initialize a Lot instance and extract necessary data.

        Parameters:
        - lot_number: The identifier for the lot.
        - lot_title: The title associated with the lot.
        - fab_prod: The fabrication product identifier.
        - ret_prod: The reticle product identifier.
        - dataengine: An instance of PASDataEngine for data extraction.
        """        
        self.npi_name = npi_name
        self.lot_number = lot_number
        self.lot_title = lot_title
        self.fab_prod = fab_prod
        self.ret_prod = ret_prod
        # self.dataengine = dataengine
        
        try:
            self.lot_flow_raw = dataengine.extract_lotflow(self.lot_number, self.npi_name, self.lot_title,self.fab_prod,self.ret_prod)
            self.lot_flow_raw = dataengine.extract_lotflow(self.lot_number, self.npi_name, self.lot_title,self.fab_prod,self.ret_prod)
            # (self, lot, npi, title, fab_prod, ret_prod)
            self.lot_redwing = dataengine.extract_redwing(self.lot_number)
            self.lot_flow = self.cleanup_LotFlow(self.lot_flow_raw)
        except Exception as e:
            print(f"Error extracting data for lot {self.lot_number}: {e}")
            self.lot_flow = None
            self.lot_redwing = None
            raise

    def get_layer(row):

        value = row['OPER_SHORT_DESC']

        if row['EXEC_SEQ'] == 1:
            return "START"
        if value[:1] == "Z":
            return "SHIP"
        
        cond_list = [' ','#',
                     'L58','L52','L46','L4','L5', #10nm conditions
                     'L8c','L8s','L8b','L86','L81','L8d','L8' #18A conditions
                     ] 

        for cond in cond_list:
            value = value.replace(cond,'')
            
        value = value[:3]

        if row['OPER_LONG_DESC'].find(value) == -1:
            if value[0]=='M':
                value = 'MT' + value[1]
            else:
                value = 'VA' + value[1]
            
        return value
    
    def check_act(self, value):
        if '*' in value:
            return 1
        else:
            return 0
                
    def cleanup_LotFlow(self,df):
        df = df.sort_values(by='EXEC_SEQ', ascending=True)
        df['ACTIVITY'] = df['OPER_SHORT_DESC'].apply(lambda x: self.check_act(x))
        df['CUM_ACTIVITY'] = df['ACTIVITY'].cumsum()


        df = df[(df['EXEC_SEQ']==1) |  
            (df['OPERATION']=='9812') |
            ((df['AREA']=='LITHO') & (
                # These are the modules for 18A
                (df['MODULE'] == "LI-SAVli") | 
                (df['MODULE'] == "LI-SAYli") | 
                (df['MODULE'] == "LI-SBHcu") | 
                (df['MODULE'] == "LI-SBLcu") | 
                (df['MODULE'] == "LI-SNEli") | 
                (df['MODULE'] == "LI-SNYli") |
                # These are the modules for 10nm
                (df['MODULE'] == "LI-BE-193") | 
                (df['MODULE'] == "LI-BE-SED") | 
                (df['MODULE'] == "LI-BE-WET") | 
                (df['MODULE'] == "LI-FE-193") | 
                (df['MODULE'] == "LI-PD-WET") |
                (df['MODULE'] == "LI-SSAFI-WET") |
                (df['MODULE'] == "LI-WET") | 
                (df['MODULE'] == "LI-FE-248")                
                )
            )
            ]

        df['LAYER'] = df.apply(lambda row: self.get_layer(row), axis=1)

        df['OUT_DATE'] = pd.to_datetime(df['OUT_DATE'], errors='coerce')        
