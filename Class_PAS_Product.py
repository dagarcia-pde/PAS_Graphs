from Class_PAS_Lot import Lot
import pandas as pd
import numpy as np
# from PAS_Graph_Class import PASPlot

class Product:
    def __init__(self, npi_name, fab_name, ret_name, dataengine, ret_version=None, lots=None, debug_flag=False):
        self.npi_name = npi_name
        self.fab_name = fab_name
        self.ret_name = ret_name
        self.dataengine = dataengine
        self.debug_flag = debug_flag

        temp = None
        if ret_version is not None:
            temp = ret_version[ret_version['RET_PROD'] == ret_name]
            if temp.empty:
                temp = None
        self.ret_version = temp
            
        self.reticle_data = self.dataengine.extract_reticleData(ret_name)
        if self.debug_flag: self.reticle_data.to_csv(f"debug/{fab_name}_reticle_data_raw.csv", index=False)
        self.RetData = self.reticle_manipulation()
        if self.debug_flag: self.RetData.to_csv(f"debug/{fab_name}_reticle_data.csv", index=False)


        
        self.lots = []
        if lots:
            for lot_number, lot_title in lots.items():
                self.add_lot(lot_number, lot_title)

    def add_lot(self, lot_number, lot_title):
        lot = Lot(self.npi_name, lot_number, lot_title, self.fab_name, self.ret_name, self.dataengine, self.debug_flag)
        self.lots.append(lot)

    def cleanRetCol(self, dt):
        try:
            dt = pd.to_datetime(dt)
            return dt
        except ValueError:
            dt = dt.str.replace('~','')
            dt = pd.to_datetime(dt)
            return dt
    
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
        df['VER'] = df['RET_PROD'].str[:3]
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
            # shipped_layers = RetData[RetData['IMO_STATUS'] == 'Shipped']['LAYER'].unique()
            # RetData = RetData[~RetData['LAYER'].isin(shipped_layers) | (RetData['IMO_STATUS'] == 'Shipped')]

            # Filter out rows where SHIP is not the earliest for the same LAYER
            # RetData = RetData.loc[RetData.groupby(['FAB_PROD', 'LAYER'])['SHIPDATE'].idxmin()]
            RetData = RetData[~((RetData['SHIPDATE'].isna()) & (RetData['IMO_COMMIT'] < pd.Timestamp.now()))]


            RetData = pd.pivot_table(RetData,index=['FAB_PROD','LAYER'], values=['TAPEIN_TREND','ITO_TREND','FAB_REQUIREDDATE','IMO_TREND','SHIPDATE'], aggfunc=np.min).reset_index()
            return RetData
        else:
            return None