# =================================================================================================================== #
# Script Name:	image_processing.py
# Author:	    Brian Laureijs
# Purpose:      Run functions on Sentinel-2 imagery for Sable Island.
# Date:         20190508
# Version:      0.1.1
# Notice:       Created for academic assessment. Do not re-use or
#               redistribute without permission from author.
# =================================================================================================================== #
# Import Libraries                                  # Requirements:
# =================================================================================================================== #
import os                                           # Directory and
import shutil                                       # file manipulation
import arcpy                                        # Vector file manipulation
import time                                         # Processing timer
from pci.str import str as stretch                  # Histogram stretching
from pci.lut import *                               # Enhancement
from pci.pcimod import *                            # Add layers
from pci.pca import *                               # Principal Components
from pci.nspio import Report, enableDefaultReport   # Report output
from pci.exceptions import PCIException             # Throwing errors
from pci.fexport import *                           # Export to TIF format
from pci.masking import *                           # Cloud and haze masking
from pci.hazerem import *                           # Haze removal
from pci.atcor import *                             # Atmospheric correction
from pci.kclus import *                             # Unsupervised K-Means classifier
from pci.ras2poly import *                          # Raster to Polygon conversion
from pci.poly2bit import *                          # Polygon to Bitmap conversion
from pci.scale import *                             # 8-Bit compression for PCT generation
from pci.datamerge import *
from pci.pctmake import *                           # PCT generation from raster layer for classification result
# ------------------------------------------------------------------------------------------------------------------- #
# Declare global variables
# ------------------------------------------------------------------------------------------------------------------- #
global sen2                                         # Sensor name used in pci correction
sen2 = "Sentinel-2"                                 # functions.

global workspace_list                               # Workspace directory list
workspace_list = []                                 # for iterative folder preparation

# ------------------------------------------------------------------------------------------------------------------- #
# Initialize path variables:
# ------------------------------------------------------------------------------------------------------------------- #
workingdir = os.getcwd()  # Get current working directory
pixdir = os.path.join(workingdir, "pix")            # Pix folder workspace

corrdir = os.path.join(workingdir, "atcor")         # Corrected pix output
workspace_list.append(corrdir)

pcadir = os.path.join(workingdir, "pca")            # PCA output
workspace_list.append(pcadir)

coastdir = os.path.join(workingdir, "coastline")    # Coastline output
workspace_list.append(coastdir)

maskdir = os.path.join(workingdir, "masks")         # Cloud mask output
workspace_list.append(maskdir)

landcoverdir = os.path.join(workingdir,"landcover") # Classified land cover
workspace_list.append(landcoverdir)


# ------------------------------------------------------------------------------------------------------------------- #
# Define delete_shp() function
#   1. Check if "input" directory exists and prompt user if it does not
#   2. For rest of folders, create new if they do not exist, or delete contents and make new folder if they do.
# Parameters:
#   shapefile      - The input image file directory; has to be handled differently so contents are not deleted
#   folder_list - The list of output folders that should be cleared before processing is started.
# ------------------------------------------------------------------------------------------------------------------- #
# TODO write function to delete shapefiles and their auxillary files
# ------------------------------------------------------------------------------------------------------------------- #
# Define prep_workspace() function
#   1. Check if "input" directory exists and prompt user if it does not
#   2. For rest of folders, create new if they do not exist, or delete contents and make new folder if they do.
# Parameters:
#   indir       - The input image file directory; has to be handled differently so contents are not deleted
#   folder_list - The list of output folders that should be cleared before processing is started.
# ------------------------------------------------------------------------------------------------------------------- #

def prep_workspace(indir,folder_list):
    if os.path.isdir(indir) == False:
        print "Missing pix folder: Run import.py first!"
    for i in range(len(folder_list)):
        if os.path.isdir(folder_list[i]) == True:
            print "Clearing \t%s" % folder_list[i]
            shutil.rmtree(folder_list[i])
            os.mkdir(folder_list[i])
        else:
            os.mkdir(folder_list[i])
            print "Created \t%s" % folder_list[i]


