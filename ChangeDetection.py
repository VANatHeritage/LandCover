"""
ChangeDetection.py
Version:  ArcGIS Pro / Python 3.x
Creation Date: 2023-04-25
Last Edit: 2023-04-25
Creator: David Bucklin

Functions to create and summarize changes in land cover over time.
"""
from helper_arcpy import *


def change_rast(nlcd_t1, nlcd_t2, chg_rast, mask=None):
   '''
   Make a change raster using classified rasters from two time periods.
   :param nlcd_t1: Land cover raster in time 1.
   :param nlcd_t2: Land cover raster in time 2.
   :param chg_rast: Output change raster
   :param mask: Mask to apply (optional).
   :return: 
   '''
   print('Calculating changes...')
   with arcpy.EnvManager(mask=mask, extent=mask, outputCoordinateSystem=nlcd_t1, snapRaster=nlcd_t1, cellSize=nlcd_t1):
      rc = arcpy.sa.RasterCalculator([nlcd_t1, nlcd_t2], ["t1", "t2"], 'Int((t1*100) + t2)')
      arcpy.sa.ExtractByMask(rc, mask).save(chg_rast)
   print("Building attribute table...")
   arcpy.BuildPyramids_management(chg_rast)
   arcpy.BuildRasterAttributeTable_management(chg_rast, overwrite="OVERWRITE")
   # vals = [a[0] for a in arcpy.da.SearchCursor(chg_rast, ["Value"])]
  
   # classes in either dataset
   cls_t1 = [[a[0], a[1]] for a in arcpy.da.SearchCursor(nlcd_t1, ["Value", "CoverClass"])]
   cls_t2 = [[a[0], a[1]] for a in arcpy.da.SearchCursor(nlcd_t2, ["Value", "CoverClass"])]
   # Create list with all possible combination of values
   cls = []
   for c in cls_t1:
      [cls.append([int(c[0]*100) + int(i[0]), c, i]) for i in cls_t2]
   # Add fields
   arcpy.AddField_management(chg_rast, "change_type", "TEXT", field_length=100)
   arcpy.AddField_management(chg_rast, "start_class", field_type="Short")
   arcpy.AddField_management(chg_rast, "start_class_name", "TEXT", field_length=100)
   arcpy.AddField_management(chg_rast, "end_class", field_type="Short")
   arcpy.AddField_management(chg_rast, "end_class_name", "TEXT", field_length=100)
   # Calculate fields
   with arcpy.da.UpdateCursor(chg_rast, ["Value", "start_class", "start_class_name", "end_class", "end_class_name", "change_type"]) as curs:
      for r in curs:
         v = [i for i in cls if i[0] == r[0]][0]
         r[1], r[2], r[3], r[4] = v[1][0], v[1][1], v[2][0], v[2][1]
         if r[1] != r[3]:
            r[5] = r[2] + " to " + r[4]
         else:
            r[5] = "No change"
         curs.updateRow(r)
   # Calculate area / percentages
   arcpy.CalculateField_management(chg_rast, "area_ha", "(!Count! * 900) / 10000", field_type="Float")
   total_cells = sum([int(a[0]) for a in arcpy.da.SearchCursor(chg_rast, ["Count"])])
   arcpy.CalculateField_management(chg_rast, "perc_total", "(!Count! / " + str(total_cells) + ") * 100", field_type="Float")
   print("Done.")
   return chg_rast


