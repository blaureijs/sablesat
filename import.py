# =================================================================================================================== #
# Script Name:	import.py
# Author:	    Brian Laureijs
# Purpose:      Convert Sable Island Sentinel-2 imagery to PIX format for further processing.
# Date:         20190502
# Version:      0.2.0
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
from pci.poly2bit import *                           # Polygon to Bitmap conversion

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
        
        pix10 = "pix/" + mission + "_" + date + "_10m_unmerged.pix"
        pixfiles10.append(pix10)
        pix20 = "pix/" + mission + "_" + date + "_20m_unmerged.pix"
        pix_merged = "pix/" + mission + "_" + date + "_10m_merged.pix"
        pixfiles_m.append(pix_merged)
        pix60 = "pix/" + mission + "_" + date + "_60m_atmospheric.pix"
        pixfiles60.append(pix60)

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

print "="*50                                    # Header
print "Sentinel-2 File Processing Script"
print "="*50

print "Current working directory is %s" % workingdir
print "Converted PIX directory is %s" % pixdir
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
