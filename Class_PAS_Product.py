
# from Class_PAS_Lot import Lot
import os
import pandas as pd
import numpy as np
from datetime import timedelta

# from PAS_Graph_Class import PASPlot


def get_layer(row):

    value = row['OPER_SHORT_DESC']

    if row['EXEC_SEQ'] == 1:
        return "START"
    if value[:1] == "Z":
        return "SHIP"
    
    cond_list = [' ','#',
                    'L58','L5B','L52','L46','L4H','L4','L5', #10nm conditions
                    'L6', # 3nm conditions
                    'L8xr','L8rb','L8rf','L8HDb','L8c','L8s','L8b','L86','L81','L8d','L8' #18A conditions
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

def check_act(value):
    if '*' in value:
        return 1
    else:
        return 0
            
def cleanup_LotFlow(df):
    # df = df.sort_values(by='EXEC_SEQ', ascending=True)
    # df['ACTIVITY'] = df['OPER_SHORT_DESC'].apply(lambda x: check_act(x))
    # df['CUM_ACTIVITY'] = df['ACTIVITY'].cumsum()


    df = df[(df['EXEC_SEQ']==1) |  
        (df['OPERATION']=='9781') |
        (((df['AREA']=='LITHO') | (df['AREA']=='FBE'))  & (
            # These are the modules for 18A
            (df['MODULE'] == "LI-SAVli") | 
            (df['MODULE'] == "LI-SAYli") | 
            (df['MODULE'] == "LI-SBHcu") | 
            (df['MODULE'] == "LI-SBLcu") | 
            (df['MODULE'] == "LI-SNEli") | 
            (df['MODULE'] == "LI-SNYli") |
            (df['MODULE'] == "FBE-LITHO") |
            # These are the modules for 3nm
            (df['MODULE'] == "LI-SAYli") |
            (df['MODULE'] == "LI-SNEli") |
            (df['MODULE'] == "LI-SAVli") |
            (df['MODULE'] == "LI-SNYli") |
            (df['MODULE'] == "LI-SBHcu") |
            (df['MODULE'] == "LI-BE-193") |
            (df['MODULE'] == "LI-SBLcu") |
            (df['MODULE'] == "LI-BE-SED") |
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

    df['LAYER'] = df.apply(lambda row: get_layer(row), axis=1)

    df['OUT_DATE'] = pd.to_datetime(df['OUT_DATE'], errors='coerce')     

    # df.loc['0', 'OUT_DATE'] = df.loc[1,'OUT_DATE']

    # df = df.sort_values(by='OUT_DATE')
    df = df.drop_duplicates(subset=['LAYER'], keep='last')

    return df


class Lot:
    def __init__(self, npi_name, lot_number, lot_title, fab_prod, ret_prod, commit, base_flow, dataengine, debug_flag=False):
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
            
            self.lot_redwing = dataengine.extract_redwing(self.lot_number)
            # self.lot_flow = cleanup_LotFlow(self.lot_flow_raw)
            self.lot_flow = pd.merge(base_flow, self.lot_flow_raw, on='OPERATION', how='inner')
            self.lot_flow['OUT_DATE'] = pd.to_datetime(self.lot_flow['OUT_DATE'], errors='coerce')     

            self.lot_flow['TREND_DATE'] = self.lot_flow['OUT_DATE'].copy()

            for i in range(len(self.lot_flow)):
                if pd.isna(self.lot_flow.loc[i,'OUT_DATE']) and i>0:
                    previous_trend_date = self.lot_flow.loc[self.lot_flow.index[i-1], 'TREND_DATE']
                    ct_hours = self.lot_flow.loc[self.lot_flow.index[i], 'CT']
                    self.lot_flow.loc[self.lot_flow.index[i], 'TREND_DATE'] = previous_trend_date + timedelta(hours=ct_hours)
                    
            # self.lot_flow = self.lot_flow.sort_values(by='OUT_DATE')
            self.lot_flow = self.lot_flow.drop_duplicates(subset=['LAYER'], keep='last')
            self.TREND_DATE = self.lot_flow['TREND_DATE'].max()
            # self.generate_plot_data()
        except Exception as e:
            print(f"Error extracting data for lot {self.lot_number}: {e}")
            self.lot_flow = None
            self.lot_redwing = None
            raise

        
        if self.debug_flag:
            self.lot_flow_raw.to_csv(f"debug/lot_flow_{lot_number}_raw.csv", index=False)
            # self.lot_flow.to_csv(f"debug/lot_flow_{lot_number}.csv", index=False)
            # self.lot_redwing.to_csv(f"debug/lot_redwing_{lot_number}_raw.csv", index=False)
    


    
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
                


class Product:
    def __init__(self, npi_name, prod_details, dataengine, ret_version=None, lots=None, debug_flag=False):
        
        self.npi_name = npi_name
        self.fab_name = prod_details['FAB_PROD']
        self.ret_name = prod_details['RET_PROD']
        self.commit = prod_details['COMMIT']
        self.technology = prod_details['Technology']
        
        self.dataengine = dataengine
        self.debug_flag = debug_flag

        if self.debug_flag:
            os.makedirs("debug", exist_ok=True)

        temp = None
        if ret_version is not None:
            temp = ret_version[ret_version['RET_PROD'] == self.ret_name]
            if temp.empty:
                temp = None
        self.ret_version = temp
            
        self.reticle_data = self.dataengine.extract_reticleData(self.fab_name, self.ret_name)
        if self.debug_flag: self.reticle_data.to_csv(f"debug/{self.fab_name}_reticle_data_raw.csv", index=False)
        self.RetData = self.reticle_manipulation()

        
        if self.debug_flag: self.RetData.to_csv(f"debug/{self.fab_name}_reticle_data.csv", index=False)


        
        self.lots = []
        if lots:
            for lot_number, lot_title in lots.items():
                self.add_lot(lot_number, lot_title)

    def add_lot(self, lot_number, lot_title):

        first_lot = False

        if len(self.lots) == 0:

            first_lot = True
                # def extract_BaseFlow(self, lot, npi, fab_prod, ret_prod,process=1278):
            df = self.dataengine.extract_BaseFlow(lot=lot_number, npi=self.npi_name, fab_prod=self.fab_name, ret_prod=self.ret_name, process=self.technology)

            if self.debug_flag: df.to_csv(f"debug/{self.fab_name}_base_flow_raw.csv", index=False)

            self.plan_flow = self.baseline_flow(df)
            self.plan_flow['CT'] = self.plan_flow['CT_for_commit'].diff()
            
            if self.debug_flag: self.plan_flow.to_csv(f"debug/{self.fab_name}_plan_flow.csv", index=False)
            
            self.base_flow = self.plan_flow[['ORDER','OPERATION','LAYER','CT']]
            
            if self.debug_flag: self.base_flow.to_csv(f"debug/{self.fab_name}_base_flow.csv", index=False)
            
            # self.RetPlotData = self.RetDataOrder()
            self.RetPlotData = pd.merge(self.base_flow[['ORDER','LAYER']], self.RetData, how='left', on=['LAYER'])


        lot = Lot(npi_name=self.npi_name, 
                  lot_number=lot_number, 
                  lot_title=lot_title, 
                  fab_prod=self.fab_name, 
                  ret_prod=self.ret_name, 
                  commit=self.commit, 
                  base_flow=self.base_flow, 
                  dataengine=self.dataengine, 
                  debug_flag=self.debug_flag)
        self.lots.append(lot)


    def RetDataOrder(self):
        df = pd.merge(self.RetPlotData, self.base_flow[['LAYER','EXEC_SEQ']], how='left', on=['LAYER'])
        df = df.sort_values(by='EXEC_SEQ', ascending=True).reset_index()
        return df

    def cleanRetCol(self, dt):
        try:
            dt = pd.to_datetime(dt)
            return dt
        except ValueError:
            dt = dt.str.replace('~','')
            dt = pd.to_datetime(dt)
            return dt

    def convert_to_days(self, col,min_val):
        col = col - min_val
        col = col.apply(lambda x: x.days if x>pd.Timedelta(days=0) else 0)
        return col
    
    def cleanupCommit(self, row):
        cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=180)
        
        if row['IMO_TREND'] < cutoff_date:
            return row['IMO_COMMIT']
        else:
            return row['IMO_TREND']


    def reticle_version_handling(self, df):
        """
        Uses the reticle data version input to overide and select specific reticles to use in tracking
        """
        # df['VER'] = df['RET_PROD'].str[:3]
        df['VER'] = df['TITLE'].str[:3]
        merged_data = df.merge(self.ret_version, how='left', on=['RET_PROD', 'LAYER'])
        df = merged_data[(merged_data['VER'] == merged_data['VERSION']) | merged_data['VERSION'].isna()]
        df.drop(columns=['VER','VERSION'], inplace=True)
        
        return df

    def reticle_manipulation(self):
        """
        Uses the reticle data version input to overide and select specific reticles to use in tracking
        """
        RetData = self.reticle_data.copy()

        col_list =['TAPEIN_TREND','ITO_TREND','ITO_COMMIT','IMO_TREND','IMO_COMMIT','SHIPDATE','FAB_REQUIREDDATE']
        for col in col_list:
            RetData[col] = self.cleanRetCol(RetData[col])

        if self.ret_version is not None:
            RetData = self.reticle_version_handling(RetData)

        cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=180)
        RetData = RetData[RetData['IMO_COMMIT']>=cutoff_date]
        RetData['IMO_TREND'] = RetData.apply(lambda row: self.cleanupCommit(row), axis =1)

        indexNames = RetData[RetData['IMO_STATUS']=='Rejected'].index
        RetData.drop(indexNames, inplace=True)

        indexNames = RetData[RetData['IMO_STATUS']=='Processing - Hold With Waiver'].index
        RetData.drop(indexNames, inplace=True)

        RetData['RetRev'] = RetData['TITLE'].str.slice(0, 3) 
        RetData['RetNum'] = RetData['TITLE'].str[3:4]

        # Filter out rows where IMO_STATUS is not 'Shipped' if there is at least one 'Shipped' status for the same LAYER
        shipped_data = RetData[RetData['IMO_STATUS'] == 'Shipped'][['FAB_PROD', 'LAYER']].drop_duplicates()
        RetData = RetData[~((RetData['IMO_STATUS'] != 'Shipped') & (RetData['LAYER'].isin(shipped_data['LAYER'])) & (RetData['RET_PROD'].isin(shipped_data['FAB_PROD'])))]

        # Get the lowest date in the IMO_COMMIT column for each layer
        RetData = RetData.sort_values(by='IMO_COMMIT').drop_duplicates(subset=['LAYER'], keep='first')

        RetData['FAB_RECEIVED'] = RetData['FIRSTARRIV']

        # Filter out rows where SHIP is not the earliest for the same LAYER
        # RetData = RetData[~((RetData['SHIPDATE'].isna()) & (RetData['IMO_COMMIT'] < pd.Timestamp.now()))]

        RetData = pd.pivot_table(RetData,index=['LAYER'], values=['TAPEIN_TREND','ITO_TREND','FAB_REQUIREDDATE','IMO_TREND','SHIPDATE','FAB_RECEIVED'], aggfunc=np.min).reset_index()
        RetData['TI'] = RetData['TAPEIN_TREND']
        RetData['TO'] = RetData['ITO_TREND']# - RetData['TI']
        RetData['SHIP'] = RetData['SHIPDATE']# - RetData['TI']
        RetData['ESD'] = RetData['IMO_TREND']# - RetData['TI']
        RetData['FRD'] = RetData['FAB_REQUIREDDATE']# - RetData['TI']

        RetData.loc[RetData['SHIP'].notna(), 'ESD'] = pd.NaT
        RetData.loc[RetData['FAB_RECEIVED'].notna(), 'ESD'] = pd.NaT
        RetData.loc[RetData['FAB_RECEIVED'].notna(), 'SHIP'] = pd.NaT


        #RetData['SHIP'] = RetData['SHIP'].fillna(pd.Timedelta(days=0))
        #RetData['ESD'] = RetData['ESD'].fillna(pd.Timedelta(days=0))
        RetData = RetData[['LAYER', 'TI', 'TO', 'ESD', 'SHIP', 'FAB_RECEIVED','FRD']]   

        return RetData     
    

    def baseline_flow(self, lot_flow):
        df = lot_flow.copy()
        
        df = cleanup_LotFlow(df)
        df = df.reset_index(drop=True)
        df['ORDER'] = df.index+1

        cum_act = df['CUM_ACTIVITY'].max()
        start_date = df['OUT_DATE'].min()
        cum_cycle_time = df['CUM_CYCLE_TIME'].max()/24
        process_days = (self.commit-start_date).days
        wt = cum_act / process_days
        wipt_sql = cum_act / cum_cycle_time
        wipt_ratio = wipt_sql / wt
        print("Cumulative Activity:", cum_act)
        print("Process Days:", process_days)
        print("WIP Turns required:", wt)
        print("Cumulative Cycle Time (hours):", cum_cycle_time)
        print("WIP Turns (SQL):", wipt_sql)
        print("WIP Turns Ratio:", wipt_ratio)
        print("Commit Date:", self.commit)
        print("Start Date:", start_date)

        df['CT_for_commit'] = df['CUM_CYCLE_TIME']*wipt_ratio
        df.loc[0, 'CT_for_commit'] = 0
        df['CT_for_commit'] = df['CT_for_commit'].fillna(0)

        df['PLAN'] = start_date + pd.to_timedelta(df['CT_for_commit'], unit='h')

        df = df[['ORDER','OPERATION','LAYER','PLAN','CT_for_commit']]

        return df

    def build_plot_data(self):
        base_flow = self.base_flow.copy()
        ReticleData = self.RetData.copy()

        plotdata = pd.merge(self.RetPlotData, self.plan_flow[['ORDER','LAYER','PLAN']], on=['ORDER','LAYER'], how='left')
        
        # plotdata = pd.merge(base_flow[['LAYER','EXEC_SEQ']], ReticleData, how='left', on=['LAYER'])
        
        
        plotdata['Estimated Ship Date'] = plotdata['ESD']
        plotdata['Estimated Ship Date'] = plotdata['ESD'].fillna(plotdata['SHIP'])
        
        plotdata['Fab Required Date'] = plotdata['FRD']
        

        for lot in self.lots:
            lot_plot_data = lot.lot_flow
            lot_title = lot.lot_title
            if lot_title.upper() == 'LEAD LOT':
                lot_plot_data['Lead Lot TREND'] = lot_plot_data['TREND_DATE']
                plotdata = pd.merge(plotdata, lot_plot_data[['ORDER', 'Lead Lot TREND']], on='ORDER', how='left')

            lot_plot_data[f'{lot_title} ACTUAL'] = lot_plot_data['OUT_DATE']

            plotdata = pd.merge(plotdata, lot_plot_data[['ORDER', f'{lot_title} ACTUAL']], on='ORDER', how='left')

        max_line = plotdata['PLAN'].max()
        min_line = plotdata['PLAN'].min()
        min_TI = plotdata['TI'].min()

        timeDelta = min_line-min_TI

        # print(f"Max Line: {max_line}, Min Line: {min_line}, Min TI: {min_TI}, Time Delta: {timeDelta}\n")

        # Normalize dates to round down to the nearest day
        ymin_date = (min_line - pd.Timedelta(days=30)).normalize()
        ymax_date = (max_line + pd.Timedelta(days=7)).normalize()

        # print(f"Y Min Date: {ymin_date}, Y Max Date: {ymax_date}\n")

        # Calculate the difference in days
        difference_days = (ymax_date - ymin_date).days
        # print(f"Difference in days: {difference_days} days\n")

        # Round up the difference to the nearest multiple of 7
        rounded_difference = np.ceil(difference_days / 7) * 7
        # print(f"Rounded difference: {rounded_difference} days\n")

        ymax_date = ymin_date + pd.Timedelta(days=rounded_difference)
        ymin_val = 0
        ymax_val = rounded_difference

        # print(f"Final Y Min Date: {ymin_date}, Final Y Max Date: {ymax_date}\n")


        # print(f"ymin_date: {ymin_date}")
        # print(f'ymin_val: {ymin_val}')
        # print(f"ymax_date: {ymax_date}")
        # print(f'ymax_val: {ymax_val}')

        bar_columns = ['TI', 'TO', 'ESD', 'SHIP', 'FAB_RECEIVED', 'FRD']    
        plotdata['TI'] = (plotdata['TI'] - ymin_date).dt.days

        plotdata['TI'] = plotdata['TI'].fillna(0)
        plotdata['TI'] = plotdata['TI'].apply(lambda x: max(x, 0))        

        plotdata['TO'] = (plotdata['TO'] - ymin_date).dt.days  - plotdata['TI']
        plotdata['FRD'] = (plotdata['FRD'] - ymin_date).dt.days
        plotdata['ESD'] = (plotdata['ESD'] - ymin_date).dt.days  - plotdata['TI']
        plotdata['SHIP'] = (plotdata['SHIP'] - ymin_date).dt.days - plotdata['TI']
        plotdata['FAB_RECEIVED'] = (plotdata['FAB_RECEIVED'] - ymin_date).dt.days - plotdata['TI']

        for col in bar_columns:
            plotdata[col] = plotdata[col].fillna(0)
            
            plotdata[col] = plotdata[col].apply(lambda x: max(x, 0))

        self.plot_data = plotdata.copy()
        self.ymin_date = ymin_date
        self.ymax_date = ymax_date
        self.ymin_val = ymin_val
        self.ymax_val = ymax_val
        

    def debug_dump(self):
        """
        Dump debug data to CSV files.
        """
        self.reticle_data.to_csv(f"debug/{self.fab_name}_reticle_data.csv", index=False)
        for lot in self.lots:
            lot.lot_flow.to_csv(f"debug/{lot.lot_number}_lot_flow.csv", index=False)
            lot.plot_data.to_csv(f"debug/{lot.lot_number}_plot_data.csv", index=False)