# ------------------------------------------------------------------------------------------------------------------- #
# Define mask_clouds() function:
#   1. Apply unsupervised classification to SWIR Cirrus image band.
#   2. Export classification to polygon format.
#   3. Select cloud polygons.
#   4. Export cloud polygons to scratch tif.
#   5. Convert scratch tif to bitmap layer.
# Parameters:
#   pix60in     - The input atmospheric band file with the SWIR cirrus band in channel three.
#   bitmapout   - The output file for the bitmap layer.
#   identifier  - Unique identifier string read from input file name.
# ------------------------------------------------------------------------------------------------------------------- #
# TODO invert mask so it masks everything OTHER than clouds, and can be used as input mask with kclus
def mask_clouds(pix60in, bitmapout, identifier):
    polygonout_name_full = identifier + "_cloud_polygons_full.shp"
    polygonout_full = os.path.join(maskdir,polygonout_name_full)
    polygonout_name = identifier + "_cloud_polygons.shp"
    polygonout = os.path.join(maskdir,polygonout_name)
    id_string = "Cloud mask bitmap for file %s" % identifier
    pcimod(file=pix60in,                                            # Input 60m resolution atmospheric bands pix file
           pciop='ADD',                                             # Modification mode "Add"
           pcival=[0, 0, 1, 0])                                     # Task - add one 16U channels
    print "Classifying clouds from SWIR Cirrus band in file %s..." % identifier
    kclus(file=pix60in,                                             # Run classification atmospheric bands
          dbic=[3],                                                 # Use Layer 3 (SWIR Cirrus)
          dboc=[4],                                                 # Output to blank layer
          numclus=[2],                                              # Two clusters - clouds, not clouds
          seedfile='',
          maxiter=[20],
          movethrs=[],
          siggen="YES",
          backval=[],
          nsam=[])
    print "Cloud classification complete."
    print "Converting to polygon shapefile..."
    ras2poly(fili=pix60in,                                              # Use scratch PIX file
             dbic=[4],                                                  # Use classification channel
             filo=polygonout_full,                                      # Polygon SHP output location
             smoothv="YES",                                             # Smooth boundaries
             dbsd=id_string,                                            # Layer description string
             ftype="SHP",                                               # Shapefile format
             foptions="")
    print "Shapefile conversion complete."
    print "Converting polygons to bitmap layer..."
    workspace = os.path.join(workingdir, "sable.gdb")                   # Define GDB workspace
    polygonoutf_lyr = identifier + "_polygon_lyr"                       # Define feature layer name for polygon output
    arcpy.env.workspace = workspace                                     # Set default workspace
    arcpy.MakeFeatureLayer_management(polygonout_full, polygonoutf_lyr) # Make polygon feature layer

    arcpy.FeatureClassToFeatureClass_conversion(in_features=polygonoutf_lyr,        # Extract only cloud polygons
                                                out_path=maskdir,                   # Output location
                                                out_name=polygonout_name,           # Output filename
                                                where_clause='"Area" < 1000000000') # Anything <1B SM not clouds
    poly2bit(fili=polygonout,                                           # Convert polygons to bitmap layer
             dbvs=[1],                                                  # Input vector layer
             filo=bitmapout,                                            # Output file
             dbsd=id_string,                                            # Layer description
             pixres=[10,10],                                            # 10m resolution
             ftype="PIX")                                               # Pix format

    pfull_dbf = polygonout_full[:-3] + "dbf"
    pfull_prj = polygonout_full[:-3] + "prj"
    pfull_pox = polygonout_full + ".pox"
    pfull_shx = polygonout_full[:-3] + "shx"
    os.remove(polygonout_full)                                          # Clean up intermediate polygon file
    os.remove(pfull_dbf)
    os.remove(pfull_prj)
    os.remove(pfull_pox)
    os.remove(pfull_shx)

    print "Bitmap conversion complete. Output to \n\t%s" % bitmapout
    return bitmapout


