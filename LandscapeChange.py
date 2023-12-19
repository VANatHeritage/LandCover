# ---------------------------------------------------------------------------
# LandscapeChange.py
# Version:  ArcGIS 10.3 / Python 2.7
# Creation Date: 2019-06-05
# Last Edit: 2023-04-25
# Creator:  Kirsten R. Hazler

# Last Run: 2023-04-25, for NLCD 2019 edition.
# ---------------------------------------------------------------------------

# Import modules and functions
from helper_arcpy import *
from Helper import *
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")

def addCoverClass(inTab, schema):
   '''To input table, adds a field indicating cover classes for each code in the "Value" field.
   
   Parameters:
   - inTab: input table (can be a standalone table or a standalone table)
   - schema: NLCD or Gen (general) codes [may want to add additional schemas at some point]
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
      # d[45] = "Deciduous Forest - Silviculture"
      # d[46] = "Evergreen Forest - Silviculture"
      # d[47] = "Mixed Forest - Silviculture"
      d[52] = "Shrub/Scrub"
      d[56] = "Shrub/Scrub successional"
      d[71] = "Herbaceous"
      d[75] = "Harvested/Disturbed"
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
      d[6] = "Harvested/Disturbed"  # This is Herbaceous which is in the Forest Change class in the change product
      
      return d[val]
      '''
   expression = "covClass(!Value!)"
   
   arcpy.AddField_management(inTab, "CoverClass", "TEXT", "", "", 50)
   arcpy.CalculateField_management(inTab, "CoverClass", expression, "PYTHON", codeblock)
   
   return inTab
    
