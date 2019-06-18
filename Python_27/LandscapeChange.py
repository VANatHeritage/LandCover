# ---------------------------------------------------------------------------
# LandscapeChange.py
# Version:  ArcGIS 10.3 / Python 2.7
# Creation Date: 2019-06-05
# Last Edit: 2019-06-18
# Creator:  Kirsten R. Hazler
# ---------------------------------------------------------------------------

# Import modules and functions
import Helper
from Helper import *
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")


def getRect(spatialObject):
   ext = arcpy.Describe(spatialObject).extent
   rect = "%s %s %s %s" %(ext.XMin, ext.YMin, ext.XMax, ext.YMax)
   return rect

def addCoverClass(inTab, schema):
   '''To input table, adds a field indicating cover classes for each code in the "Value" field.
   
   Parameters:
   - inTab: input table (can be a standalone table or a standalone table)
   - schema: NLCD or Gen (general) codes
   '''
   
   if schema == "NLCD":   
      codeblock = '''def covClass(val):
      d = {}
      d[0] = "Unclassified"
      d[11] = "Open Water"
      d[21] = "Developed, Open Space"
      d[22] = "Developed, Low Intensity"
      d[23] = "Developed, Medium Intensity"
      d[24] = "Developed, High Intensity"
      d[31] = "Barren, Natural"
      d[32] = "Barren, Anthropogenic"
      d[41] = "Deciduous Forest"
      d[42] = "Evergreen Forest"
      d[43] = "Mixed Forest"
      d[52] = "Shrub/Scrub"
      d[71] = "Herbaceous"
      d[81] = "Hay/Pasture"
      d[82] = "Cultivated Crops"
      d[90] = "Woody Wetlands"
      d[95] = "Emergent Herbaceous Wetlands"
      
      return d[val]
      '''
   else:
      codeblock = '''def covClass(val):
      d = {}
      d[0] = "Undefined"
      d[1] = "Open Water"
      d[2] = "Developed"
      d[3] = "Agriculture"
      d[4] = "Natural"
      d[5] = "Successional"
      
      return d[val]
      '''
   expression = "covClass(!Value!)"
   
   arcpy.AddField_management(inTab, "CoverClass", "TEXT", "", "", 50)
   arcpy.CalculateField_management(inTab, "CoverClass", expression, "PYTHON", codeblock)
   
   return inTab
    