# ------------------------------------------------------------------------------------------------------------------- #
# Define correction() function:
#   1. Process masks for raw pix image.
#   2. Process haze removal for pix image.
#   3. Process atmospheric correction for pix image.
# Parameters:
#   piximage    - The input pix format image.
#   hazeout     - The output haze corrected image.
#   atcorout    - The output atmospherically corrected image.
# ------------------------------------------------------------------------------------------------------------------- #
def correction(piximage, hazeout, atcorout):
    print "-" * 50
    print "Processing masks..."
    masking(fili=piximage,                          # Input pix
            asensor=sen2,                           # Sentinel-2
            visirchn=[1, 3, 4],                     # B, R, NIR channels
            hazecov=[25],                           # Haze coverage
            clthresh=[-1, -1, -1],                  # Default cloud reflectance threshold
            filo=piximage)                          # Output (same file)
    print "Masks for %s completed" % piximage
    print "Processing haze removal... (This may take a while)"
    hazerem(fili=piximage,                          # Input pix
            asensor=sen2,                           # Sentinel-2
            visirchn=[1, 3, 4],                     # B, R, NIR channels
            chanopt="p,p,p,c,p,p,p,c,c,c,",         # Process or copy? (channels 1-13)
            maskfili=piximage,                      # Masks in same file
            maskseg=[2, 3, 4],                      # Haze, Cloud, Water mask channels
            hazecov=[50],                           # Haze coverage default 50
            filo=hazeout)                           # Output pix
    print "Haze removed from %s." % piximage
    print "Processing atmospheric correction..."
    atcor(fili=hazeout,                             # Haze corrected input
          asensor=sen2,                             # Sentinel-2
          maskfili=piximage,                        # Mask file
          atmdef="Maritime",                        # Atmosphere type
          atmcond="summer",                         # Atmosphere conditions
          outunits="16bit_Reflectance",             # Output
          filo=atcorout)                            # Corrected pix
    print "%s atmospheric correction completed." % piximage


# ------------------------------------------------------------------------------------------------------------------- #
# Define make_pca() function:                                                              -- Run on unmodified image
#   1. Generate a linear stretch LUT for mosaicked pix
#   2. Apply LUT enhancement to pix mosaic
# Parameters:
#   merged_input    - The merged input PIX format file with all bands.
#   identifier      - A unique naming identifier for report output.
# Note:
#   Some tweaks here to ensure that the PCA stats report is output to the project workspace, instead of the default
#   PCI folder on the C:\ Drive. The code for this section was adapted from sample at
#   https://support.pcigeomatics.com/hc/en-us/community/posts/203566673-Write-report-to-file-in-python
#   (Shawn Melamed, 2015)
# ------------------------------------------------------------------------------------------------------------------- #

def make_pca(merged_input, pca_out, identifier):
    print "Starting Principal Component Analysis for file %s" % identifier
    pca_rep = os.path.join(pcadir, "PCA_" + identifier + "_report.txt")
    fexport(fili=merged_input,
            filo=pca_out,
            dbic=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            ftype="PIX")
    try:
        Report.clear()                                          # Clear report file
        enableDefaultReport(pca_rep)                            # Change output folder location

        pcimod(file=pca_out,
               pciop="ADD",
               pcival=[0, 0, 3])                                # Add 3 16 bit unsigned channels
        pca(file=pca_out,
            dbic=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],               # Use first ten bands
            eign=[1, 2, 3],                                     # Output first three eigenchannels
            dboc=[11, 12, 13],                                  # Output to 3 new channels
            rtype="LONG")                                       # Output extended report format
    except PCIException, e:
        print e
    finally:
        enableDefaultReport('term')  # Close the report file

    print "PCA for %s completed." % identifier


