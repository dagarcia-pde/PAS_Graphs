from Class_PAS_Lot import Lot
# from PAS_Graph_Class import PASPlot

class Product:
    def __init__(self, npi_name, fab_name, ret_name, dataengine, lots=None, debug_flag=False):
        self.npi_name = npi_name
        self.fab_name = fab_name
        self.ret_name = ret_name
        self.dataengine = dataengine
        self.debug_flag = debug_flag

        self.reticle_data = self.dataengine.extract_reticleData(ret_name)
        if self.debug_flag: self.reticle_data.to_csv(f"debug/reticle_data_raw.csv", index=False)
        
        self.lots = []
        if lots:
            for lot_number, lot_title in lots.items():
                self.add_lot(lot_number, lot_title)

    def add_lot(self, lot_number, lot_title):
        lot = Lot(self.npi_name, lot_number, lot_title, self.fab_name, self.ret_name, self.dataengine)
        self.lots.append(lot)
        
        if self.debug_flag:
            lot.lot_flow.to_csv(f"debug/lot_flow_{lot_number}_raw.csv", index=False)
            lot.lot_redwing.to_csv(f"debug/lot_redwing_{lot_number}_raw.csv", index=False)
    
        