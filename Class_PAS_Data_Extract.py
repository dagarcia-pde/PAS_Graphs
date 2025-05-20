import PyUber
import pandas as pd

class PASDataEngine:
    def __init__(self, debug_flag=False, xeus_source='F32_PROD_XEUS',imo_source='D1D_PROD_XEUS_CENTRAL',imo_fab_list="'F32','F42','F12','F22','F52'"):
        self.debug_flag = debug_flag
        self.xeus_source = xeus_source
        self.imo_source = imo_source
        self.imo_fab_list = imo_fab_list
    
    def extract_lotflow(self, lot, npi, title, fab_prod, ret_prod):
        
        with PyUber.connect(datasource=self.xeus_source) as conn:
        
            query = f'''
                SELECT 
                        '{npi}' AS NPI
                        ,'{title}' AS TITLE
                        ,'{fab_prod}' AS FAB_PROD
                        ,'{ret_prod}' AS RET_PROD
                        ,flf.product AS product
                        ,flf.lot AS lot
                        ,flf.exec_seq AS exec_seq
                        ,flf.operation AS operation
                        ,flf.oper_short_desc AS oper_short_desc
                        ,o.oper_long_desc AS oper_long_desc
                        ,To_Char(flf.out_date,'yyyy-mm-dd hh24:mi:ss') AS out_date
                        ,flf.lot_priority_movein AS lot_priority_movein
                        ,o.area AS area
                        ,o.module AS module
                FROM 
                    F_Lot_Flow flf
                    CROSS JOIN F_Facility f
                    INNER JOIN F_Operation O ON o.operation=flf.operation AND o.facility = f.facility AND o.latest_version = 'Y'
                WHERE
                    flf.history_deleted_flag = 'N' 
                    AND flf.lot = '{lot}'
                ORDER BY flf.exec_seq 
            '''

            df = pd.read_sql(query, conn)

        return df
    
    def extract_reticleData(self, fab_prod, ret_name):
        
        with PyUber.connect(datasource= self.imo_source) as conn:

            # retProdList = retProds['RET_PROD'].unique()

            # Construct the WHERE clause dynamically
            # where_clause = ' OR '.join([f"z0.product LIKE '{ret_name}'" for value in retProdList])

            query = f'''
                SELECT 
                    z0.commonname AS common_name
                    ,z0.title AS title
                    ,'{fab_prod}' AS FAB_PROD
                    ,z0.product AS RET_PROD
                    ,z0.rev AS rev
                    ,z0.layer AS layer
                    ,z0.step AS step
                    ,z0.platetype AS plate_type
                    ,z0.tapeintrend AS tapein_trend
                    ,z0.itotrend AS ito_trend
                    ,To_Char(z0.itocommit,'yyyy-mm-dd hh24:mi:ss') AS ito_commit
                    ,z0.itostatus AS ito_status
                    ,z0.retfabrev AS ret_fabrev
                    ,z0.fab AS fab
                    ,z0.barcode AS barcode
                    ,z0.imotrend AS imo_trend
                    ,To_Char(z0.imocommit,'yyyy-mm-dd hh24:mi:ss') AS imo_commit
                    ,z0.imostatus AS imo_status
                    ,To_Char(z0.shipdate,'yyyy-mm-dd hh24:mi:ss') AS shipdate
                    ,z0.fabrequireddate AS fab_requireddate
                    ,z0.imodotprocess AS imo_dotprocess
                    ,z0.imoishot AS imo_ishot
                    ,z0.technology AS technology
                    ,z0.toengcontact AS to_engcontact
                    ,z0.dbnames AS dbnames
                    ,To_Char(z0.last_updated_timestamp,'yyyy-mm-dd hh24:mi:ss') AS last_updated_timestamp
                FROM 
                    F_IMO_TRIFECTA_DASHBOARD z0
                WHERE
                    1=1
                    --AND z0.last_updated_timestamp >= SYSDATE - 180 
                    AND z0.fab In ({self.imo_fab_list})     
                    AND (
                        z0.product LIKE '{ret_name}'
                    )
            '''
            df = pd.read_sql(query, conn)

            # df = pd.merge(df,retProds, on='RET_PROD', how='inner')
            # cursor.execute(query)

        # self.reticleData = df
        return df
    
    def extract_redwing(self, lot):
        with PyUber.connect(datasource= self.xeus_source) as conn:
        # cursor = conn.cursor()

            query = f'''
                SELECT DISTINCT
                    *
                FROM
                    F_RW_LOT_SCENARIO LS
                WHERE
                    LS.lot = '{lot}' 
                    AND LS.ADDED_BY <> 'ATC-AUTOLOAD'
                    AND LS.COMMITOUT is not null           '''
            df = pd.read_sql(query, conn)
        # cursor.execute(query)
        # self.redwing = df    
        return df
    