# ------------------------------------------------------------------------------------------------------------------- #
# Define enhance_pca() function
#   1. Generate a linear stretch LUT for the PCA result.
#   2. Apply LUT enhancement to PCA and output to new file.
# Parameters:
#   pcain   - The input PIX format file that make_pca() was run on.
#   pcaout  - The output file for the enhanced PCA composite.
# ------------------------------------------------------------------------------------------------------------------- #
def enhance_pca(pcain, pcaout, identifier):
    print "Generating look-up tables for file %s" % identifier
    stretch(file=pcain,
            dbic=[14],              # Stretch band 14
            dblut=[],
            dbsn="LinLUT",
            dbsd="Linear Stretch",
            expo=[1])               # Linear stretch
    stretch(file=pcain,
            dbic=[15],              # Stretch band 15
            dblut=[],
            dbsn="LinLUT",
            dbsd="Linear Stretch",
            expo=[1])               # Linear stretch
    stretch(file=pcain,
            dbic=[16],              # Stretch band 16
            dblut=[],
            dbsn="LinLUT",
            dbsd="Linear Stretch",
            expo=[1])               # Linear stretch
    print "LUT generation complete."
    print "Applying LUT enhancement..."
    lut(fili=pcain,
        dbic=[11, 12, 13],          # Use bands (14,15,16)
        dblut=[2, 3, 4],            # LUT segments
        filo=pcaout,                # Output mosaic
        datatype="16U",             # 16-bit unsigned
        ftype="TIF")                # Tif output
    print "PCA enhancement for %s complete." %identifier


