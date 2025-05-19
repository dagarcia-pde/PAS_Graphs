import pandas as pd

class Lot:
    def __init__(self, npi_name, lot_number, lot_title, fab_prod, ret_prod, commit, dataengine, debug_flag=False):
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
        self.commit = commit
        self.debug_flag = debug_flag
        # self.dataengine = dataengine
        
        try:
            self.lot_flow_raw = dataengine.extract_lotflow(self.lot_number, self.npi_name, self.lot_title,self.fab_prod,self.ret_prod)
            self.lot_flow_raw = dataengine.extract_lotflow(self.lot_number, self.npi_name, self.lot_title,self.fab_prod,self.ret_prod)
            self.lot_flow_raw.to_csv(f"debug/lot_flow_{lot_number}_raw.csv", index=False)
            # (self, lot, npi, title, fab_prod, ret_prod)
            self.lot_redwing = dataengine.extract_redwing(self.lot_number)
            self.lot_flow = self.cleanup_LotFlow(self.lot_flow_raw)
            self.generate_plot_data()
        except Exception as e:
            print(f"Error extracting data for lot {self.lot_number}: {e}")
            self.lot_flow = None
            self.lot_redwing = None
            raise

        
        if self.debug_flag:
            self.lot_flow_raw.to_csv(f"debug/lot_flow_{lot_number}_raw.csv", index=False)
            self.lot_flow.to_csv(f"debug/lot_flow_{lot_number}.csv", index=False)
            self.lot_redwing.to_csv(f"debug/lot_redwing_{lot_number}_raw.csv", index=False)
    

    def get_layer(self, row):

        value = row['OPER_SHORT_DESC']

        if row['EXEC_SEQ'] == 1:
            return "START"
        if value[:1] == "Z":
            return "SHIP"
        
        cond_list = [' ','#',
                     'L58','L5B','L52','L46','L4H','L4','L5', #10nm conditions
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

        # df.loc['0', 'OUT_DATE'] = df.loc[1,'OUT_DATE']

        return df
    
    def generate_plot_data(self):

        lot_flow = self.lot_flow
        commit = self.commit
        total_act = lot_flow['CUM_ACTIVITY'].max()
        days_remaining = (self.commit - pd.Timestamp.now()).days

        plot_data = lot_flow.groupby(['LAYER'])[['CUM_ACTIVITY','OUT_DATE','EXEC_SEQ']].max().reset_index()
        plot_data = plot_data.sort_values(by='EXEC_SEQ', ascending=True).reset_index(drop=True)

        plot_data['ACT'] = plot_data['CUM_ACTIVITY'].diff()

        plot_data['ACTUAL'] = plot_data['OUT_DATE']

        reverse_plot_data = plot_data[::-1]
        last_valid_index = reverse_plot_data['OUT_DATE'].first_valid_index()

        current_act = plot_data.loc[last_valid_index,'CUM_ACTIVITY'] if last_valid_index is not None else None

        # wt_req = (total_act - current_act)/days_remaining

        plan_release = plot_data.loc[1,'OUT_DATE']
        if pd.isna(plan_release):
            plan_release = pd.Timestamp.now()

        plan_first_act = plot_data.loc[1,'CUM_ACTIVITY']

        plan_total_days = (commit - plan_release).days
        plan_wt_req = (total_act - plan_first_act)/plan_total_days
        plan_base_start = plan_release + pd.Timedelta(days=plan_first_act/plan_wt_req)

        plot_data['TREND'] = plot_data['OUT_DATE']

        for idx in plot_data.index:
            plot_data.loc[idx,'PLAN'] = plan_base_start + pd.Timedelta(days=plot_data.loc[idx,'CUM_ACTIVITY']/plan_wt_req)

            if pd.isna(plot_data.loc[idx,'TREND']):
                plot_data.loc[idx,'TREND'] = plot_data.loc[idx-1,'TREND']+pd.Timedelta(days=plot_data.loc[idx,'ACT']/plan_wt_req)


        self.plot_data = plot_data.drop(columns=['EXEC_SEQ','CUM_ACTIVITY','OUT_DATE'])        
                
