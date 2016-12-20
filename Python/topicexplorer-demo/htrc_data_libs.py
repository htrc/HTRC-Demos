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

import urllib
import urllib2
import json
import zipfile
import io
import os
import re
import xml.etree.ElementTree

import logging
from nltk.corpus import wordnet as wn
import enchant

def _get_oauth2_token(endpoint, client_id, client_secret):
    """ function that authorizes with OAuth2 token endpoint, obtains and returns an OAuth2 token
    
    arguments:
    clientID -- client ID or username
    clientSecret -- client secret or password
    
    returns OAuth2 token upon successful authroization.
    raises exception if authorization fails
    """
    
    # content-type http header must be "application/x-www-form-urlencoded"
    headers = {'content-type' : 'application/x-www-form-urlencoded'}
     
    # request body
    values = {'grant_type' : 'client_credentials',
          'client_id' : client_id,
          'client_secret' : client_secret }
    body = urllib.urlencode(values)
     
    # request method must be POST
    req = urllib2.Request(endpoint, body, headers)
    try:
        # urllib2 module sends HTTP/1.1 requests with Connection:close header included
        response = urllib2.urlopen(req)
         
        # any other response code means the OAuth2 authentication failed. raise exception
        if (response.code != 200):
            raise urllib2.HTTPError(response.url, response.code, response.read(), response.info(), response.fp)
         
        # response body is a JSON string
        oauth2JsonStr = response.read()
         
        # parse JSON string using python built-in json lib
        oauth2Json = json.loads(oauth2JsonStr)
         
        # return the access token
        return oauth2Json["access_token"]    
    # response code in the 400-599 range will raise HTTPError
    except urllib2.HTTPError as e:
        # just re-raise the exception
        raise Exception(str(e.code) + " " + str(e.reason) + " " + str(e.info) + " " + str(e.read())) 
    
def _append_to_zipfile(zipcontent, zf):    
    """ function that writes text to a zip file
    
    arguments:
    zipcontent -- text returned from Data API
    zf -- zip file to be appended
    """
    
    # read from zip stream
    zippedFile = zipfile.ZipFile(zipcontent, "r")
    
    try:
        # getting a list of entries in the ZIP
        infoList = zippedFile.infolist()
        for zipInfo in infoList:
            entryName = zipInfo.filename
            entry = zippedFile.open(entryName, "r")
            
            # read zip entry content 
            content = ''
            line = entry.readline()
            while (line != ""):
                line = entry.readline()
                content += line
            
            # remember to close each entry
            entry.close()
            
            # write to zip file in disk
            zf.writestr(zipInfo, content)
    finally:
        zippedFile.close()
        
def _download_volumes_as_a_stream_(endpoint, token, parameters):
    """ function that sends request to Data API service and returns a zip stream 
        
    returns zip stream upon successful authroization.
    raises exception if any HTTP error occurs
    """
    
    # 2 http request headers must be present
    # the Authorization header must be the OAuth2 token prefixed with "Bearer " (note the last space)
    # and the Content-type header must be "application/x-www-form-urlencoded" 
    headers = {"Authorization" : "Bearer " + token,
           "Content-type" : "application/x-www-form-urlencoded"}
    
    # urlencode the body query string
    urlEncodedBody = urllib.urlencode(parameters)
    
    # make the request
    # the request method must be POST
    # the body is the urlencoded www form
    # the headers contain OAuth2 token as Authorization, and application/x-www-form-urlencoded as content-type
    req = urllib2.Request(endpoint, urlEncodedBody, headers)
    print("Sending data api request to " + endpoint)
    response = urllib2.urlopen(req)
    if (response.code != 200):
        raise urllib2.HTTPError(response.url, response.code, response.read(), response.info(), response.fp)
     
    #  keep the zipcontent in memory
    zipcontent = io.BytesIO(response.read())
    return zipcontent

def filter_by_suffix(l, ignore):
    """
    Returns elements in `l` that does not end with elements in `ignore`.

    :param l: List of strings to filter.
    :type l: list

    :param ignore: List of suffix to be ignored or filtered out.
    :type ignore: list

    :returns: List of elements in `l` whose suffix is not in `ignore`.

    **Examples**

    >>> l = ['a.txt', 'b.json', 'c.txt']
    >>> ignore = ['.txt']
    >>> filter_by_suffix(l, ignore)
    ['b.json']
    """
    return [e for e in l if not sum([e.endswith(s) for s in ignore])]        