def TabLcTypes(rasterList, sumTab, clipShp = None):
   '''Tabulates the amount and percent cover for each land cover type, for each input raster. Calculates the amount of change between the first year and the last year in the sequence. Optionally, clips the rasters prior to tabulation. Modifies the rasters' attributes tables.
   
   Assumptions:
   - Input rasters are in GDB format, and all cover the exact same area. 
   - Naming convention of input rasters is "lc_yyyy*", so the year can be reliably extracted.
   - All input rasters are already clipped, or all need to be clipped (no mixture).
   - If a clipping feature class is used, it's assumed to be in the same coordinate system as the input rasters.
   
   Parameters:
   - rasterList: a list of rasters to be processed. 
   - sumTab: output summary table   
   - clipShp: an optional feature class used to clip each raster prior to calculating stats.
   '''
   
   c = 0 # initialize counter
   y = [] # initialize list of years
   for rast in rasterList:
      name = os.path.basename(rast)
      printMsg('Working on %s'%rast)
      
      if clipShp:
         # Clip raster to clipShp, if applicable
         printMsg('Clipping...')
         rect = getRect(clipShp)
         clipRast = rast + '_clp'
         arcpy.Clip_management (rast, rect, clipRast, clipShp, "", "ClippingGeometry")
      else: 
         clipRast = rast
      
      if c == 0:
      # get total pixel count; only need to do this once
         printMsg('Counting pixels...')
         arr = arcpy.da.TableToNumPyArray (clipRast,["Value", "Count"], skip_nulls=True)
         sum = arr["Count"].sum() 
      
      # determine year
      name = os.path.basename(clipRast)
      year = name[3:7]
      
      # add and calculate percent field
      printMsg('Creating and calculating percent field...')
      percFld = "Percent_%s"%year
      arcpy.AddField_management(clipRast, percFld, "FLOAT")
      arcpy.CalculateField_management(clipRast, percFld, "100*!Count!/%s"%sum, "PYTHON")
      
      # add and calculate hectares field
      printMsg('Creating and calculating hectares field...')
      haFld = "Area_ha_%s"%year
      arcpy.AddField_management(clipRast, haFld, "FLOAT")
      arcpy.CalculateField_management(clipRast, haFld, "!Count!*0.09", "PYTHON")
      
      # add and calculate acres field
      printMsg('Creating and calculating acres field...')
      acFld = "Area_ac_%s"%year
      arcpy.AddField_management(clipRast, acFld, "FLOAT")
      arcpy.CalculateField_management(clipRast, acFld, "!Count!*0.2223948429", "PYTHON")
      
      # make or append to summary table: year, percent, hectares, acres
      path = os.path.dirname(sumTab)
      name = os.path.basename(sumTab)

      if c == 0:
         printMsg('Creating summary table...')
         arcpy.TableToTable_conversion(clipRast, path, name) 
         arcpy.DeleteField_management(sumTab, "Count;Red;Green;Blue;Opacity")
         
      else:
         printMsg('Appending to summary table...')
         arcpy.JoinField_management (sumTab, "Value", clipRast, "Value", [percFld, haFld, acFld])
      
      y.append(year) 
      y.sort()
      c += 1 # update counter
   
   # determine start and end years and corresponding fields
   c -= 1
   startYear = y[0]
   endYear = y[c]
   
   # Calculate change in hectares from start to end
   startHa = "Area_ha_%s"%startYear
   endHa = "Area_ha_%s"%endYear
   printMsg('Creating and calculating hectares change field...')
   arcpy.AddField_management(sumTab, "Change_ha", "FLOAT")
   arcpy.CalculateField_management(sumTab, "Change_ha", "!%s! - !%s!"%(endHa,startHa), "PYTHON")
   
   # Calculate change in acres from start to end
   startAc = "Area_ac_%s"%startYear
   endAc = "Area_ac_%s"%endYear
   printMsg('Creating and calculating acres change field...')
   arcpy.AddField_management(sumTab, "Change_ac", "FLOAT")
   arcpy.CalculateField_management(sumTab, "Change_ac", "!%s! - !%s!"%(endAc,startAc), "PYTHON")
   
   # Calculate percent change from start to end
   printMsg('Creating and calculating change field...')
   arcpy.AddField_management(sumTab, "Change_perc", "FLOAT")
   arcpy.CalculateField_management(sumTab, "Change_perc", "100*(!%s! - !%s!)/!%s!"%(endHa,startHa,startHa), "PYTHON")
     
   printMsg('Finished.')
   return sumTab

  
def reclassBarren(refRast, schema, inRast, outRast, cmap = None): 
   '''For NLCD data: reclassifies the 31 (Barren) land cover class to 31 (for "natural barrens") or 32 (for "anthropogenic barrens"), based on a reference raster from a prior year.
   Parameters:
   - refRast: input reference raster from a previous year
   - schema: classification schema of refRast (1992 or standard)
   - inRast: the raster for which the barren class should be reclassified
   - out Rast: the updated raster with the barren class split into two types   
   '''
   # Reclassify reference raster to likeliest transition (to 31 or 32 IF inRast is classified as 31)
   refRast_rcls = refRast + '_rcls'
   if schema == '1992':
      rclsTab = "0 NODATA;11 31;21 32;22 32;23 32;31 31;32 32;33 32;41 32;42 32;43 32;51 32;61 32;71 32;81 32;82 32;83 32;84 32;85 32;91 31;92 31"
   else:
      rclsTab = "0 NODATA;11 31;21 32;22 32;23 32;24 32; 31 31;32 32;41 32;42 32;43 32;52 32;71 32;81 32;82 32;90 31;95 31"
   printMsg('Reclassifying reference raster...')
   arcpy.gp.Reclassify_sa(refRast, "Value", rclsTab, refRast_rcls, "DATA")
   
   # Apply a majority filter to the reclassified reference raster
   refRast_filt = refRast + '_filt'
   printMsg('Applying majority filter...')
   arcpy.gp.FocalStatistics_sa(refRast_rcls, refRast_filt, "Rectangle 3 3 CELL", "MAJORITY", "DATA")
   
   # Expand the 31 class in the reclassified, filtered reference raster
   exp31 = refRast + '_exp31'
   printMsg('Expanding 31 class...')
   arcpy.gp.Expand_sa(refRast_filt, exp31, "3", "31")
   
   # Get Euclidean distance to the 32 class in reference raster
   refRast_32 = refRast + '_32'
   printMsg('Creating raster for 32 class...')
   arcpy.gp.SetNull_sa(refRast, "32", refRast_32, "Value <>32")
   
   eDist32 = refRast + '_eDist32'
   printMsg('Getting Euclidean distance to 32 class...')
   arcpy.gp.EucDistance_sa(refRast_32, eDist32, "", "30", "")
   
   # Apply series of if/then statements to get final classification
   printMsg('Applying final raster calculation...')
   inRast = Raster(inRast)
   refRast = Raster(refRast)
   eDist32 = Raster(eDist32)
   exp31 = Raster(exp31)
   
   expression = """Con("%s" == 31,Con("%s" == 31,31,Con("%s" == 32,32,Con("%s" < 100,32,"%s"))),"%s")"""%(inRast, refRast, refRast, eDist32, exp31, inRast)
   arcpy.gp.RasterCalculator_sa(expression, outRast)
   
   # Add color map
   if cmap:
      printMsg('Adding color map...')
      arcpy.AddColormap_management(outRast, "", cmap)
   
   # Build pyramids
   printMsg('Building pyramids...')
   arcpy.BuildPyramids_management(outRast)

   printMsg('Finished.')
   return outRast
   