def tabLcTypes(rasterList, sumTab, clipShp = None):
   '''Tabulates the amount and percent cover for each land cover type, for each input raster. Calculates the amount of change between the first year and the last year in the sequence. Optionally, clips the rasters prior to tabulation. Modifies the rasters' attributes tables.
   
   Assumptions:
   - Input rasters are in GDB format, and all cover the exact same area. 
   - Naming convention of input rasters is "lc_yyyy*", so the year can be reliably extracted.
   - All input rasters are already clipped, or all need to be clipped (no mixture of clipped and unclipped).
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
         rect = getRect(clipShp)
         clipRast = rast + '_clp'
         if not arcpy.Exists(clipRast):
            printMsg('Clipping...')
            # headsup: if workspace is set to memory/in_memory, the mask will not work correctly (at least in Pro 3.1.2)
            arcpy.sa.ExtractByMask(rast, clipShp, "INSIDE", clipShp).save(clipRast)
            # arcpy.Clip_management(rast, rect, clipRast, clipShp, "", "ClippingGeometry")
            # Raster attribute table should be re-created, otherwise Count may not be up-to-date
            arcpy.BuildRasterAttributeTable_management(clipRast, overwrite="OVERWRITE")
      else:
         clipRast = rast
      
      if c == 0:
         # get total pixel count; only need to do this once
         printMsg('Counting pixels...')
         arr = arcpy.da.TableToNumPyArray(clipRast,["Value", "Count"], skip_nulls=True)
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
   # Reclassify reference raster to likeliest transition, only applicable IF the current raster is classed as barren. 
   # Rationale: If it was forest and is now barren, it is probably due to clearing, e.g. for mining (anthropogenic). If it was agriculture and is now barren, it may be due to clearing for development (anthropogenic). If it was water or wetland and is now barren, it is probably simply due to the shifting mosaic of barrier island habitats, and is now sand (natural). Etc. 
   # None of this matters if the current raster is anything other than 31.

   refRast_rcls = 'ref_rcls'
   if schema == '1992':
      rclsTab = "0 NODATA;11 31;21 32;22 32;23 32;31 31;32 32;33 32;41 32;42 32;43 32;51 32;61 32;71 32;81 32;82 32;83 32;84 32;85 32;91 31;92 31"
   else:
      rclsTab = "0 NODATA;11 31;21 32;22 32;23 32;24 32; 31 31;32 32;41 32;42 32;43 32;52 32;71 32;81 32;82 32;90 31;95 31"
   printMsg('Reclassifying reference raster...')
   arcpy.gp.Reclassify_sa(refRast, "Value", rclsTab, refRast_rcls, "DATA")
   
   # Apply a majority filter to the reclassified reference raster
   # This is to get rid of the effect of errant speckles
   refRast_filt = 'ref_filt'
   printMsg('Applying majority filter...')
   arcpy.gp.FocalStatistics_sa(refRast_rcls, refRast_filt, "Rectangle 3 3 CELL", "MAJORITY", "DATA")
   
   # Expand the 31 class in the reclassified, filtered reference raster
   # This is to give the "natural" barren class additional leverage near shorelines
   exp31 = 'ref_exp31'
   printMsg('Expanding 31 class...')
   arcpy.gp.Expand_sa(refRast_filt, exp31, "3", "31")
   
   # Get Euclidean distance to the 32 class in reference raster
   # If it's close to anthropogenic clearing, new barren land is more likely to be anthropogenic.
   refRast_32 = 'ref_32'
   printMsg('Creating raster for 32 class...')
   arcpy.gp.SetNull_sa(refRast, "32", refRast_32, "Value <> 32")
   
   eDist32 = 'ref_eDist32'
   printMsg('Getting Euclidean distance to 32 class...')
   arcpy.gp.EucDistance_sa(refRast_32, eDist32, "", "30", "")
   
   # Apply series of if/then statements to get final classification
   # In English pseudocode:
   # If the current pixel is NOT coded 31: keep its original class code
   # Else:
   #     If the reference pixel is 31: keep as 31
   #     Else if the reference pixel is 32: recode to 32
   #     Else if the distance to a reference pixel coded 32 is less than 100 meters: recode to 32
   #     Else: recode to the most likely transition, determined from the "exp31" raster
   printMsg('Applying final raster calculation...')
   inRast = Raster(inRast)
   refRast = Raster(refRast)
   eDist32 = Raster(eDist32)
   exp31 = Raster(exp31)
   
   expression = """Con("%s" == 31,Con("%s" == 31,31,Con("%s" == 32,32,Con("%s" < 100,32,"%s"))),"%s")"""%(inRast, refRast, refRast, eDist32, exp31, inRast)
   arcpy.gp.RasterCalculator_sa(expression, outRast)
   
   # Add cover class field
   addCoverClass(outRast, schema="NLCD")
   
   # Add color map
   if cmap:
      printMsg('Adding color map...')
      arcpy.AddColormap_management(outRast, "", cmap)
   
   # Build pyramids
   printMsg('Building pyramids...')
   arcpy.BuildPyramids_management(outRast)

   printMsg('Finished.')
   return outRast
   
def reclassGeneral(inRast, outRast, cmap = None):
   '''Reclassifies NLCD data to more general land cover types. 
   
   Assumption: Barren Land class (NLCD code 31) has already been split into Barren, Anthropogenic (32) and Barren, Natural (31)
   
   Parameters:
   - inRast: Input raster to be reclassified
   - outRast: Output raster that has been reclassified
   - cmap: A colormap to apply to the output raster (optional)
   
   Reclassification schema:
   - 1 (Open Water) includes NLCD code 11 only
   - 2 (Developed) includes NLCD codes 21, 22, 23, 24, and 32
   - 3 (Agriculture) includes NLCD codes 81 and 82
   - 4 (Natural) includes NLCD codes 31, 41, 42, 43, 90, 95
   - 5 (Successional) includes NLCD codes 52 and 71
   - alternate codes:
   - 6 (Harvested/Disturbed) includes derived code 75 (NLCD herbaceous which is in the "Forest change" class in the NLCD change raster [currently for 2001-2019]).
   - 7 (maintained grass/Shrubland)
   '''
   # Reclassify data
   # rclsTab = "0 NODATA;11 1;21 2;22 2;23 2;24 2; 31 4;32 2;41 4;42 4;43 4;52 5;71 5;81 3;82 3;90 4;95 4"
   rclsTab = "0 NODATA;11 1;21 2;22 2;23 2;24 2;31 4;32 2;41 4;42 4;43 4;52 5;56 5;71 5;75 6;81 3;82 3;90 4;95 4"  # includes forest-change added classes
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
   
def reclassForestChange(inLC, inChangeProd, outRast, clipShp = None):
   """
   headsup: experimental: use change product from NLCD to identify likely silvicultural areas.
   
   Reclassifies Shrub/Scrub (52), or Herbaceous (71) land cover classes which fall in the 
   NLCD Change Product class = 11, indicating Change to or from any of the three Forest classes (Evergreen, Deciduous, 
   and Mixed) at some point in entire NLCD time series (currently 2001-2019).
   
   If the criteria is met, the original cover class values given a new class value (old class value + 4). This avoids 
   conflict with any original NLCD class values.
   
   This re-classifies shrub/scrub or herbaceous, if it falls in the "forest change" (11) class of the NLCD change product raster.
      
   :param inLandCover: input classified land cover
   :param inChangeProd: NLCD change product raster
   :param outRast: output classified land cover with silviculture class(es)
   :return: outRast
   """
   # working
   print("Using change product to add forest change class using " + inLC + "...")
   # expression = """Con(("%s" == 41) | ("%s" == 42) | ("%s" == 43) | ("%s" == 52) | ("%s" == 71), Con("%s" == 11, "%s" + 4, "%s"), "%s")""" % (inLC, inLC, inLC, inLC, inLC, inChangeProd, inLC, inLC, inLC)
   expression = """Con(("%s" == 52) | ("%s" == 71), Con("%s" == 11, "%s" + 4, "%s"), "%s")""" % (inLC, inLC, inChangeProd, inLC, inLC, inLC)
   with arcpy.EnvManager(extent=clipShp, mask=clipShp, cellSize=inLC, snapRaster=inLC):
      arcpy.gp.RasterCalculator_sa(expression, outRast)
   arcpy.BuildPyramids_management(outRast)
   arcpy.BuildRasterAttributeTable_management(outRast)
   addCoverClass(outRast, "NLCD")
   print("Done with " + outRast + ".")
   return outRast



# Use the main function below to run desired function(s) directly from Python IDE or command line with hard-coded variables
def main():
   
   out_gdb = r'C:\David\proc\NLCD_chg\nlcd_2019ed_LandCover_albers_rclsBarrens.gdb'
   nlcd_gdb = r'F:\David\GIS_data\NLCD\nlcd_2021\nlcd_2021ed_LandCover_albers.gdb'
   nlcd_1992_orig = r"F:\David\GIS_data\NLCD\nlcd_1992_30meter_whole\nlcd_1992_30meter_whole.img"
   # change_prod_orig = r"F:\David\GIS_data\NLCD\NLCD_landcover_2019_release_all_files_20210604\nlcd_2001_2019_change_index_l48_20210604\nlcd_2001_2019_change_index_l48_20210604.img"
   clipShp = r'D:\projects\GIS_Data\Reference_Data.gdb\VirginiaCounty_dissolved'
   cmap = r"F:\David\GIS_data\NLCD\cmap_rclsBarrens.clr"
   nlcd_rasts = [[2001, nlcd_gdb + os.sep + "lc_2001"], [2004, nlcd_gdb + os.sep + "lc_2004"],
                 [2006, nlcd_gdb + os.sep + "lc_2006"], [2008, nlcd_gdb + os.sep + "lc_2008"],
                 [2011, nlcd_gdb + os.sep + "lc_2011"], [2013, nlcd_gdb + os.sep + "lc_2013"],
                 [2016, nlcd_gdb + os.sep + "lc_2016"], [2019, nlcd_gdb + os.sep + "lc_2019"],
                 [2021, nlcd_gdb + os.sep + "lc_2021"]]
   mask = nlcd_rasts[0][1]
   
   make_gdb(out_gdb)
   arcpy.env.workspace = out_gdb  # headsup: do not use memory workspace here. Can cause issues with masking rasters.
   # arcpy.env.scratchWorkspace = "in_memory"
   arcpy.env.outputCoordinateSystem = mask
   arcpy.env.extent = mask
   arcpy.env.mask = mask
   arcpy.env.cellSize = mask
   arcpy.env.snapRaster = mask
   arcpy.env.overwriteOutput = True
   
   # Extract nlcd_1992 to extent of other datasets
   nlcd_1992 = out_gdb + os.sep + "nlcd_1992"
   if not arcpy.Exists(nlcd_1992):
      arcpy.sa.ExtractByMask(nlcd_1992_orig, mask).save(nlcd_1992)
   # change_prod = out_gdb + os.sep + "nlcd_changeproduct_2001_2019"
   # if not arcpy.Exists(change_prod):
   #    arcpy.sa.ExtractByMask(change_prod_orig, mask).save(change_prod)
   
   # Loop over nlcd 2001-2019
   for n in enumerate(nlcd_rasts):
      if n[0] == 0:
         ref = nlcd_1992
         refYear = "1992"
      else:
         ref = outRast
         refYear = "2001"
      inRast = n[1]
      outRast = out_gdb + os.sep + 'lc_' + str(inRast[0]) + '_rclsBarrens'
      if not arcpy.Exists(outRast):
         print("Making " + outRast + "...")
         reclassBarren(ref, refYear, inRast[1], outRast, cmap)
      else:
         print("Already exists: " + outRast + "...")
      # Makes general land cover
      outRast_gen = out_gdb + os.sep + 'lc_' + str(inRast[0]) + '_rclsGeneral'
      if not arcpy.Exists(outRast_gen):
         reclassGeneral(outRast, outRast_gen)
      
      # coulddo: run again to add Silviculture class (current forest which has/will experience change).
      # With silviculture classes
      # outRast_For = out_gdb + os.sep + 'lc_' + str(inRast[0]) + '_rclsFor'
      # if not arcpy.Exists(outRast_For):
      #    reclassForestChange(outRast, change_prod, outRast_For, clipShp=clipShp)
      # # Makes general land cover
      # outRast_genFor = out_gdb + os.sep + 'lc_' + str(inRast[0]) + '_rclsGeneralFor'
      # if not arcpy.Exists(outRast_genFor):
      #    reclassGeneral(outRast_For, outRast_genFor)
      
   ### Summarizing all land cover
   # rasterList = [out_gdb + os.sep + 'lc_' + str(n[0]) + '_rclsBarrens' for n in nlcd_rasts]
   # sumTab = out_gdb + os.sep + 'lc_rclsBarren_changeSummary'
   # clipShp = r'D:\projects\GIS_Data\Reference_Data.gdb\VirginiaCounty_dissolved'
   # tabLcTypes(rasterList, sumTab, clipShp)
   
   ### Summarizing general land cover
   rasterList = [out_gdb + os.sep + 'lc_' + str(n[0]) + '_rclsGeneral' for n in nlcd_rasts]
   sumTab = out_gdb + os.sep + 'lc_rclsGeneral_changeSummary_upd2021_chk'
   tabLcTypes(rasterList, sumTab, clipShp)
   addCoverClass(sumTab, "Gen")
   
   ### Summarizing general land cover (w/ harvested/disturbed)
   # headsup: these are already clipped to boundary
   # rasterList = [out_gdb + os.sep + 'lc_' + str(n[0]) + '_rclsGeneralFor' for n in nlcd_rasts]
   # sumTab = out_gdb + os.sep + 'lc_rclsGeneralFor_changeSummary'
   # tabLcTypes(rasterList, sumTab)
   # addCoverClass(sumTab, "Gen")
   
   # rasterList = [out_gdb + os.sep + 'lc_' + str(n[0]) + '_rclsFor' for n in nlcd_rasts]
   # sumTab = out_gdb + os.sep + 'lc_rclsFor_changeSummary'
   # tabLcTypes(rasterList, sumTab)
   # addCoverClass(sumTab, "NLCD")
   
if __name__ == '__main__':
   main()