def proc_htrc_book(book, coll_dir, ignore=['.json', '.log']):
    """
    Cleans up page headers, line breaks, and hyphens for all plain pages in the book directory. 
    Creates a log file for debugging purposes.  
  
    :param book: The name of the book directory in coll_dir.
    :type book: string
    
    :param coll_dir: The path for collection.
    :type coll_dir: string
    
    :param ignore: List of file extensions to ignore in the directory.
    :type ignore: list of strings, optional

    :returns: None

    :See Also: :meth: rm_pg_headers, :meth: rm_lb_hyphens
    """
    book_root = os.path.join(coll_dir, book)

    logger = logging.getLogger(book)
    logger.setLevel(logging.INFO)
    log_file = os.path.join(coll_dir, book + '-raw-proc.log')
    handler = logging.FileHandler(log_file, mode='w')
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    print 'Processing', book_root

    try:
        rm_pg_headers(book_root, logger, ignore=ignore)
        rm_lb_hyphens(book_root, logger, ignore=ignore)
    finally:
        handler.close()

def rm_lb_hyphens(plain_root, logger, ignore=['.json', '.log']):
    """
    Looks for a hyphen followed by whitespace or a line break.

    Reconstructs word and checks to see if the result exists in either
    WordNet or the OS's default spellchecker dictionary. If so,
    replaces fragments with reconstructed word.
    
    :param plain_root: The name of the directory containing plain-text 
        files.
    :type plain_root: string
    
    :param logger: Logger that handles logging for the given directory.
    :type logger: Logger
    
    :param ignore: List of file extensions to ignore in the directory.
    :type ignore: list of strings, optional

    :returns: None
    """

    d = enchant.Dict('en_US')

    def recon(match_obj):
        rc_word = match_obj.group(1) + match_obj.group(2)
        
        if wn.synsets(rc_word) or d.check(rc_word):
            logger.info('\nbook: %s\nreconstructed word:\n%s\n',
                         plain_root, rc_word)
            return rc_word
        
        logger.info('\nbook: %s\nignored expression:\nleft: %s\nright: %s\n',
                     plain_root, match_obj.group(1), match_obj.group(2))

        return match_obj.group(0)

    def inner(s):
        lb_hyphenated = re.compile(r'(\w+)-\s+(\w+)')
        return lb_hyphenated.sub(recon, s)
    
    page_files = os.listdir(plain_root)
    page_files = filter_by_suffix(page_files, ignore)

    for i, page_file in enumerate(page_files):
        filename = os.path.join(plain_root, page_file)
        print filename

        with open(filename, 'r+') as f:
            page = f.read()
            page = inner(page)
            f.seek(0)
            f.write(page)
            f.truncate()



def rm_pg_headers(plain_root, logger, bound=1, ignore=['.json', '.log']):
    """
    Tries to detect repeated page headers (e.g., chapter titles). If
    found, removes them.

    The routine takes the first non-empty lines of text, strips them
    of numbers and punctuation and computes frequencies. If frequency
    for the reduced string exceeds `bound`, the corresponding first
    lines are considered headers.
    
    :param plain_root: The name of the directory containing plain-text 
        files.
    :type plain_root: string
    
    :param logger: Logger that handles logging for the given directory.
    :type logger: Logger
    
    :param bound: Number of frequency of a reduced string. If the string
        appears more than `bound`, then the corresponding first lines are
        considered headers. Default is 1.
    :param bound: int, optional

    :param ignore: List of file extensions to ignore in the directory.
    :type ignore: list of strings, optional

    :returns: None
    """
    page_files = os.listdir(plain_root)
    page_files = filter_by_suffix(page_files, ignore)

    # Get first non-empty lines
    first_lines = []
    fl = re.compile(r'^\s*([^\n]*)\n')
    
    for page_file in page_files:
        page_file = os.path.join(plain_root, page_file)

        with open(page_file, 'r') as f:
            page = f.read()

        first_line = fl.match(page)
        if first_line == None:
            first_lines.append('')
        else:
            first_lines.append(first_line.group(0))

    # Remove capitalization, roman numerals for numbers under 50,
    # punctuation, arabic numerals from first lines
    for i in xrange(len(first_lines)):
        line = first_lines[i]
        line = line.lower()

        # An overzealous arabic numeral detector (OCR errors include
        # `i` for `1` for example)
        line = re.sub(r'\b\S*\d+\S*\b', '', line)

        # Roman numerals i to xxxix
        line = re.sub(r'\b(x{0,3})(ix|iv|v?i{0,3})\b', '', line)

        # Collapse line to letters only
        line = re.sub(r'[^a-z]', '', line)
        first_lines[i] = (first_lines[i], line)

    freqs = dict()
    for line, reduced in first_lines:
        if reduced in freqs:
            freqs[reduced] += 1
        else:
            freqs[reduced] = 1
    
    for i, page_file in enumerate(page_files):
        filename = os.path.join(plain_root, page_file)
        line, reduced = first_lines[i]

        if freqs[reduced] > bound:
            with open(filename, 'r') as f:
                page = f.read()
            if page:
                logger.info('\nbook: %s\nfile: %s\nremoved header:\n%s\n',
                             plain_root, page_file, line)
            page = fl.sub('', page)

            with open(filename, 'w') as f:
                f.write(page)
                
