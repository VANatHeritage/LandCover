# ----------------------------------------------------------------------------------------
# nlcd_summaries.py
# Version:  ArcGIS Pro 2.3.3 / Python 3.6
# Creation Date: 2016
# Last Edit: 2019-07-02
# Creator(s): Amy Conley, David Bucklin

# Summary:
# Takes NLCD (including impervious and canopy coverage) data,
# a study region, and a raster mask, and outputs
# summary variables for land cover types. This
# script outputs TIF files to a new project
# folder that can be used directly as environmental
# variables for SDM work. TIF files are proportional
# land cover, multiplied by 10000 and rounded to
# integers to save file space.

# Usage Tips:
# 1. Set all paths prior to usage.
# 2. TIF outputs are large - make sure you have enough space in working directory drive

# Dependencies:
# Spatial analyst

# Syntax:
# [need to manually enter variables and run entire script in IDE]

# Data Links:
# latest Virginia NLCD clips are here:
# http://vdcr.maps.arcgis.com/home/group.html?id=6195b324fa8343029c17692140e7c0b6
# ----------------------------------------------------------------------------------------

import arcpy
import os
from arcpy.sa import *

# begin variables

# working directory (project folder created here)
wd = r'D:\scratch\arc_wd'
# project folder name
project_nm = 'nlcd_2016'

# study extent
extent_shp = r'E:\arcmap_wd\scratch.gdb\sdmVA_pred_area'

# input raster(s). Set None for ones not used
nlcd_classified = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2016'
impervious_raster = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_Impervious_albers.gdb\imperv_2016'
canopy_raster = None

# (optional) mask
mask = r'E:\projects\SDM_ancilliary\Hypergrid\VA_methods\raster\_masks\data_mask.tif'

# end variables

# make output dir/processing gdb
project_dir = wd + os.sep + project_nm
try:
   os.mkdir(project_dir)
except:
   print("Folder already exists. This will overwrite existing files in the folder.")
try:
   out_gdb = arcpy.CreateFileGDB_management(project_dir, project_nm + "_processing")
except:
   print("Processing gdb already exists. This will overwrite existing files in the gdb.")
   out_gdb = project_dir + os.sep + project_nm + "_processing.gdb"

# set environmental variables
arcpy.CheckOutExtension("Spatial")
arcpy.env.workspace = str(out_gdb)
arcpy.env.overwriteOutput = True
arcpy.env.snapRaster = mask
arcpy.env.outputCoordinateSystem = mask

# buffer extent feature
# skip if already buffered
extent_shp = arcpy.Buffer_analysis(in_features=extent_shp, out_feature_class="nlcdprocextent",
                                   buffer_distance_or_field="5000 Meters", dissolve_option="ALL")
# arcpy.env.extent = extent_shp (not necessary)

# clean (clip and set null) rasters
# nlcd classified
in_nlcd = arcpy.Clip_management(nlcd_classified, "#", "nlcdcliptemp", extent_shp, "#", "ClippingGeometry")
inraster = "nlcdcliptemp"
where_clause = "Value = 0"
false_raster = inraster
output_raster = "landcover_classified_clean"
outsetNull = SetNull(inraster, false_raster, where_clause)
outsetNull.save(output_raster)
in_nlcd_class = "landcover_classified_clean"

# impervious
if impervious_raster:
   in_nlcd = arcpy.Clip_management(impervious_raster, "#", "nlcdcliptemp", extent_shp, "#", "ClippingGeometry")
   inraster = "nlcdcliptemp"
   where_clause = "Value = 127"
   false_raster = inraster
   output_raster = "impsur"
   outsetNull = SetNull(inraster, false_raster, where_clause)
   outsetNull.save(output_raster)
   in_impervious = "impsur"

# canopy
if canopy_raster:
   in_nlcd = arcpy.Clip_management(canopy_raster, "#", "nlcdcliptemp", extent_shp, "#", "ClippingGeometry")
   inraster = "nlcdcliptemp"
   where_clause = "Value = 0"
   false_raster = inraster
   output_raster = "canopy"
   outsetNull = SetNull(inraster, false_raster, where_clause)
   outsetNull.save(output_raster)
   in_canopy = "canopy"

arcpy.Delete_management("nlcdcliptemp")
##Step 0: Set up the Remap Values

# Raster values and their associated habitat in the NLCD
# 11 = Open Water
# 12 = Perennial Ice/Snow
# 21 = Developed Open Space
# 22 = Developed Low Intensity
# 23 = Developed Medium Intensity
# 24 = Developed High Intensity
# 31 = Barren Land
# 41 = Deciduous Forest
# 42 = Evergreen Forest
# 43 = Mixed Forest
# 52 = Shrub/Scrub
# 71 = Grassland/Herbaceous
# 81 = Pasture/Hay
# 82 = Cultivated Crops
# 90 = Woody Wetlands
# 95 = Emergent Herbaceous Wetlands

# For Forest we only want values 41,42,43
# remap_forest = RemapValue(
#    [[11, 0], [12, 0], [21, 0], [22, 0], [23, 0], [24, 0], [31, 0], [41, 1], [42, 1], [43, 1], [52, 0], [71, 0], [81, 0],
#     [82, 0], [90, 0], [95, 0]])

# For Wetland we only want 90 and 95
remap_wetland = RemapValue(
   [[11, 0], [12, 0], [21, 0], [22, 0], [23, 0], [24, 0], [31, 0], [41, 0], [42, 0], [43, 0], [52, 0], [71, 0], [81, 0],
    [82, 0], [90, 1], [95, 1]])

