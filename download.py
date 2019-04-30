# ====================================================================== #
# Script Name:	data_prep.py
# Author:	    Brian Laureijs
# Purpose:      Download Sentinel-2 imagery
# Date:         20190205
# Version:      0.1.0
# ====================================================================== #
# Import Libraries                              # Requirements:
# ====================================================================== #
import getpass
import subprocess
import os
import datetime
import json
import collections
ss_inst = False
while ss_inst == False:
    try:
        from sentinelsat import SentinelAPI
        from sentinelsat import read_geojson
        from sentinelsat import geojson_to_wkt
        ss_inst = True
    except:
        print "Sentinel Python library not found. Installing now."
        if os.path.isdir(r"C:\python27\ArcGIS10.6\Scripts") == True:
            subprocess.call([r'install_sentinelsat_arcdir.bat'])
        elif os.path.isdir(r"C:\python27\scripts") == True:
            subprocess.call([r'install_sentinelsat.bat'])


def getlogin():
    print "\nThe Sentinelsat Library requires a Copernicus Open Access Hub user ID"
    print "and password. Please enter your credentials here."
    print "\nIf you don't have a login, please register at https://scihub.copernicus.eu/\n"
    coah_user = raw_input("User Name:")
    coah_pass = getpass.getpass("Password:")
    login = SentinelAPI(coah_user, coah_pass, 'https://scihub.copernicus.eu/dhus')
    return login


def download_single(api):
    print "Download a single product by ID (example: 711cd44e-2948-4f25-a669-05f9b7a6291e)"
    id = raw_input("Enter the product ID :")
    api.download(id)


def search(api):
    footprint = geojson_to_wkt(read_geojson('clip_ext.geojson'))
    tiles = ['T20TQP']
    query_kwargs = {
            'platformname': 'Sentinel-2',
            'producttype': 'S2MSI1C',
            'date':('NOW-14DAYS','NOW')}
    products = collections.OrderedDict()
    for tile in tiles:
        kw = query_kwargs.copy()
        kw['tileid'] = tile
        pp = api.query(**kw)
        products.update(pp)
    api.get_products_size(products)

    #productsB = api.query(footprint,
    #                     date=('20190212', datetime.date(2019, 02, 12)),
    #                     platformname='Sentinel-2',
    #                     cloudcoverpercentage=(0,100))
    print json.dumps(products)


api = getlogin()

#download_single(api)

search(api)