def change_summary(chg_rast, start_cls, start_cls_nm, end_cls, end_cls_nm, out_rast, backwards=True):
   """
   From the change-detection raster, create a classified raster showing change from start_cls to end_cls.
   :param chg_rast: Change raster, created by 'change_detection_rast' function.
   :param start_cls: List of start classes to identify change from (and optionally to)
   :param start_cls_nm: Name to assign the start classes
   :param end_cls: List of end classes, where changes from start to end (and optionally end to start) will be identified
   :param end_cls_nm: Name to assign to the end classes
   :param out_rast: Output raster
   :param backwards: whether to include a classes identifying change from the end_cls the start_cls.
   The output raster can potentially have 6 classes, including:
      0: Not part of start_cls for either time period
      1: In start_cls for both time periods (no change)
      2: Changed from start_cls to end_cls
      3: Changed from start_cls to any other class (i.e. not included in end_cls)
   If backwards = True, change TO the start class will also be identified:
      4. Change from end_cls to start_cls
      5. Change from any other class (i.e. not included in end_cls) to start_cls
   :return: chg_rast
   """
   print("Creating reclassification table...")
   comb_class = start_cls + end_cls
   arcpy.CopyRows_management(chg_rast, "tmp_tab")
   arcpy.AddField_management("tmp_tab", "reclass", "SHORT")
   with arcpy.da.UpdateCursor("tmp_tab", ["start_class", "end_class", "reclass"]) as curs:
      for r in curs:
         sc = r[0]
         ec = r[1]
         if sc in start_cls and ec in start_cls:
            r[2] = 1
         elif sc in start_cls and ec in end_cls:
            r[2] = 2
         elif sc in start_cls and ec not in comb_class:
            r[2] = 3
         elif sc in end_cls and ec in start_cls:
            r[2] = 4
         elif sc not in comb_class and ec in start_cls:
            if backwards:
               r[2] = 5
            else:
               r[2] = 4
         else:
            r[2] = 0
         curs.updateRow(r)
   print("Reclassifying change detection raster...")
   arcpy.sa.ReclassByTable(chg_rast, "tmp_tab", "Value", "Value", "reclass").save(out_rast)
   arcpy.BuildRasterAttributeTable_management(out_rast, "OVERWRITE")
   arcpy.BuildPyramids_management(out_rast)
   
   print("Calculating attributes....")
   codeblock = '''def fn(val, sn, en, bw):
      if val == 0:
         return 'not ' + sn + ' in either time period'
      elif val == 1:
         return sn + ' in both time periods'
      elif val == 2:
         return sn + ' to ' + en
      elif val == 3:
         return sn + ' to non-' + en + ' class'
      elif val == 4:
         if bw:
            return en + ' to ' + sn
         else:
            return 'non-' + sn + ' class to ' + sn
      elif val == 5:
         return 'non-' + en + ' class to ' + sn
   '''
   fn_call = "fn(!Value!,'" + start_cls_nm + "','" + end_cls_nm + "'," + str(backwards) + ")"
   arcpy.CalculateField_management(out_rast, "class", fn_call, code_block=codeblock, field_type="TEXT")

   # Calculate stats
   arcpy.CalculateField_management(out_rast, "area_ha", "(!Count! * 900) / 10000", field_type="Float")
   # percentages (only for rows which were start_cls in t1, so the percentages are relative to that time period).
   tab = arcpy.MakeTableView_management(out_rast, where_clause="Value IN (1, 2, 3)")
   total_cells = sum([int(a[0]) for a in arcpy.da.SearchCursor(tab, ["Count"])])
   arcpy.CalculateField_management(tab, "perc_of_t1_area", "(!Count! / " + str(total_cells) + ") * 100", field_type="Float")
   print("Done.")
   return out_rast


def change_to_from(chg_rast, start_cls, start_cls_nm, out_rast):
   """
   From the change-detection raster, create a classified raster showing change from start_cls to end_cls.
   :param chg_rast: Change raster, created by 'change_detection_rast' function.
   :param start_cls: List of start classes to identify change from (and optionally to)
   :param start_cls_nm: Name to assign the start classes
   :param out_rast: Output raster
   The output raster can potentially have 6 classes, including:
      0: Not part of start_cls for either time period
      1: In start_cls for both time periods (no change)
      2: Changed from start_cls to end_cls
      3: Changed from start_cls to any other class (i.e. not included in end_cls)
   If backwards = True, change TO the start class will also be identified:
      4. Change from end_cls to start_cls
      5. Change from any other class (i.e. not included in end_cls) to start_cls
   :return: chg_rast
   """
   print("Creating reclassification table...")
   arcpy.CopyRows_management(chg_rast, "tmp_tab")
   arcpy.AddField_management("tmp_tab", "reclass", "LONG")
   repl = str(start_cls[0])
   
   with arcpy.da.UpdateCursor("tmp_tab", ["start_class", "start_class_name", "end_class", "end_class_name", "reclass", "Value", "change_type"]) as curs:
      for r in curs:
         sc = r[0]
         ec = r[2]
         if sc in start_cls:
            if ec in start_cls:
               # no change
               r[4] = 1
               r[6] = start_cls_nm + " both time periods"
            else:
               # change from target
               r[0] = int(repl)
               r[1] = start_cls_nm
               # make new change class
               r[4] = int(repl + str(ec))
               r[6] = start_cls_nm + " to " + r[3]
         else:
            if ec in start_cls:
               # change to target
               r[2] = int(repl)
               r[3] = start_cls_nm
               # make new change class
               r[4] = int(str(sc) + repl)
               r[6] = r[1] + " to " + start_cls_nm
            else:
               # not part of target class either period
               r[4] = 0
               r[6] = "Not " + start_cls_nm + " either time period"
         curs.updateRow(r)
   arcpy.CopyRows_management("tmp_tab", out_rast + 'tab')
   print("Reclassifying change detection raster...")
   arcpy.sa.ReclassByTable(chg_rast, "tmp_tab", "Value", "Value", "reclass").save(out_rast)
   arcpy.BuildRasterAttributeTable_management(out_rast, "OVERWRITE")
   arcpy.BuildPyramids_management(out_rast)
   # join new name
   flds = ['change_type']
   arcpy.JoinField_management(out_rast, "Value", "tmp_tab", "reclass", flds)

   # Calculate stats
   arcpy.CalculateField_management(out_rast, "area_ha", "(!Count! * 900) / 10000", field_type="Float")
   total_cells = sum([int(a[0]) for a in arcpy.da.SearchCursor(out_rast, ["Count"])])
   arcpy.CalculateField_management(out_rast, "perc_area", "(!Count! / " + str(total_cells) + ") * 100", field_type="Float")
   # Copy table
   arcpy.CopyRows_management(out_rast, out_rast + "_tab")
   
   print("Done.")
   return out_rast


