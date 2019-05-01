# =================================================================================================================== #
# Script Name:	data_prep.py
# Author:	    Brian Laureijs
# Purpose:      Convert and run functions on Sentinel-2 imagery for Sable
# Date:         20190429
# Version:      0.1.0
# Notice:       Created for academic assessment. Do not re-use or
#               redistribute without permission from author.
# =================================================================================================================== #
# Import Libraries                                  # Requirements:
# =================================================================================================================== #
import os                                           # Directory and
import shutil                                       # file manipulation
import arcpy                                        # Vector file manipulation
from pci.fimport import *                           # PIX format conversion
from pci.clip import *                              # Clipping to AOI
from pci.resamp import *                            # Resample 60m bands
from pci.datamerge import *                         # Merging bands
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
from pci.ras2bit import *                           # Raster to Bitmap conversion

# ------------------------------------------------------------------------------------------------------------------- #
# Declare global variables
# ------------------------------------------------------------------------------------------------------------------- #
global sen2                                         # Sensor name used in pci correction
sen2 = "Sentinel-2"                                 # functions.
global pixfiles10                                   # Initialize list of converted 10m
pixfiles10 = []
global pixfiles_m                                   # Initialize list of full band pix
pixfiles_m = []
global pixfiles60
pixfiles60 = []
global workspace_list                               # Workspace directory list
workspace_list = []                                 # for iterative folder preparation

# ------------------------------------------------------------------------------------------------------------------- #
# Initialize path variables:
# ------------------------------------------------------------------------------------------------------------------- #
workingdir = os.getcwd()                            # Get current working directory
indir = os.path.join(workingdir, "input")           # Sentinel input files
clipvec = os.path.join(workingdir, "clip_extent", "clip_ext.pix")

mergedir = os.path.join(workingdir, "mergefiles")   # File lists for layer-stacking image
workspace_list.append(mergedir)

corrdir = os.path.join(workingdir, "atcor")         # Corrected pix output
workspace_list.append(corrdir)

pixdir = os.path.join(workingdir, "pix")            # Pix workspace
workspace_list.append(pixdir)

pcadir = os.path.join(workingdir, "pca")            # PCA output
workspace_list.append(pcadir)

coastdir = os.path.join(workingdir, "coastline")    # Coastline output
workspace_list.append(coastdir)