# ------------------------------------------------------------------------------------------------------------------- #
# Define coastline() function:                                              -- Must be run AFTER make_pca() completes
#   1. Export PCA layers to scratch pix file.
#   2. Add layer for classification result
#   3. Run unsupervised k-means clustering algorithm and output to new layer
#   4. Export classification raster to polygon shapefile
#   5. Select Sable Island polygon(s) that contain selection points (selection_polygons.shp)
#   6. Convert to polyline format and smooth line to remove zig-zag from raster cells.
# Parameters:
#   pixin           - The input PIX format file with PCA output layers.
#   coastscr        - The output scratch pix file location for the classification layer.
#   polygonout      - The output polygon format vector file.
#   lineout         - The output polyline format vector file.
#   lineout_smooth  - The output polylines with a line smoothing algorithm applied.
#   identifier      - Unique identifier string read from input file name.
# ------------------------------------------------------------------------------------------------------------------- #
# TODO see if there is any way to improve result - avoid inclusion of surf action on south side of island
def coastline(pixin, polygonout, lineout, lineout_smooth, identifier):
    print "Generating coastline classification..."
    id_string = "Coastline from file %s." % identifier
    coastscr = os.path.join(coastdir, identifier + "_coastline.pix")
    fexport(fili=pixin,                                             # Input with PCA
            filo=coastscr,                                          # Output scratch file
            dbiw=[],
            dbic=[11, 12, 13],                                      # PCA channels
            dbib=[],
            dbvs=[],
            dblut=[],
            dbpct=[],
            ftype="PIX",                                            # PIX filetype
            foptions="")
    pcimod(file=coastscr,                                           # Output scratch PIX file
           pciop='ADD',                                             # Modification mode "Add"
           pcival=[0, 2, 0, 0])                                     # Task - add two 16U channels
    kclus(file=coastscr,                                            # Run classification on scratch file
          dbic=[1, 2, 3],                                           # Use three PCA layers
          dboc=[4],                                                 # Output to blank layer
          numclus=[2],                                              # Two clusters - land, ocean
          seedfile='',
          maxiter=[20],
          movethrs=[],
          siggen="YES",
          backval=[],
          nsam=[])
    ras2poly(fili=coastscr,                                         # Use scratch PIX file
             dbic=[4],                                              # Use classification channel
             filo=polygonout,                                       # Polygon SHP output location
             smoothv="YES",                                         # Smooth boundaries
             dbsd=id_string,                                        # Layer description string
             ftype="SHP",                                           # Shapefile format
             foptions="")
    selpoints = os.path.join(workingdir,"selection_points","selection_polygons.shp")
    workspace = os.path.join(workingdir,"sable.gdb")                # Define GDB workspace
    polygonout_lyr = identifier + "_polygon_lyr"                    # Define feature layer name for polygon output
    arcpy.env.workspace = workspace                                 # Set default workspace
    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = "PROJCS['WGS_1984_UTM_Zone_20N',GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',\
    SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],\
    PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',0.0],PARAMETER\
    ['Central_Meridian',-63.0],PARAMETER['Scale_Factor',0.9996],PARAMETER['Latitude_Of_Origin',0.0],UNIT['Meter',1.0]]"
    arcpy.MakeFeatureLayer_management(polygonout, polygonout_lyr)   # Make polygon feature layer
    arcpy.AddField_management(in_table=polygonout,                  # Add new dissolve field
                              field_name="DISV",
                              field_type="SHORT",
                              field_precision=1,
                              field_scale=0,
                              field_is_nullable="NULLABLE",
                              field_is_required="NON_REQUIRED")
    cb = "def calDisv(area):\\n    if area > 1000000000:\\n        return 0\\n    elif area < 1000000000:\\n        return 1"
    arcpy.CalculateField_management(in_table=polygonout,            # Calculate dissolve field
                                    field="DISV",
                                    expression="calDisv(!Area!)",   # =0 if Ocean, =1 otherwise
                                    expression_type="PYTHON",
                                    code_block=cb)
    polygons_dissolved = identifier + "_poly_dissolved"
    arcpy.Dissolve_management(in_features=polygonout,               # Dissolve island polygons
                              out_feature_class=polygons_dissolved,
                              dissolve_field="DISV",
                              multi_part="SINGLE_PART",
                              unsplit_lines="DISSOLVE_LINES")
    polygondisv_lyr = identifier + "_polygon_disv_lyr"
    arcpy.MakeFeatureLayer_management(polygons_dissolved, polygondisv_lyr)  # Make polygon feature layer
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=polygondisv_lyr,
                                            selection_type="NEW_SELECTION",
                                            where_clause="DISV=1")
    island_poly_dissolved = identifier + "island_poly_dissolved"
    arcpy.CopyFeatures_management(in_features=polygondisv_lyr,
                                  out_feature_class=island_poly_dissolved)
    island_poly_disv_lyr = identifier + "_isl_poly_disv_lyr"
    arcpy.MakeFeatureLayer_management(island_poly_dissolved, island_poly_disv_lyr)  # Make polygon feature layer
    # Select island polygons that contain selection circle polygons (small, basically points).
    # These points are placed where the island is likely to exist.
    # Remove selection of features larger than 1B sq. m - this feature most likely represents ocean.
    try:                                                    # Does feature layer 'selpoints_lyr' exist yet?
        arcpy.SelectLayerByLocation_management(island_poly_disv_lyr,'CONTAINS','selpoints_lyr','','NEW_SELECTION')
    except:                                                 # Didn't work, so create 'selpoints_lyr' first
        arcpy.MakeFeatureLayer_management(selpoints, 'selpoints_lyr')
        arcpy.SelectLayerByLocation_management(island_poly_disv_lyr, 'CONTAINS', 'selpoints_lyr', '', 'NEW_SELECTION')

    # Convert polygon features to polyline
    arcpy.PolygonToLine_management(island_poly_disv_lyr,lineout,'IDENTIFY_NEIGHBORS')

    # Smooth line features to fix zig-zag from raster cells
    arcpy.cartography.SmoothLine(lineout,lineout_smooth,"PAEK",50,"")
    # TODO add function to copy polygon and line shapefiles to GDB feature class
    os.remove(coastscr)
    return lineout_smooth