# Run process
out_gdb = r'C:\David\proc\NLCD_chg\nlcd2019ed_changeDetection.gdb'
arcpy.env.workspace = out_gdb  # "in_memory"  # headsup: don't use memory as workspace. Can cause issues with masking.
arcpy.env.overwriteOutput = True
make_gdb(out_gdb)
in_gdb = r'C:\David\proc\NLCD_chg\nlcd_2019ed_LandCover_albers_rclsBarrens.gdb'
# change_prod = in_gdb + os.sep + "nlcd_changeproduct_2001_2019"
mask = r"D:\projects\GIS_Data\Reference_Data.gdb\VirginiaCounty_dissolved"

# Set up year combinations
# yr_all = ['2001', '2004', '2006', '2008', '2011', '2013', '2016', '2019']
# yr_pairs = [[yr_all[i], yr_all[i+1]] for i in list(range(0, len(yr_all)-1))] + [[yr_all[0], yr_all[len(yr_all)-1]]]
yr_pairs = [['2001', '2021'], ['2001', '2011'], ['2011', '2021']]  # manual setting
# yr_pairs = [['2001', '2011']]

# Settings for General reclass change summary
# Find differences for Natural->developed
start_cls = [4]
end_cls = [2]
start_cls_nm = "Natural"
end_cls_nm = "Developed"
suffix = '_rclsGeneral'
chg_nm = "lc_allChangeGeneral"
summ_nm = "chg_nat_dev"

## Settings for All NLCD class change summary
# Find differences for Forest->developed
start_cls = [41, 42, 43, 52, 90]  # note the derived forest change classes are 56 (shrub/scrub), 75 (herbaceous)
start_cls_nm = "Forest"
end_cls = [21, 22, 23, 24, 32]
end_cls_nm = "Developed"
# Input raster name pattern
suffix = "rclsBarrens"  # rclsBarrens | rclsFor
# Output rasters name pattern
if suffix == "rclsBarrens":
   chg_nm = "lc_allChange"
   summ_nm = "chg_forest_dev"
else:
   chg_nm = "lc_allChangeFor"
   summ_nm = "chgFor_forest_dev"

# Run change summary
for y in yr_pairs:
   y1 = y[0]
   y2 = y[1]
   print("Working on " + y1 + " to " + y2 + "...")
   nlcd_t1 = in_gdb + os.sep + 'lc_' + y1 + "_" + suffix
   nlcd_t2 = in_gdb + os.sep + 'lc_' + y2 + "_" + suffix
   chg_rast = out_gdb + os.sep + chg_nm + "_" + y1 + "_" + y2
   if not arcpy.Exists(chg_rast):
      change_rast(nlcd_t1, nlcd_t2, chg_rast, mask)
   out_rast = out_gdb + os.sep + summ_nm + "_" + y1 + "_" + y2
   change_summary(chg_rast, start_cls, start_cls_nm, end_cls, end_cls_nm, out_rast, backwards=False)

# end
