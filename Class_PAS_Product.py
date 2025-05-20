
from Class_PAS_Lot import Lot
import pandas as pd
import numpy as np
# from PAS_Graph_Class import PASPlot

class Product:
    def __init__(self, npi_name, prod_details, dataengine, ret_version=None, lots=None, debug_flag=False):
        
        self.npi_name = npi_name
        self.fab_name = prod_details['FAB_PROD']
        self.ret_name = prod_details['RET_PROD']
        self.commit = prod_details['COMMIT']
        
        self.dataengine = dataengine
        self.debug_flag = debug_flag

        temp = None
        if ret_version is not None:
            temp = ret_version[ret_version['RET_PROD'] == self.ret_name]
            if temp.empty:
                temp = None
        self.ret_version = temp
            
        self.reticle_data = self.dataengine.extract_reticleData(self.fab_name, self.ret_name)
        if self.debug_flag: self.reticle_data.to_csv(f"debug/{self.fab_name}_reticle_data_raw.csv", index=False)
        self.RetData = self.reticle_manipulation()
        # self.RetPlotData = self.generate_ret_plot_data()
        if self.debug_flag: self.RetData.to_csv(f"debug/{self.fab_name}_reticle_data.csv", index=False)


        
        self.lots = []
        if lots:
            for lot_number, lot_title in lots.items():
                self.add_lot(lot_number, lot_title)

    def add_lot(self, lot_number, lot_title):
        lot = Lot(self.npi_name, lot_number, lot_title, self.fab_name, self.ret_name, self.commit, self.dataengine, self.debug_flag)
        self.lots.append(lot)

        if len(self.lots) == 1:
            self.base_flow = self.baseline_flow(lot.lot_flow)
            # self.RetPlotData = self.RetDataOrder()

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

        # Filter out rows where SHIP is not the earliest for the same LAYER
        RetData = RetData[~((RetData['SHIPDATE'].isna()) & (RetData['IMO_COMMIT'] < pd.Timestamp.now()))]

        RetData = pd.pivot_table(RetData,index=['LAYER'], values=['TAPEIN_TREND','ITO_TREND','FAB_REQUIREDDATE','IMO_TREND','SHIPDATE'], aggfunc=np.min).reset_index()
        RetData['TI'] = RetData['TAPEIN_TREND']
        RetData['TO'] = RetData['ITO_TREND']# - RetData['TI']
        RetData['SHIP'] = RetData['SHIPDATE']# - RetData['TI']
        RetData['ESD'] = RetData['IMO_TREND']# - RetData['TI']
        RetData['FRD'] = RetData['FAB_REQUIREDDATE']# - RetData['TI']

        RetData.loc[RetData['SHIP'].notna(), 'ESD'] = pd.NaT

        #RetData['SHIP'] = RetData['SHIP'].fillna(pd.Timedelta(days=0))
        #RetData['ESD'] = RetData['ESD'].fillna(pd.Timedelta(days=0))
        RetData = RetData[['LAYER', 'TI', 'TO', 'ESD', 'SHIP', 'FRD']]   

        return RetData     
    
    def baseline_flow(self,lot_flow):
        self.days_remaining = (self.commit - pd.Timestamp.now()).days

        order_flow = lot_flow.pivot_table(index=['NPI','FAB_PROD','LAYER'],values=['EXEC_SEQ','CUM_ACTIVITY'],aggfunc='min')
        order_flow = order_flow.sort_values(by='EXEC_SEQ', ascending=True).reset_index()

        self.total_act = order_flow['CUM_ACTIVITY'].max()

        order_flow['ACT'] = order_flow['CUM_ACTIVITY'].diff()

        return order_flow


    def build_plot_data(self):
        base_flow = self.base_flow.copy()
        ReticleData = self.RetData.copy()
        plotdata = pd.merge(base_flow[['LAYER','EXEC_SEQ']], ReticleData, how='left', on=['LAYER'])

        # plotdata['TI'] = plotdata['TI'].fillna(plotdata['TI'].min())


        # for col in columns_to_fill:
        #     plotdata[col] = plotdata[col].fillna(0)  # Fill NaN with 0
        #     plotdata[col] = pd.to_timedelta(plotdata[col], unit='D')  # Convert to Timedelta



        for n in range(len(self.lots)):
            lot_plot_data = self.lots[n].plot_data.copy()
            lot_title = self.lots[n].lot_title
            
            lot_plot_data['NPI PLAN'] = lot_plot_data['PLAN']
            lot_plot_data[f'{lot_title} TREND'] = lot_plot_data['TREND']
            lot_plot_data[f'{lot_title} ACTUAL'] = lot_plot_data['ACTUAL']

            lot_plot_data = lot_plot_data[['LAYER', 'NPI PLAN', f'{lot_title} TREND', f'{lot_title} ACTUAL']]

            if n > 0:
                lot_plot_data = lot_plot_data[['LAYER', f'{lot_title} TREND', f'{lot_title} ACTUAL']]
                

            plotdata = pd.merge(plotdata, lot_plot_data, how='left', on=['LAYER'])
        
        trend_columns = [col for col in plotdata.columns if col.endswith('TREND')]
        trend_columns
        max_line = max(plotdata[trend_columns].max())
        min_line = min(plotdata[trend_columns].min())

        min_TI = plotdata['TI'].min()

        timeDelta = min_line - min_TI

        # Normalize dates to round down to the nearest day
        ymin_date = (min_line - pd.Timedelta(days=30)).normalize()
        ymax_date = (max_line + pd.Timedelta(days=7)).normalize()

        # Calculate the difference in days
        difference_days = (ymax_date - ymin_date).days
        print(f"Difference in days: {difference_days} days")

        # Round up the difference to the nearest multiple of 7
        rounded_difference = np.ceil(difference_days / 7) * 7
        print(f"Rounded difference: {rounded_difference} days")

        ymax_date = ymin_date + pd.Timedelta(days=rounded_difference)
        ymin_val = 0
        ymax_val = rounded_difference


        print(f"ymin_date: {ymin_date}")
        print(f'ymin_val: {ymin_val}')
        print(f"ymax_date: {ymax_date}")
        print(f'ymax_val: {ymax_val}')
        # ymin_days = 0
        # ymin_days = ymax
        
        self.plot_data_raw = plotdata.copy()

        bar_columns = ['TI', 'TO', 'ESD', 'SHIP', 'FRD']        
        
        plotdata['SHIP'] = (plotdata['SHIP'] - plotdata['TO']).dt.days
        plotdata['ESD'] = (plotdata['ESD'] - plotdata['TO']).dt.days
        plotdata['TO'] = (plotdata['TO'] - plotdata['TI']).dt.days
        
        
        plotdata['FRD'] = (plotdata['FRD'] - ymin_date).dt.days
        plotdata['TI'] = (plotdata['TI'] - ymin_date).dt.days
        
        for col in bar_columns:
            plotdata[col] = plotdata[col].fillna(0)
            
            plotdata[col] = plotdata[col].apply(lambda x: max(x, 0))
        # for col in bar_columns:
        #     plotdata[col] = self.convert_to_days(plotdata[col],ymin_date)

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