maskdir = os.path.join(workingdir, "masks")         # Cloud mask output
workspace_list.append(maskdir)

     
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
            chanopt="p,p,p,c,p,p,p,c,c,c,",    # Process or copy? (channels 1-13)
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
# Define readtopix() function
#   1. Read folders from input directory to list.
#   2. Append XML and band resolutions so PCI can read input.
#   3. Read Sentinel-2 files to Pix format.
#   4. Append pix files to list.
# Parameters:
#   indir   - The directory to read raw files from.
# ------------------------------------------------------------------------------------------------------------------- #
def readtopix(indir):
    infiles = os.listdir(indir)                 # List input folders
    for i in range(len(infiles)):               # Add path for 10m S2 Bands
        fili_10 = "input/" + infiles[i] + "/MTD_MSIL1C.xml?r=%3ABand+Resolution%3A10M"
        fili_20 = "input/" + infiles[i] + "/MTD_MSIL1C.xml?r=%3ABand+Resolution%3A20M"
        fili_60 = "input/" + infiles[i] + "/MTD_MSIL1C.xml?r=%3ABand+Resolution%3A60M"

        name_fields = infiles[i].split("_")     # Set up fields for filename
        mission = name_fields[0]
        date = (name_fields[2])[:8]

        pix10full = "pix/" + mission + "_" + date + "_10m_full.pix"
        pix20full = "pix/" + mission + "_" + date + "_20m_full.pix"
        pix60full = "pix/" + mission + "_" + date + "_60m_full.pix"
        
        pix10 = "pix/" + mission + "_" + date + "_10m.pix"
        pixfiles10.append(pix10)
        pix20 = "pix/" + mission + "_" + date + "_20m.pix"
        pix_merged = "pix/" + mission + "_" + date + "_10m_merged.pix"
        pixfiles_m.append(pix_merged)
        pix60 = "pix/" + mission + "_" + date + "_atmospheric_60m.pix"
        pixfiles60.append(pix60)
        pix60resamp = "pix/" + mission + "_" + date + "_atmospheric_60m_resamp_10m.pix"

        print "Starting pix conversion file %s_%s." %(mission,date)
        fimport(fili_10, pix10full)         # Import R,G,B,NIR bands
        fimport(fili_20, pix20full)         # Import RE,NIR,SWIR bands
        fimport(fili_60, pix60full)         # Import Coastal, Vapour, Cirrus

        clip(fili=pix10full,
             dbic=[1, 2, 3, 4],
             dbsl=[],
             sltype="",
             filo=pix10,
             ftype="PIX",
             foptions="",
             clipmeth="LAYERVEC",
             clipfil=clipvec,
             cliplay=[2])

        clip(fili=pix20full,
             dbic=[1, 2, 3, 4, 5, 6],
             dbsl=[],
             sltype="",
             filo=pix20,
             ftype="PIX",
             foptions="",
             clipmeth="LAYERVEC",
             clipfil=clipvec,
             cliplay=[2])
        
        clip(fili=pix60full,
             dbic=[1, 2, 3],
             dbsl=[],
             sltype="",
             filo=pix60,
             ftype="PIX",
             foptions="",
             clipmeth="LAYERVEC",
             clipfil=clipvec,
             cliplay=[2])

        os.remove(pix10full)
        os.remove(pix20full)
        os.remove(pix60full)

        # The order of data in merge list file matters:
        # 10m bands first results in resampling of 20m resolution
        # to 10m resolution. Avoids data loss due to resampling of 10m to 20.
        mergefile_name = mission + "_" + date + "_merge.txt"
        mergefile_path = os.path.join(mergedir,mergefile_name)

        path10 = os.path.join(workingdir,pix10)
        path20 = os.path.join(workingdir,pix20)

        mergefile = open(mergefile_path, "w")
        mergefile.write('"' + path10 + '"' + "\n")
        mergefile.write('"' + path20 + '"')
        mergefile.close()

        datamerge(mfile=mergefile_path,         # Merge 10m bands and 20m bands into one pix file
                  dbic=[],
                  filo=pix_merged,
                  ftype="PIX",
                  foptions="",
                  extent="UNION",
                  nodatval=[],
                  resample="NEAR")

        ## rscale = 0.16666                        # Resampling factor for 60m - 10m
        ## resamp(fili=pix60,                      # Resample 60m file to 10m for future interoperability
        ##       dbic=[1, 2, 3],
        ##       dbsl=[1, 2, 3],
        ##       sltype="ALL",
        ##       filo=pix60resamp,
        ##       ftype="PIX",
        ##       pxszout=[rscale,rscale])


        print "Pix conversion completed for %s_%s:" %(mission,date)
        print "Wrote files to:\n\t%s\n\t%s\n\t%s\n\t%s" %(pix10, pix20, pix60resamp, pix_merged)
    

# ------------------------------------------------------------------------------------------------------------------- #
# Define make_pca() function:                    -- RUN ON RAW DATA ONLY
#   1. Generate a linear stretch LUT for mosaicked pix
#   2. Apply LUT enhancement to pix mosaic
# Parameters:
#   merged_input    - The merged input PIX format file with all bands.
#   identifier      - A unique naming identifier for report output.
# Note:
#   Some tweaks here to ensure that the PCA stats report is output to
#   the project workspace, instead of the default folder on the C:\ Drive.
#   The code for this section was adapted from sample at
#   https://support.pcigeomatics.com/hc/en-us/community/posts/
#   203566673-Write-report-to-file-in-python (Shawn Melamed, 2015)
# ------------------------------------------------------------------------------------------------------------------- #