# For Open Area we want 31, 71,81,82
remap_Open = RemapValue(
   [[11, 0], [12, 0], [21, 0], [22, 0], [23, 0], [24, 0], [31, 1], [41, 0], [42, 0], [43, 0], [52, 0], [71, 1], [81, 1],
    [82, 1], [90, 0], [95, 0]])

# For Water we want 11
remap_water = RemapValue(
   [[11, 1], [12, 0], [21, 0], [22, 0], [23, 0], [24, 0], [31, 0], [41, 0], [42, 0], [43, 0], [52, 0], [71, 0], [81, 0],
    [82, 0], [90, 0], [95, 0]])

# For ShrubScrub we want 52
remap_ShrubScrub = RemapValue(
   [[11, 0], [12, 0], [21, 0], [22, 0], [23, 0], [24, 0], [31, 0], [41, 0], [42, 0], [43, 0], [52, 1], [71, 0], [81, 0],
    [82, 0], [90, 0], [95, 0]])

# For ConiferForest we want 42
# remap_evergreen = RemapValue(
#    [[11, 0], [12, 0], [21, 0], [22, 0], [23, 0], [24, 0], [31, 0], [41, 0], [42, 1], [43, 0], [52, 0], [71, 0], [81, 0],
#     [82, 0], [90, 0], [95, 0]])

# For Deciduous/Mix we want 41 and 43 and we want 43 half as much so 41->100 and 43->50
remap_decidmix = RemapValue(
   [[11, 0], [12, 0], [21, 0], [22, 0], [23, 0], [24, 0], [31, 0], [41, 100], [42, 0], [43, 50], [52, 0], [71, 0],
    [81, 0], [82, 0], [90, 0], [95, 0]])

# For Evergreen/Mix we want 42 and 43 and we want 43 half as much so 42->100 and 43->50
remap_evermix = RemapValue(
   [[11, 0], [12, 0], [21, 0], [22, 0], [23, 0], [24, 0], [31, 0], [41, 0], [42, 100], [43, 50], [52, 0], [71, 0],
    [81, 0], [82, 0], [90, 0], [95, 0]])

inraster = in_nlcd_class

# Step 2 - Reclass the rasters for each desired land type
reclass_field = "Value"

# out_reclassify_forest = Reclassify(inraster, reclass_field, remap_forest, "NODATA")
# out_reclassify_forest.save(project_nm + "_b_forest_n")

out_reclassify_wetland = Reclassify(inraster, reclass_field, remap_wetland, "NODATA")
out_reclassify_wetland.save('nlcdwet')

out_reclassify_open = Reclassify(inraster, reclass_field, remap_Open, "NODATA")
out_reclassify_open.save('nlcdopn')

out_reclassify_water = Reclassify(inraster, reclass_field, remap_water, "NODATA")
out_reclassify_water.save('nlcdwat')

out_reclassify_ShrubScrub = Reclassify(inraster, reclass_field, remap_ShrubScrub, "NODATA")
out_reclassify_ShrubScrub.save('nlcdshb')

#########Added 2017 - Split the forest into evergreen/mixed forest and deciduous/mixed forest

# out_reclassify_Evergreen = Reclassify(inraster, reclass_field, remap_evergreen, "NODATA")
# out_reclassify_Evergreen.save(project_nm + "_b_evergreen_n")

out_reclassify_decidmix = Reclassify(inraster, reclass_field, remap_decidmix, "NODATA")
out_reclassify_decidmix.save('nlcddfr')

out_reclassify_Evermix = Reclassify(inraster, reclass_field, remap_evermix, "NODATA")
out_reclassify_Evermix.save('nlcdefr')

print("done reclassifying")
# Step 3: Calculate focal statistics

# get list of binary rasters and add impervious and canopy if necessary
# proj_source = arcpy.ListRasters('nlcd*')
proj_source = ['nlcdwet', 'nlcdopn', 'nlcdwat', 'nlcdshb', 'nlcddfr', 'nlcdefr']
if impervious_raster:
   proj_source.append(in_impervious)
if canopy_raster:
   proj_source.append(in_canopy)

# focal neighborhood names and types
ngb_nm = ['1', '10', '100']
ngb_type = [NbrRectangle(3, 3, "CELL"), NbrCircle(10, "CELL"), NbrCircle(100, "CELL")]
ngb_ls = [i for i in range(0, len(ngb_nm))]

for raster in proj_source:
   print("Calculating focal statistics for " + raster + "...")

   for n in ngb_ls:
      out_raster = project_dir + os.sep + raster + ngb_nm[n] + '.tif'
      type = ngb_type[n]
      print("Calculating neighborhood " + ngb_nm[n] + "...")
      outFocal = FocalStatistics(raster, type, "MEAN", "DATA")
      outFocal = Con(IsNull(outFocal), 0, outFocal)
      outFocal = ExtractByMask(outFocal, mask)
      if raster in ['impsur', 'nlcddfr', 'nlcdefr']:
         # these have initial max value of 100
         outFocal = Int((outFocal * 100) + 0.5)
      else:
         # these have initial max value of 1
         outFocal = Int((outFocal * 10000) + 0.5)
      outFocal.save(out_raster)
      print("Finished with neighborhood " + ngb_nm[n] + ".")

   print("Finished with " + raster + ".")

## clean up
if arcpy.Exists("maskfinal"):
   arcpy.Delete_management("maskfinal")
arcpy.Delete_management("nlcdprocextent")