# ------------------------------------------------------------------------------------------------------------------- #
# Define land_cover() function:                                              -- Must be run AFTER make_pca() completes
#   1. Export PCA layers to scratch pix file.
#   2. Add layer for classification result
#   3. Run unsupervised k-means clustering algorithm and output to new layer
#   4. Rescale RGB and Classification layers to 8-bit for use with pctmake()
#   5. Use pctmake() to automatically generate a colour table from the rgb image layers.
#   6. Export classification with colour table.
#   7. Export classification as vector shapefile format.
# Parameters:
#   pixin           - The input PIX format file with PCA output layers.
#   vout            - The output classified vector file in SHP format.
#   rout            - The output classified raster in TIF format.
#   identifier      - Unique identifier string read from input file name.
# ------------------------------------------------------------------------------------------------------------------- #
def land_cover(pixin, vout, rout, identifier):
    start_time = time.time()                                        # Start timer
    print "Generating land cover classification..."
    pct_string = "PCT generated using RGB channels from file %s" % identifier
    id_string = "Classification from file %s." % identifier
    landscr = os.path.join(landcoverdir, identifier + "_landcover.pix")     # Scratch pix file
    rgb8bit = os.path.join(landcoverdir, identifier + "_rgb8bit.pix")       # Rescaled 8-bit pix file
    fexport(fili=pixin,                                             # Input with PCA
            filo=landscr,                                           # Output scratch file
            dbiw=[],
            dbic=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],       # Use all channels
            dbib=[],
            dbvs=[],
            dblut=[],
            dbpct=[],
            ftype="PIX",                                            # PIX filetype
            foptions="")
    pcimod(file=landscr,                                            # Output scratch PIX file
           pciop='ADD',                                             # Modification mode "Add"
           pcival=[0, 2, 0, 0])                                     # Task - add two 16U channels
    kclus(file=landscr,                                             # Run classification on scratch file
          dbic=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],         # Use all image layers
          dboc=[14],                                                # Output to blank layer
          numclus=[24],                                             # 24 clusters (not all will be used, but
          seedfile='',                                              # this avoids cluster confusion
          maxiter=[20],
          movethrs=[0.01],
          siggen="YES",                                             # Save signature layers
          backval=[],
          nsam=[])
    print "Land cover classification for file %s completed." % identifier
    print "Creating a colour table for classification result..."
    scale(fili=landscr,                                             # Rescale layers to 8-bit for use with pctmake
          filo=rgb8bit,
          dbic=[1, 2, 3, 14],                                       # Rescale RGB and classification layer
          dboc=[],
          sfunct="LIN",
          datatype="8U",                                            # Scale to 8-bit unsigned
          ftype="PIX")                                              # PIX format
    stretch(file=rgb8bit,                                           # Creat lookup tables for histogram enhancement
            dbic=[1],                                               # Stretch band 1
            dblut=[],
            dbsn="LinLUT",
            dbsd="Linear Stretch",
            expo=[1])                                               # Linear stretch
    stretch(file=rgb8bit,
            dbic=[2],                                               # Stretch band 2
            dblut=[],
            dbsn="LinLUT",
            dbsd="Linear Stretch",
            expo=[1])                                               # Linear stretch
    stretch(file=rgb8bit,
            dbic=[3],                                               # Stretch band 3
            dblut=[],
            dbsn="LinLUT",
            dbsd="Linear Stretch",
            expo=[1])                                               # Linear stretch
    pctmake(file=rgb8bit,                                           # Make Colour table from rescaled RGB
            dbic=[3, 2, 1],                                         # RGB layers
            dblut=[4, 3, 2],                                        # Apply LUT stretch enhancement
            dbtc=[4],                                               # Classification layer
            dbpct=[],                                               # Make new PCT
            mask=[],
            dbsn="TC_PCT",                                          # PCT name
            dbsd=pct_string)                                        # PCT description
    print "Colour table generated from RGB layers and applied to %s classification result." % identifier
    print "Exporting classified raster to TIF format..."
    fexport(fili=rgb8bit,                                           # Export raster
            filo=rout,                                              # Raster output location
            dbic=[4],                                               # Classification channel
            dbpct=[5],                                              # Colour table channel (2,3,4 are LUT)
            ftype="TIF",                                            # TIF format
            foptions="")
    print "Raster export complete. Wrote to %s." % rout
    print "Exporting classification to shapefile..."
    ras2poly(fili=rgb8bit,                                          # Export to vector
             dbic=[4],                                              # Use classification channel
             filo=vout,                                             # Vector output location
             smoothv="NO",                                          # Don't smooth boundaries
             dbsd=id_string,                                        # Layer description string
             ftype="SHP",                                           # Shapefile format
             foptions="")
    print "Vector export complete. Wrote to %s." % vout
    os.remove(landscr)                                              # Delete intermediate PIX files
    os.remove(rgb8bit)
    completion_time = time.time() - start_time                      # Calculate time to complete
    print "Land cover classification process completed for image %s in %i seconds." % (identifier, completion_time)
    # TODO add function to copy polygon and raster to file GDB