def make_pca(merged_input,pca_out,identifier):
    print "Starting Principal Component Analysis for file %s" %identifier
    pca_rep = os.path.join(pcadir, "PCA_"+ identifier + "_report.txt")
    fexport(fili=merged_input,
            filo=pca_out,
            dbic=[1,2,3,4,5,6,7,8,9,10],
            ftype="PIX")
    try:
        Report.clear()                          # Clear report file
        enableDefaultReport(pca_rep)            # Change output folder location

        pcimod(file=pca_out,
                pciop="ADD",
                pcival=[0,0,3])                 # Add 3 16 bit unsigned channels
        pca(file=pca_out,
            dbic=[1,2,3,4,5,6,7,8,9,10],        # Use first ten bands
            eign=[1,2,3],                       # Output first three eigenchannels
            dboc=[11,12,13],                    # Output to 3 new channels
            rtype="LONG")                       # Output extended report format
    except PCIException, e:
        print e
    finally:
        enableDefaultReport('term')             # Close the report file
    
    print "PCA for %s completed." %identifier


# ------------------------------------------------------------------------------------------------------------------- #
# Define mask_clouds() function                                             - Note 20190430 this is untested
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

def mask_clouds(pix60in, bitmapout, identifier):
    polygonout_name = identifier + "_cloud_polygons.shp"
    polygonout = os.path.join(maskdir,polygonout_name)
    rasterout_name = identifier + "_cloud_raster.tif"
    rasterout = os.path.join(maskdir,rasterout_name)
    id_string = "Cloud mask bitmap for file %s" % identifier
    pcimod(file=pix60in,                                            # Input 60m resolution atmospheric bands pix file
           pciop='ADD',                                             # Modification mode "Add"
           pcival=[0, 1, 0, 0])                                     # Task - add one 16U channels
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
    ras2poly(fili=pix60in,                                          # Use scratch PIX file
             dbic=[4],                                              # Use classification channel
             filo=polygonout,                                       # Polygon SHP output location
             smoothv="YES",                                         # Smooth boundaries
             dbsd=id_string,                                        # Layer description string
             ftype="SHP",                                           # Shapefile format
             foptions="")
    print "Shapefile conversion complete."
    print "Converting polygons to bitmap layer..."
    workspace = os.path.join(workingdir, "sable.gdb")               # Define GDB workspace
    polygonout_lyr = identifier + "_polygon_lyr"                    # Define feature layer name for polygon output
    arcpy.env.workspace = workspace                                 # Set default workspace
    arcpy.MakeFeatureLayer_management(polygonout, polygonout_lyr)   # Make polygon feature layer
    arcpy.SelectLayerByAttribute_management(polygonout_lyr, 'NEW_SELECTION', '"Area" < 1000000000')
    arcpy.PolygonToRaster_conversion(polygonout_lyr,"FID",rasterout,"MAXIMUM_AREA",1)
    ras2bit(fili=rasterout,                                         # Scratch tif file
            dbic=[1],                                               # Data channel
            filo=bitmapout,                                         # Output PIX file
            dbsd=id_string,                                         # Layer description
            ftype="PIX")
    print "Bitmap conversion complete. Output to \n\t%s" % bitmapout
    return bitmapout


# ------------------------------------------------------------------------------------------------------------------- #
# Define enhance_pca() function
#   1. Generate a linear stretch LUT for the PCA result.
#   2. Apply LUT enhancement to PCA and output to new file.
# Parameters:
#   pcain   - The input PIX format file that make_pca() was run on.
#   pcaout  - The output file for the enhanced PCA composite.
# ------------------------------------------------------------------------------------------------------------------- #
def enhance_pca(pcain, pcaout, identifier):
    print "Generating look-up tables for file %s" %identifier
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

