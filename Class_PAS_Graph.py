import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import re
import os

class PASPlot:
    def __init__(self,prod,output_dir,fussion_dir):
    
        self.npi_name = prod.npi_name
        self.output_dir = output_dir
        self.fussion_dir = fussion_dir
        self.trend_colors = ["#1E2EB8", "#FF5662", "#00C7FD", "#00377C", "#A0EBFF", "#9C3EF9"]
        self.bar_colors = ['#001E50',"#1E2EB8", '#FF5662', '#00C7FD', "#02B108"]
    
        self.plotdata = prod.plot_data
        self.ymin_date = prod.ymin_date
        self.ymax_date = prod.ymax_date
        self.ymin_val = prod.ymin_val
        self.ymax_val = prod.ymax_val
        self.commit_date = prod.commit
        
        self.lots = []
        
        for n in range(len(prod.lots)):
            self.lots.append(prod.lots[n].lot_title)

    def sanitize_filename(self, title):
        """
        Sanitizes a string to be safe for use as a filename by:
        - Replacing spaces with underscores
        - Removing or replacing invalid characters
        """
        # Replace spaces with underscores
        title = title.replace(' ', '_')
        
        # Remove or replace invalid characters
        # The regex below will remove any characters that are not alphanumeric, underscores, or dots
        title = re.sub(r'[^\w\.]', '', title)
        
        return title
        
        
    def make_plot(self):
        

        plotdata = self.plotdata
        ymin_date = self.ymin_date
        ymax_date = self.ymax_date
        ymin_val = self.ymin_val
        ymax_val = self.ymax_val
        commit_date = self.commit_date
        trend_date = plotdata['Lead Lot TREND'].max() 
        
        # print(f"commit_date: {commit_date}")
        # print(f"trend_date: {trend_date}")       
        
        fig, ax1 = plt.subplots(figsize=(12, 8))

        ax1.plot(plotdata['LAYER'], plotdata['PLAN'],color='black', label='NPI PLAN', linewidth=2, linestyle='--')

        # ax1.plot(plotdata['LAYER'], plotdata['Lead Lot TREND'],color='blue', label='Lead Lot TREND', linewidth=2, linestyle='--')  
        for idx, lot in enumerate(self.lots):
            color = self.trend_colors[idx % len(self.trend_colors)]
            ax1.plot(plotdata['LAYER'], plotdata[f'{lot} ACTUAL'], color=color, label=f'{lot} ACTUAL', linewidth=2)
        
        
        ax2 = ax1.twinx()

        bar_columns = ['TI', 'TO', 'ESD', 'SHIP','FAB_RECEIVED']

        # TrendLineColor = "#09FF00FF"
        TrendLineColor = "#FF0011"
        if commit_date >= trend_date:
            TrendLineColor = "#09FF00FF"

        ax1.axhline(y=commit_date, color=TrendLineColor, linestyle='-', linewidth=2)

        plotdata['BOTTOM'] = 0
        for idx, bar in enumerate(bar_columns):

            ax2.bar(plotdata['LAYER'], plotdata[bar], bottom=plotdata['BOTTOM'], label=bar, color=self.bar_colors[idx], alpha=0.8)
            plotdata['BOTTOM'] = plotdata[bar] + plotdata['BOTTOM']


        for bar,frd in zip(plt.gca().patches,plotdata['FRD']):
            x = bar.get_x() + bar.get_width() / 2
            ax2.hlines(frd, x-bar.get_width()/2, x+bar.get_width()/2, color='grey', linewidth=1)

        ax1.set_ylim(ymin_date, ymax_date)
        ax2.set_ylim(ymin_val, ymax_val)
        
        # Set the background color of the axes (the plot area) to white
        ax1.set_facecolor('white')
        ax2.set_facecolor('white')
        fig.patch.set_facecolor('white')

        # Add a text box in the upper left
        textstr = f'Commit Date: {commit_date.strftime("%m-%d-%Y")}'
        textstr += f'\nTrend Date: {trend_date.strftime("%m-%d-%Y")}'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax1.text(0.05, 0.85, textstr, transform=ax1.transAxes, fontsize=12,
                    verticalalignment='top', horizontalalignment='left', bbox=props)


        ax1.set_xticklabels(plotdata['LAYER'], rotation=90, fontsize=8)
        ax2.set_yticklabels([])
        ax1.margins(x=0)
        ax1.yaxis.grid(True)
        ax1.yaxis.set_major_locator(mdates.DayLocator(interval=14)) 
        ax1.yaxis.set_major_formatter(mdates.DateFormatter('%m-%d-%Y'))
        
        handles1, labels1 = ax1.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        frd_line = Line2D([0], [0], linestyle='-', color='grey', linewidth=1, label='FRD')

        handles = handles1 + handles2 + [frd_line]
        labels = labels1 + labels2 + ['FRD']
        plt.legend(handles, labels, loc='upper left', bbox_to_anchor=(1.01,1),borderaxespad=0.)
        
        ax1.set_title(f'{self.npi_name} NPI', color='#001E50', fontsize=16)
        # Show plot
        plt.tight_layout()
        
        filename = self.sanitize_filename(self.npi_name+'_NPI')+'.png'
        
        # Combine them into a full file path
        full_path = os.path.join(self.output_dir, filename)        
        fussion_path = os.path.join(self.fussion_dir, filename)        
        
        fig.savefig(full_path)
        fig.savefig(fussion_path)
        
        plt.close(fig)