def main():
    total_start_time = time.time()
    prep_workspace(pixdir, workspace_list)                      # Prepare workspace

    pixlist = os.listdir(pixdir)                                # Read converted PIX files to list
    pixfiles_m = []                                             # Initialize list of 10m*10m converted files
    pixfiles60 = []                                             # Initialize list of 60m*60m converted files

    for i in range(len(pixlist)):
        name_fields = pixlist[i].split("_")                     # Split filenames by underscore
        res = name_fields[2]                                    # Get image resolution from name
        itype = name_fields[3][:-4]                             # Get image type from name
        if res == "60m":                                        # Add 60m atmospheric bands to list
            p60_add = os.path.join(pixdir, pixlist[i])
            pixfiles60.append(p60_add)
        if itype == "merged":                                   # Add 10m and resampled 20m image stack to list
            pm_add = os.path.join(pixdir, pixlist[i])
            pixfiles_m.append(pm_add)

#    for i in range(len(pixfiles60)):
#        id_fields = pixfiles60[i].split("_")
#        mission = (id_fields[0])[-3:]
#        date = id_fields[1]
#        iid = mission + "_" + date

#        cloud_bitmap = os.path.join(maskdir, iid + "_clouds.pix")
#        mask_clouds(pixfiles60[i], cloud_bitmap, iid)

    for i in range(len(pixfiles_m)):
        id_fields = pixfiles_m[i].split("_")
        mission = (id_fields[0])[-3:]
        date = id_fields[1]
        iid = mission + "_" + date

        hzrm_merge = os.path.join(pixdir, iid + "_hzrm.pix")
        atcor_merge = os.path.join(corrdir, iid + "_atcor.pix")
        coastshp = os.path.join(coastdir, iid + "_coastline.shp")
        coastpoly = os.path.join(coastdir, iid + "_coastline_polygons.shp")
        coastsmooth = os.path.join(coastdir, iid + "_coastline_smoothed.shp")
        landshp = os.path.join(landcoverdir, iid + "_landcover.shp")
        landtif = os.path.join(landcoverdir, iid + "_landcover.tif")
        pca_image = os.path.join(pcadir, iid + "_pca.pix")


#        correction(pixfiles_m[i], hzrm_merge, atcor_merge)
        make_pca(pixfiles_m[i], pca_image, iid)
        land_cover(pca_image, landshp, landtif, iid)
#        coastline(pca_image, coastpoly, coastshp, coastsmooth, iid)

    total_completion_time = time.time() - total_start_time
    tct_minutes = total_completion_time / 60
    print "Image processing completed in %i minutes." % tct_minutes


# ------------------------------------------------------------------------------------------------------------------- #
# Mainline
#   - Loop to stop script from autorunning if user is unaware of file
#     deletion at beginning of script.
# ------------------------------------------------------------------------------------------------------------------- #

print "="*50                                    # Header
print "Sentinel-2 Image Processing Script"
print "="*50

print "Current working directory is %s" % workingdir
print "Operations will be performed on PIX directory %s" % pixdir
print "Running this script will DELETE existing data from output folders!"
start = "Y"
while start[0].upper() != "N":                  # Start a loop
    start = raw_input("Continue? (Y/N):")
    if len(start) == 0:                         # Stop if no answer
        start = "N"                             # Exit script
        print " ----- Goodbye"*2, "-----"
    elif start[0].upper() == "Y":               # Start if starts with y
        main()                                  # Run main()
        start = "N"
    else:
        start = "N"                             # Kill loop
        print " ----- Goodbye"*2, "-----"       # Exit script
