# ---------------------------------------------------------------------------
# LandscapePlots.py
# Version:  ArcGIS Pro / Python 3.6.6 / Anaconda
# Creation Date: 2019-06-05
# Last Edit: 2019-06-18
# Creator:  Kirsten R. Hazler

# Usage notes: This is written to run under the Python environment shipped with ArcGIS Pro. Start by running the executable proenv.bat, then type "idle" in the command window to get the IDLE window running the correct version of Python.
# ---------------------------------------------------------------------------

import arcpy
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
   
def plotGeneralChange(yearList, sumTab, outFig):
   '''Plots land cover area (hectares) over time, for generalized classes of NLCD landcover:
      - Open Water
      - Developed
      - Agriculture
      - Natural
      - Successional
      
      Parameters:
      -yearList: list of years to plot. Must be valid NLCD years.
      -sumTab: summary table with the general categories and the hectare values for each year.
      
      Plot adapted from code here: http://lagrange.univ-lyon1.fr/docs/matplotlib/examples/pylab_examples/broken_axis.html
   '''   
   
   base = 'Area_ha'
   flds = ['Value', 'CoverClass']
   
   for y in yearList:
      fld = base + '_%s'%str(y)
      flds.append(fld)
   
   arr = arcpy.da.TableToNumPyArray (sumTab, flds)
   fldNames = ['Code','Class']
   for y in yearList:
      fldNames.append(str(y))
   fldNames = tuple(fldNames)
   arr.dtype.names = fldNames
   
   wat = list(arr[0])
   wat.append('Blue')
   dev = list(arr[1])
   dev.append('DarkRed')
   agr = list(arr[2])
   agr.append('GoldenRod')
   nat = list(arr[3])
   nat.append('DarkGreen')
   suc = list(arr[4])
   suc.append('LimeGreen')

   fig = plt.figure(figsize=(6,6))
   fig.suptitle('Land Cover in Virginia')
   fig.text(0.04, 0.5, 'Millions of Hectares', va='center', rotation='vertical')
   fig.text(0.5, 0.04, 'Year', va='center')
   gs = GridSpec(16, 1, figure=fig)
   ax1 = fig.add_subplot(gs[0:3, 0])
   ax1.set_xticks([2001, 2006, 2011, 2016])
   y1 = [i for i in numpy.arange(6.4,6.9,0.2)]
   ax1.set_yticks(y1)
   ax1.minorticks_on()
   ax1.xaxis.set_tick_params(which='both', top=False)
   ax1.grid(axis = 'y', linestyle = 'dashed', which = 'major')
   ax2 = fig.add_subplot(gs[4:, 0])
   ax2.set_xticks([2001, 2006, 2011, 2016])
   y2 = [i for i in numpy.arange(0.2,2.4,0.2)]
   ax2.set_yticks(y2)
   ax2.minorticks_on()
   ax2.xaxis.set_tick_params(which='minor', bottom=False)
   ax2.grid(axis = 'y', linestyle = 'dashed', which = 'major')
   
   # hide the spines between ax and ax2
   ax1.spines['bottom'].set_visible(False)
   ax2.spines['top'].set_visible(False)
   ax1.xaxis.tick_top()
   ax1.tick_params(labeltop='off')  # don't put tick labels at the top
   ax2.xaxis.tick_bottom()
   
   # zoom-in / limit the view to different portions of the data
   ax1.set_ylim(6.3, 6.8)
   ax2.set_ylim(0.3, 2.3)
   
   lineobjects = []
   for lc in [wat, dev, agr, nat, suc]:
      yvals = lc[2:-1]
      millions = [y/1000000 for y in yvals]
      
      # plot the same data on both axes
      ax2.plot(yearList, millions, linestyle = '-', marker='o', label = lc[1], color = lc[-1])
      ax1.plot(yearList, millions, linestyle = '-', marker='o', label = lc[1], color = lc[-1])
      lineobjects.append(lc[1])
   legend = fig.legend(lineobjects, loc = 'upper right', bbox_to_anchor=(0.5, 0.6), framealpha = 1)
   plt.subplots_adjust(left = 0.15, right=0.95, top = 0.93, hspace = 0)
   #plt.xlabel('Year')

   
   # Make the plot breaklines
   d = .015  # how big to make the diagonal lines in axes coordinates
   # arguments to pass plot, just so we don't keep repeating them
   kwargs = dict(transform=ax1.transAxes, color='k', clip_on=False)
   ax1.plot((-d, +d), (-4*d, +4*d), **kwargs)        # top-left diagonal
   ax1.plot((1 - d, 1 + d), (-4*d, +4*d), **kwargs)  # top-right diagonal

   kwargs.update(transform=ax2.transAxes)  # switch to the bottom axes
   ax2.plot((-d, +d), (1 - d, 1 + d), **kwargs)  # bottom-left diagonal
   ax2.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)  # bottom-right diagonal
   
   plt.savefig(outFig)
   plt.show()
   return
   
# Use the main function below to run desired function(s) directly from Python IDE or command line with hard-coded variables
def main():
   # Set up variables
   sumTab = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_GenSumTab'
   yearList = [2001, 2006, 2011, 2016]
   outFig = r'C:\Users\xch43889\Pictures\pyPlots\lcChange.png'
   
   # Specify function(s) to run below
   plotGeneralChange(yearList, sumTab, outFig)
   
if __name__ == '__main__':
   main()