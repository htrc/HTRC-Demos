# Copyright 2013 The Trustees of Indiana University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import urllib
import sys
import os

import htrc_data_libs

'''
HTRC setting
'''
OAUTH2_CLIENT_ID = "_OgVnhUBwTVRXhYLB9r6xrFishsa"
OAUTH2_CLIENT_SECRET = "bZUr_VzhQmTYcSKfhc53UG9r6oka"
OA2_EPR = "https://silvermaple.pti.indiana.edu/oauth2/token?"
DATAAPI_EPR = "https://silvermaple.pti.indiana.edu:25443/data-api/volumes"
SOLR_METADATA_URL = "http://chinkapin.pti.indiana.edu:9994/solr/meta/select?q="
SOLR_OCR_URL = "http://chinkapin.pti.indiana.edu:9994/solr/ocr/select?q="


parser = argparse.ArgumentParser()
parser.add_argument("--getvolumes", nargs='+', help="download volumes from HTRC Data API", required=False)
parser.add_argument("--getvolumesid", nargs='+', help="download a list volume id from HTRC Solr", required=False)
parser.add_argument("--cleanvolumes", nargs='+', help="clean HTRC texts", required=False)
args = parser.parse_args()

if args.getvolumes:
    argv = args.getvolumes
    if (len(argv) != 2):
        print ("htrc_data_launcher.py --getvolumes <id-filename> <zip file>")
        sys.exit()
    
    id_file_path = argv[0]
    zipfilename = argv[1]
    fileExtension = os.path.splitext(zipfilename)[1]
    if (fileExtension != '.zip'):
        print("The output file extension should be zip, e.g., volume.zip. Change it and try again")
        sys.exit()
    
    id_list = []
    with open(id_file_path, 'r') as f:
        id_list = f.readlines()
        
#     req_options = {'concat':'true'}
    req_options = {}
    
    htrc_data_libs.download_volumes_to_zipfile( \
        zipfilename, DATAAPI_EPR, id_list, req_options, \
        OA2_EPR, OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET)
elif args.getvolumesid != None:
    argv = args.getvolumesid
    if (len(argv) != 2):
        print ("htrc_data_launcher.py --getvolumesid <query> <id-filename>")
        sys.exit()
    
    query = argv[0]
    outfile = argv[1]
    
    volume_ids = htrc_data_libs.get_volume_ids_from_solr(SOLR_METADATA_URL + urllib.quote(query))
    
    f = open(outfile, 'w')
    s1 = '\n'.join(volume_ids)
    f.write(s1)
    f.close()
elif args.cleanvolumes != None:
    """
    The cleanup procedure expects the texts to be organized as follows.
    /path/to/collections/book-1/000000001.txt
                             +/000000002.txt
                             ...
    /path/to/collections/book-2/000000001.txt
                              +/000000002.txt
                             ...
    """
    
    argv = args.cleanvolumes
    collection_dir = argv[0]
    
    htrc_data_libs.proc_htrc_coll(collection_dir)
else:
    print "Usage: htrc_data_launcher.py --getvolumes | --getvolumesid | --cleanvolumes"