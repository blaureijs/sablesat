# =================================================================================================================== #
# Script Name:	import.py
# Author:	    Brian Laureijs
# Purpose:      Convert Sable Island Sentinel-2 imagery to PIX format for further processing.
# Date:         20190502
# Version:      0.2.1
# Notice:       Created for academic assessment. Do not re-use or redistribute without permission from author.
# =================================================================================================================== #
# Import Libraries                                  # Requirements:
# =================================================================================================================== #
import os                                           # Directory and
import shutil                                       # file manipulation
import time                                         # Timer function
from pci.fimport import *                           # PIX format conversion
from pci.clip import *                              # Clipping to AOI
from pci.datamerge import *                         # Merging bands

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
workingdir = os.getcwd()                            # Get current working directory
indir = os.path.join(workingdir, "input")           # Sentinel input files
clipvec = os.path.join(workingdir, "clip_extent", "clip_ext.pix")

mergedir = os.path.join(workingdir, "mergefiles")   # File lists for layer-stacking image
workspace_list.append(mergedir)

pixdir = os.path.join(workingdir, "pix")            # Pix workspace
workspace_list.append(pixdir)


# ------------------------------------------------------------------------------------------------------------------- #
# Define readtopix() function
#   1. Read folders from input directory to list.
#   2. Append XML and band resolutions so PCI can read input.
#   3. Read Sentinel-2 files to Pix format.
#   4. Append pix files to list.
# Parameters:
#   inputdir   - The directory to read raw files from.
# ------------------------------------------------------------------------------------------------------------------- #
def readtopix(inputdir):
    infiles = os.listdir(inputdir)                                  # List input folders
    for i in range(len(infiles)):                                   # Add paths for S2 band sets
        fili_10 = "input/" + infiles[i] + "/MTD_MSIL1C.xml?r=%3ABand+Resolution%3A10M"
        fili_20 = "input/" + infiles[i] + "/MTD_MSIL1C.xml?r=%3ABand+Resolution%3A20M"
        fili_60 = "input/" + infiles[i] + "/MTD_MSIL1C.xml?r=%3ABand+Resolution%3A60M"

        name_fields = infiles[i].split("_")                         # Set up fields for filenames
        mission = name_fields[0]
        date = (name_fields[2])[:8]

        pix10full = "pix/" + mission + "_" + date + "_10m_full.pix" # Set up paths for functions
        pix20full = "pix/" + mission + "_" + date + "_20m_full.pix"
        pix60full = "pix/" + mission + "_" + date + "_60m_full.pix"
        pix10 = "pix/" + mission + "_" + date + "_10m_unmerged.pix"
        pix20 = "pix/" + mission + "_" + date + "_20m_unmerged.pix"
        pix_merged = "pix/" + mission + "_" + date + "_10m_merged.pix"
        pix60 = "pix/" + mission + "_" + date + "_60m_atmospheric.pix"

        start_time = time.time()
        print "Starting pix conversion file %s_%s." %(mission,date)
        fimport(fili_10, pix10full)         # Import R,G,B,NIR bands
        fimport(fili_20, pix20full)         # Import RE,NIR,SWIR bands
        fimport(fili_60, pix60full)         # Import Coastal, Vapour, Cirrus

        clip(fili=pix10full,                # Clip 10m bands
             dbic=[1, 2, 3, 4],
             dbsl=[],
             sltype="",
             filo=pix10,
             ftype="PIX",
             foptions="",
             clipmeth="LAYERVEC",
             clipfil=clipvec,
             cliplay=[2])

        clip(fili=pix20full,                # Clip 20m bands
             dbic=[1, 2, 3, 4, 5, 6],
             dbsl=[],
             sltype="",
             filo=pix20,
             ftype="PIX",
             foptions="",
             clipmeth="LAYERVEC",
             clipfil=clipvec,
             cliplay=[2])
        
        clip(fili=pix60full,                # Clip 60m bands
             dbic=[1, 2, 3],
             dbsl=[],
             sltype="",
             filo=pix60,
             ftype="PIX",
             foptions="",
             clipmeth="LAYERVEC",
             clipfil=clipvec,
             cliplay=[2])

        os.remove(pix10full)                # Delete un-clipped images
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

        completion_time = time.time() - start_time
        print "Pix conversion completed for image %s_%s in %i seconds." % (mission, date, completion_time)
        print "Wrote files to:\n\t%s\n\t%s\n\t%s\n\t%s\n" % (pix_merged, pix10, pix20, pix60)


# ------------------------------------------------------------------------------------------------------------------- #
# Define prep_workspace() function
#   1. Check if "input" directory exists and prompt user if it does not
#   2. For rest of folders, create new if they do not exist, or delete contents and make new folder if they do.
# Parameters:
#   inputdir       - The input image file directory; has to be handled differently so contents are not deleted
#   folder_list - The list of output folders that should be cleared before processing is started.
# ------------------------------------------------------------------------------------------------------------------- #

def prep_workspace(inputdir,folder_list):
    if os.path.isdir(inputdir) == False:
        print "Missing input folder!"
        print "Add unzipped input files to input folder"
    for i in range(len(folder_list)):
        if os.path.isdir(folder_list[i]):
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
# ------------------------------------------------------------------------------------------------------------------- #
def main():
    total_start_time = time.time()
    prep_workspace(indir, workspace_list)
    readtopix(indir)
    total_completion_time = time.time() - total_start_time
    tct_minutes = total_completion_time / 60
    print "All images were converted to PIX format in %i minutes." % tct_minutes


# ------------------------------------------------------------------------------------------------------------------- #
# Mainline
#   - Loop to stop script from auto-running if user is unaware of file deletion at beginning of script.
# ------------------------------------------------------------------------------------------------------------------- #
print "="*50
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