def ReclassGeneral (inRast, outRast, cmap = None):
   '''Reclassifies NLCD data to more general land cover types.
   
   Parameters:
   - inRast: Input raster to be reclassified
   - outRast: Output raster that has been reclassified
   - cmap: A colormap to apply to the output raster (optional)
   '''
   # Reclassify data
   rclsTab = "0 NODATA;11 1;21 2;22 2;23 2;24 2; 31 4;32 2;41 4;42 4;43 4;52 5;71 5;81 3;82 3;90 4;95 4"
   printMsg('Reclassifying raster...')
   arcpy.gp.Reclassify_sa(inRast, "Value", rclsTab, outRast, "DATA")
   
   # Add/populate land cover type field
   printMsg('Adding cover class names...')
   addCoverClass(outRast, "Gen")
   
   # Add color map
   if cmap:
      printMsg('Adding color map...')
      arcpy.AddColormap_management(outRast, "", cmap)
   
   # Build pyramids
   printMsg('Building pyramids...')
   arcpy.BuildPyramids_management(outRast)

   printMsg('Finished.')
   return outRast
   
# Use the main function below to run desired function(s) directly from Python IDE or command line with hard-coded variables
def main():
   ### Reclassifying barrens  
   # # Reclassifying 2001 with 1992
   # refRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_1992.gdb\lc_1992'
   # schema = '1992'
   # inRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2001'
   # outRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2001_rclsBarrens'
   
   # # Reclassifying 2006 with 2001
   # refRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2001_rclsBarrens'
   # schema = 'standard'
   # inRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2006'
   # outRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2006_rclsBarrens'
   
   # # Reclassifying 2011 with 2006
   # refRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2006_rclsBarrens'
   # schema = 'standard'
   # inRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2011'
   # outRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2011_rclsBarrens'
   
   # # Reclassifying 2016 with 2011
   # refRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2011_rclsBarrens'
   # schema = 'standard'
   # inRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2016'
   # outRast = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2016_rclsBarrens'
   
   # reclassBarren(refRast, schema, inRast, outRast)
   
   # ### Summarizing all land cover
   # r1 = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_2001_rclsBarrens_clp'
   # r2 = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_2006_rclsBarrens_clp'
   # r3 = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_2011_rclsBarrens_clp'
   # r4 = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_2016_rclsBarrens_clp'
   
   # rasterList = [r1,r2,r3,r4]
   # sumTab = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_SumTab'
   # #clipShp = r'H:\Backups\GIS_Data_VA\VGIN\AdminBounds\vginData_2019.gdb\AdminBnds_dissolve_valam'

   # TabLcTypes (rasterList, sumTab)
   
   ### Summarizing general land cover
   r1 = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_2001_rclsGeneral_clp'
   r2 = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_2006_rclsGeneral_clp'
   r3 = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_2011_rclsGeneral_clp'
   r4 = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_2016_rclsGeneral_clp'
   
   rasterList = [r1,r2,r3,r4]
   sumTab = r'H:\Backups\GIS_Data_VA\NLCD\Products_2016\nlcd_2016ed_LandCover_valam.gdb\lc_GenSumTab'

   TabLcTypes (rasterList, sumTab)
   
if __name__ == '__main__':
   main()