def coastline(pixin, coastscr, polygonout, lineout, lineout_smooth, identifier):
    print "Generating coastline classification..."
    id_string="Coastline from file %s." % identifier
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
    arcpy.MakeFeatureLayer_management(polygonout,polygonout_lyr)    # Make polygon feature layer

    # Select island polygons that contain selection circle polygons (small, basically points).
    # These points are placed where the island is likely to exist.
    # Remove selection of features larger than 1B sq. m - this feature most likely represents ocean.
    try:                                                    # Does feature layer 'selpoints_lyr' exist yet?
        arcpy.SelectLayerByLocation_management(polygonout_lyr,'CONTAINS','selpoints_lyr','','NEW_SELECTION')
    except:                                                 # Didn't work, so create 'selpoints_lyr' first
        arcpy.MakeFeatureLayer_management(selpoints, 'selpoints_lyr')
        arcpy.SelectLayerByLocation_management(polygonout_lyr, 'CONTAINS', 'selpoints_lyr', '', 'NEW_SELECTION')
    arcpy.SelectLayerByAttribute_management(polygonout_lyr,'REMOVE_FROM_SELECTION','"Area" > 1000000000')

    # Convert polygon features to polyline
    arcpy.PolygonToLine_management(polygonout_lyr,lineout,'IDENTIFY_NEIGHBORS')

    # Smooth line features to fix zig-zag from raster cells
    arcpy.cartography.SmoothLine(lineout,lineout_smooth,"PAEK",50,"")

    os.remove(coastscr)
    return lineout_smooth

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
        print "Missing input folder!"
        print "Add unzipped input files to input folder"
    for i in range(len(folder_list)):
          if os.path.isdir(folder_list[i]) == True:
              print "Clearing \t%s" % folder_list[i]
              shutil.rmtree(folder_list[i])
              os.mkdir(folder_list[i])
          else:
              os.mkdir(folder_list[i])
              print "Created \t%s" % folder_list[i]


# ------------------------------------------------------------------------------------------------------------------- #
# Define mainline function
#   1. Clear folders if they already exist, create folders if missing
#   2. Read input to pix format
#   3.
# ------------------------------------------------------------------------------------------------------------------- #
def main():

    prep_workspace(indir, workspace_list)   # Prepare workspace
    
    readtopix(indir)                        # Convert raw input to pix

    for i in range(len(pixfiles60)):
        id_fields = pixfiles60[i].split("_")
        mission = (id_fields[0])[4:]
        date = id_fields[1]
        id = mission + "_" + date

        cloud_bitmap = os.path.join(maskdir,id + "_clouds.pix")

        mask_clouds(pixfiles60[i], cloud_bitmap, id)

    for i in range(len(pixfiles_m)):
        id_fields = pixfiles_m[i].split("_")
        mission = (id_fields[0])[4:]
        date = id_fields[1]
        id = mission + "_" + date

        hzrm_merge = os.path.join(pixdir,id + "_hzrm.pix")
        atcor_merge = os.path.join(corrdir,id + "_atcor.pix")
        coastshp = os.path.join(coastdir,id + "_coastline.shp")
        coastpoly = os.path.join(coastdir,id + "_coastline_polygons.shp")
        coastsmooth = os.path.join(coastdir,id + "_coastline_smoothed.shp")
        coastscratch = os.path.join(coastdir,id + "_coastline.pix")
        pca_image = os.path.join(pcadir,id + "_pca.pix")

        # correction(pixfiles_m[i], hzrm_merge, atcor_merge)
        # make_pca(pixfiles_m[i], pca_image, id)
        # coastline(pca_image, coastscratch, coastpoly, coastshp, coastsmooth, id)



main()

# ------------------------------------------------------------------------------------------------------------------- #
# Mainline
#   - Loop to stop script from autorunning if user is unaware of file
#     deletion at beginning of script.
# ------------------------------------------------------------------------------------------------------------------- #

# print "="*50                                    # Header
# print "Sentinel-2 Mosaicking Script"
# print "="*50

# print "This script should be run from %s" %workingdir
# print "Unzip Sentinel-2 input to %s" %indir
# print "Running this script will DELETE existing data"
# print "from corrected, mosaic, and pix folders!"
# start = raw_input("Continue? (Y/N):")
# while start[0].upper() <> "N":                  # Start a loop
#    if len(start) == 0:                         # Stop if no answer
#        start = "N"                             # Exit script
#        print " ----- Goodbye"*2, "-----"
#    elif start[0].upper() == "Y":               # Start if starts with y
#        main()                                  # Run main()
#    else:
#        start = "N"                             # Kill loop
#        print " ----- Goodbye"*2, "-----"       # Exit script

##for i in range(len(pixfiles10)):
##    hzrm10out = pixfiles10[i][:19] + "_hzrm.pix"
##    atcor10out = pixfiles10[i][:19] + "_atcor.pix"
##    correction(pixfiles20[i], hzrm10out, atcor10out)
