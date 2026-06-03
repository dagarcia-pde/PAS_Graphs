import PyUber
import pandas as pd

class PASDataEngine:
    def __init__(self, debug_flag=False, xeus_source='F32_PROD_XEUS',imo_source='D1D_PROD_XEUS_CENTRAL',imo_fab_list="'F32','F42','F12','F22','F52'"):
        self.debug_flag = debug_flag
        self.xeus_source = xeus_source
        self.imo_source = imo_source
        self.imo_fab_list = imo_fab_list
        self.reticle_arrival_source = f'{self.xeus_source[:3]}S'
    
    def extract_BaseFlow(self, lot, npi, fab_prod, ret_prod,process=1278):

        with PyUber.connect(datasource=self.xeus_source) as conn:
            query = f'''
                Select
                    a.LOT
                    ,a.OPERATION
                    ,a.OPER_SHORT_DESC
                    ,a.OPER_LONG_DESC
                    ,a.AREA
                    ,a.MODULE                
                    ,a.EXEC_SEQ
                    ,a.OUT_DATE
                    ,SUM(a.PLAN_CYCLE_TIME) OVER (ORDER BY a.EXEC_SEQ) AS CUM_CYCLE_TIME
                    ,SUM(a.Activity) OVER (ORDER BY a.EXEC_SEQ) AS CUM_ACTIVITY
                FROM
                    (SELECT DISTINCT
                        lf.LOT
                        ,lf.OPERATION
                        ,lf.OPER_SHORT_DESC
                        ,o.OPER_LONG_DESC
                        ,o.area AS AREA
                        ,o.module AS MODULE                
                        ,lf.EXEC_SEQ
                        ,lf.out_date as OUT_DATE
                        ,ct.PLAN_CYCLE_TIME
                        ,CASE WHEN lf.OPER_SHORT_DESC like '%*%' THEN 1 ELSE 0 END AS Activity
                    FROM
                        F_LOT_FLOW lf
                        LEFT JOIN F_Operation O
                            ON lf.OPERATION = O.OPERATION     
                                AND O.LATEST_VERSION = 'Y'
                        LEFT JOIN
                            (SELECT Distinct
                                LO.OPERATION,
                                LO.PT_PERCENTILE_30 as PLAN_CYCLE_TIME
                            FROM
                                F_LOT_OPER_CYCLETIME LO 
                            WHERE
                                LO.LOT_PROCESS = {process}) as ct
                            ON lf.OPERATION = ct.OPERATION                        
                    WHERE
                        lf.LOT = '{lot}'
                        AND lf.REWORK_FROM_EXEC_SEQ is NULL

                    ORDER By
                        lf.EXEC_SEQ) as a
                ORDER BY a.EXEC_SEQ
            '''
            df = pd.read_sql(query, conn)

        return df

    def extract_retArrival(self, fab_prod, ret_name):
        
        with PyUber.connect(datasource=self.xeus_source) as conn:
        
            query = f'''
                SELECT  
                    substr(RETICLE,1,12) as RETICLE_ID,  min(TXN_DATE) as FirstArriv 
                FROM
                    {self.reticle_arrival_source}.F_RETICLEHIST
                WHERE RETICLE_PRODUCT in ('{ret_name}')
                    and TRANSACTION like 'RetSSRec%' 
                    and TXN_DATE  > current_date -360        
                group by
                    substr(RETICLE,1,12)
            '''

            df = pd.read_sql(query, conn)

        return df
       
    def extract_lotflow(self, lot, npi, title, fab_prod, ret_prod):
        
        with PyUber.connect(datasource=self.xeus_source) as conn:
        
            query = f'''
                SELECT DISTINCT
                        flf.lot AS LOT
                        ,flf.operation AS OPERATION
                        ,To_Char(flf.out_date,'yyyy-mm-dd hh24:mi:ss') AS OUT_DATE
                FROM 
                    F_Lot_Flow flf
                WHERE
                    flf.history_deleted_flag = 'N' 
                    AND flf.lot = '{lot}'
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
                    ,z0.IMOBARCODE
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

            df2 = self.extract_retArrival(fab_prod, ret_name)

            df['RETICLE_ID'] = df['IMOBARCODE'].str[:12]
            ret = pd.merge(df, df2, on='RETICLE_ID', how='left')

            # df = pd.merge(df,retProds, on='RET_PROD', how='inner')
            # cursor.execute(query)

        # self.reticleData = df
        return ret
    
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
    
