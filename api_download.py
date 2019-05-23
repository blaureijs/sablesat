# =================================================================================================================== #
# Script Name:	api_download.py
# Author:	    Brian Laureijs
# Purpose:      Download Sentinel-2 imagery
# Date:         20190523
# Version:      0.2.0
# =================================================================================================================== #
# Import Libraries                                                      # Requirements:
# =================================================================================================================== #
import getpass                                                          # Copernicus API login
import os                                                               # Directory and file manipulation
import sentinelsat                                                      # Copernicus API access
import untangle                                                         # Read copernicus cart XML download
import zipfile                                                          # Unzip downloads
import time                                                             # Time to complete

# ------------------------------------------------------------------------------------------------------------------- #
# Define path variables
# ------------------------------------------------------------------------------------------------------------------- #
workingdir = os.getcwd()
apidir = os.path.join(workingdir, "sentinel_api")
inputdir = os.path.join(workingdir, "input")


# ------------------------------------------------------------------------------------------------------------------- #
# Define function getlogin():
#   1. Ask for Copernicus username and password.
#   2. Return API login element.
# ------------------------------------------------------------------------------------------------------------------- #
def getlogin():
    print "\nThis script requires a Copernicus Open Access Hub user ID and password."
    print "Please enter your credentials here.\n"
    print "If you don't have a login, you can register at https://scihub.copernicus.eu/\n"
    print "\nWarning: Some python interpreters will echo password input or fail after username input."
    print "To avoid this, run api_download.py from Command Prompt or Powershell.\n"
    coah_user = raw_input("User Name:")
    coah_pass = getpass.getpass("Password:")
    login = sentinelsat.SentinelAPI(coah_user, coah_pass, 'https://scihub.copernicus.eu/dhus')
    return login


# ------------------------------------------------------------------------------------------------------------------- #
# Define function download_single():
#   1. Ask for a product ID.
#   2. Download that product.
# Parameters:
#   api     - The login credentials assigned by getlogin().
# ------------------------------------------------------------------------------------------------------------------- #
def download_single(api):
    print "Download a single product by Copernicus UUID (example: 711cd44e-2948-4f25-a669-05f9b7a6291e)"
    try:
        id = raw_input("Enter the product ID :")
        print "Starting product download..."
        api.download(id)
    except:
        print "An error occurred. Make sure your ID string is valid. Enter the full string, without quotes."


# ------------------------------------------------------------------------------------------------------------------- #
# Define download_cart() function
#   1. Read 'products.meta4' file from cart download.
#   2. Download products in cart by UUID.
# Parameters:
#   api     - The login credentials assigned by getlogin().
# ------------------------------------------------------------------------------------------------------------------- #
def download_cart(api):
    total_start_time = time.time()
    xml_path = os.path.join(workingdir, 'products.meta4')
    uuid_list = []
    if os.path.isfile(xml_path):
        print 'Copernicus cart download file found in %s.' % workingdir
        xml = untangle.parse(xml_path)                                  # Read the XML file
        for i in range(len(xml.metalink.file)):
            download = xml.metalink.file[i]                             # Look at file i in XML list
            url = str(download.url)                                     # Get the URL element as string
            url_sp = url.split("'")                                     # Isolate the UUID code
            uuid = url_sp[1]                                            # Assign uuid
            uuid_list.append(uuid)                                      # Append uuid code to a list
        for i in range(len(uuid_list)):
            start_time = time.time()
            id = uuid_list[i]
            api.download(id)                                            # Download incrementally by UUID
            completion_time = time.time() - start_time
            print "Download completed in %i seconds." % completion_time
        total_completion_time = time.time() - total_start_time
        tct_mins = total_completion_time / 60
        print "All downloads completed in %i minutes." % tct_mins
    else:
        print 'The Copernicus cart file was not found. Copy the "products.meta4" file to %s' % workingdir


# ------------------------------------------------------------------------------------------------------------------- #
# Define unzip() function
#   1. Find downloaded zip files in working directory.
#   2. Extract zip files to input directory.
# ------------------------------------------------------------------------------------------------------------------- #
def unzip():
    zipfiles = []
    total_start_time = time.time()
    allfiles = os.listdir(workingdir)
    for i in range(len(allfiles)):
        if (allfiles[i])[-4:] == '.zip':
            zipfiles.append(allfiles[i])                                # Add zip files to a list
    for i in range(len(zipfiles)):
        start_time = time.time()
        with zipfile.ZipFile(zipfiles[i],'r') as zipobject:             # Read each zipfile
            zipobject.extractall(inputdir)                              # Extract to the input folder
        os.remove(zipfiles[i])                                          # Clean up the downloaded zip
        completion_time = time.time() - start_time
        print 'File %s extracted to %s in %i seconds.' % (zipfiles[i], inputdir, completion_time)
    total_completion_time = time.time() - total_start_time
    tct_mins = total_completion_time / 60
    print "All files unzipped in %i minutes." % tct_mins


# ------------------------------------------------------------------------------------------------------------------- #
# Define main() function:
#   1. Run selected download function.
# Parameters:
# mode  - The download function to run, based on user input.
# ------------------------------------------------------------------------------------------------------------------- #
def main(mode):
    if mode == 1:
        download_single(api)
        unzip()
    elif mode == 2:
        download_cart(api)
        unzip()


# ------------------------------------------------------------------------------------------------------------------- #
# Mainline
# ------------------------------------------------------------------------------------------------------------------- #

print "-"*50
print "Copernicus Data Download Script"
print "-"*50
print ""

api = getlogin()
global api

print "You can download a single product by ID, or products contained in a cart file.\n"
print "Warning: Files will be downloaded to the working directory of the Command Prompt."
print "Change the directory to the Sable project location to ensure files are downloaded to the correct folder.\n"
print "Please make a selection from these options:"
print "-"*50
print "1. Download single product by UUID (universally unique identifier)."
print "2. Download all products in a Copernicus cart download file, 'products.meta4'."
print "-"*50
goodsel = False
while not goodsel:
    try:
        mode_sel = raw_input("Enter your selection (1 or 2):")
        mode_sel =int(mode_sel)
        if mode_sel > 0 and mode_sel < 3:
            goodsel = True
            again = "Y"
            if mode_sel == 1:
                main(1)
            if mode_sel == 2:
                main(2)
            while again[0].upper() == "Y":
                again = raw_input("Download more files? (Y/N):")
                if len(again) == 0:
                    again = "Y"
                elif again[0].upper() == "Y":
                    mode_sel = raw_input("Enter your selection (1 or 2):")
                    mode_sel = int(mode_sel)
                    if mode_sel > 0 and mode_sel < 3:
                        goodsel = True
                        again = "Y"
                        if mode_sel == 1:
                            main(1)
                        if mode_sel == 2:
                            main(2)
                else:
                    again = "N"
                    print "-"*50
                    print "Goodbye!"
                    print "-"*50
        else:
            print "Invalid entry - please enter 1 or 2."
            goodsel = False
    except:
        print "Invalid entry - please enter 1 or 2."
        goodsel = False