def proc_htrc_coll(coll_dir, ignore=['.json', '.log']):
    """
    Given a collection, cleans up plain page files for books in the collection.

    :param coll_dir: The path for collection.
    :type coll_dir: string
    
    :param ignore: List of file extensions to ignore in the directory.
    :type ignore: list of strings, optional

    :returns: None

    :See Also: :meth: proc_htrc_book
    """
    books = os.listdir(coll_dir)
    books = filter_by_suffix(books, ignore)
    
    for book in books:
        # For debugging
        # if book == 'uc2.ark+=13960=t1zc80k1p':
        # if book == 'uc2.ark+=13960=t8tb11c8g':
        # if book == 'uc2.ark+=13960=t74t6gz6r':
        proc_htrc_book(book, coll_dir, ignore=ignore)

def download_volumes_to_zipfile(zipfilename, data_endpoint, volume_ids, req_options, \
    oauth2_endpoint, client_id, client_secret):
    token = _get_oauth2_token(oauth2_endpoint, client_id, client_secret)
    print("Obtained token: " + token)
    
    # open file to write
    BATCH_SIZE = 20
    zf = zipfile.ZipFile(zipfilename, mode='w', allowZip64=True)
    try:
        # send batch request to DATA API
        start = 0
        length = len(volume_ids)
        while (start < length):
            batch = volume_ids[start : (start + BATCH_SIZE)]
            start = start + BATCH_SIZE
            
            # fill in data api request parameters
            # concatenate volume id with pipe '|'
            volumeIdList = '|'.join(batch)
            parameters = {'volumeIDs' : volumeIdList}
            parameters.update(req_options)
            
            # call Data api
            remain = length - start
            if (remain < 0):
                remain = 0
            print("Requesting " + str(len(batch)) + " volumes from Data API, " + \
                str(remain) + " more volumes left.")
            zipcontent = _download_volumes_as_a_stream_(data_endpoint, token, parameters)
            
            # write zip stream to file
            print("Writing to zip file")
            _append_to_zipfile(zipcontent, zf) 
    finally:
        print 'Closing zip file'
        zf.close() 
    
def get_volume_ids_from_solr(request_url):
    print("Sending solr request to " + request_url)
    max_attempts = 3
    batch = 500
    start = 0
    volume_ids = []
    while True:
        volumes = []
        solrurl = request_url + '&fl=id&rows={}&start={}'.format(str(batch), str(start))        
        for i in range(0, max_attempts):
            try:
                response = urllib2.urlopen(solrurl)
                print("Asking " + solrurl)
                if (response.code != 200):
                    raise urllib2.HTTPError(response.url, response.code, response.read(), \
                        response.info(), response.fp)
                    
                solrresponse = io.BytesIO(response.read())
                for event, element in xml.etree.ElementTree.iterparse(solrresponse):
                    if element.tag == 'str' and element.attrib.has_key('name') and \
                        element.attrib['name'] == 'id':
                        volumes.append(element.text) 
                
                if len(volumes) == 0:
                    return volume_ids
                else:
                    start += len(volumes)
                    volume_ids.extend(volumes)  
                    break  
            except:
                continue
    raise Exception("Unable to get data from Solr...")
        
