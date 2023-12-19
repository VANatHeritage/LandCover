# Clip NLCD original files from national products to a new geodatabase. 
# Developed for 2019 version of NLCD, which delivers national NLCD layers in zipfiles (one zip for each year). This 
# script will unzip the full-extent raster, clip it, and then delete the full-extent raster (these are very large).
#
# Recommend using a template raster for extent/mask. 
# Clip feature is used for extent and clipping geometry. The coordinate system, snap, and cellsize of original
# files is maintained.
# 
# Created by: David Bucklin
# Created on: 2021-07-30
import arcpy
import os
import zipfile
import time


def clipNLCD(in_nlcd, out_nlcd, template_mask=None, clip_feature=None, cmap=False):

   templ = in_nlcd
   # generate name of new file (extracts year by position; update if needed).
   print('Cropping/masking ' + os.path.basename(in_nlcd) + ' to create `' + os.path.basename(out_nlcd) + '`...')
   # raster mask
   if template_mask is not None:
      with arcpy.EnvManager(outputCoordinateSystem=template_mask, snapRaster=template_mask, extent=template_mask, cellSize=template_mask):
         arcpy.sa.ExtractByMask(in_nlcd, template_mask).save(out_nlcd)
   else:
      # Clip from feature.
      # Headsup: don't use Clip_management. It will resample, even wiwth NO_MAINTAIN_EXTENT. May be a bug/change for Pro 3.1.2.
      with arcpy.EnvManager(outputCoordinateSystem=templ, extent=clip_feature, snapRaster=templ, cellSize=templ):
         arcpy.Clip_management(in_nlcd, out_raster=out_nlcd, in_template_dataset=clip_feature,
                               clipping_geometry="ClippingGeometry", maintain_clipping_extent="NO_MAINTAIN_EXTENT")
   arcpy.BuildPyramids_management(out_nlcd)
   if cmap:
      print("Applying colormap...")
      arcpy.AddColormap_management(out_nlcd, in_nlcd)
   return out_nlcd


def main():
   # clip = r'D:\projects\GIS_Data\Reference_Data.gdb\VA_Buff50mi_wgs84'
   template_raster = r'F:\David\GIS_data\NLCD\nlcd_2019\nlcd_2019ed_LandCover_albers.gdb\lc_2001'
   # clr_impd = r'F:\David\GIS_data\NLCD\nlcd_2021\impDescriptor_clr.clr'
   # clr_imp = r'F:\David\GIS_data\NLCD\nlcd_2021\imperv_clr.clr'
   # clr_lc = r'F:\David\GIS_data\NLCD\nlcd_2021\lc_clr.clr'
   
   # New gdbs
   nlcd_folder = r'F:\David\GIS_data\NLCD'
   lc_gdb = r'F:\David\GIS_data\NLCD\nlcd_2021\nlcd_2021ed_LandCover_albers.gdb'
   imp_gdb = r'F:\David\GIS_data\NLCD\nlcd_2021\nlcd_2021ed_Impervious_albers.gdb'
   
   # copy existing GDBs to new GDBs
   from_folder = r'F:\David\GIS_data\NLCD\nlcd_2019'
   to_folder = r'F:\David\GIS_data\NLCD\nlcd_2021'
   with arcpy.EnvManager(workspace=from_folder):
      ls = arcpy.ListWorkspaces(workspace_type="FileGDB")
   for i in ls:
      new = to_folder + os.sep + os.path.basename(i).replace("2019", "2021")
      if not arcpy.Exists(new):
         arcpy.Copy_management(i, new)
   # headsup: don't add colormaps to existing rasters. For some reason it's slow and makes the files huge.
   
   # Set up patterns
   patterns = [("2021_land_cover_l48", "lc_", lc_gdb), ("2021_impervious_l48", "imperv_", imp_gdb), ('2021_impervious_descriptor_l48', 'impDescriptor_', imp_gdb)]
   for pattern, prefix, out_gdb in patterns:
      # This loops over zipfiles. It will delete extracted files after creating clipped raster.
      flist = os.listdir(nlcd_folder)  # Get a list of all items in the input directory
      zfiles = [f for f in flist if pattern in f and f.endswith('.zip')]  # This limits the list to zips matching pattern
      for z in zfiles:
         base = z.replace('.zip', '')
         o = out_gdb + os.sep + prefix + base[5:9]
         if arcpy.Exists(o):
            print('File exists, moving on...')
            continue
         f = nlcd_folder + os.sep + base + '.img'
         if not arcpy.Exists(f):
            print('Extracting ' + z + '...')
            t0 = time.time()
            zf = zipfile.ZipFile(nlcd_folder + os.sep + z)
            zf.extractall(nlcd_folder)
            print('That took ' + str(round((time.time() - t0) / 60, 1)) + ' minutes.')
         # Now process raster
         clipNLCD(f, o, template_mask=template_raster)
   
         print('Removing files...')
         flist = os.listdir(nlcd_folder)
         ffiles = [f for f in flist if f.startswith(base) and not f.endswith('.zip')]  # This limits the list to zip files
         bla = [os.remove(nlcd_folder + os.sep + i) for i in ffiles]


if __name__ == '__main__':
   main()