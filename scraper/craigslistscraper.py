#!/usr/bin/python3

# 2016-11-23, v. 0.2
# Irek Rybark, irek@rybark.com

# This script queries number of Craigslist site for a car listings.
# It uses request parameters like max price, min year etc. from config file

# example of a configuration file

# [email]
# user=my.account@gmail.com
# password=somepassword
#
# [notifications]
# to_email=recipent1@gmail.com;recipent2@gmail.com
#
# [craigslist]
# sites=newjersey,cnj,jerseyshore,southjersey,longisland,newyork,newhaven,hudsonvalley,catskills,philadelphia,allentown,reading,delaware,poconos,scranton,lancaster
#
# [search]
# search_distance=100
# postal=07080
# min_price=7000
# max_price=13000
# auto_make_model=jeep+wrangler
# min_auto_year=2004
# max_auto_miles=110000
# auto_transmission=1
#
# [paths]
# results_path=../data/results.csv
# ignored_path=../data/ignored.csv
# new_res_path=../data/results_new.csv

# The script is roughly based on the following tutorial by Greg Reda
# http://www.gregreda.com/2014/07/27/scraping-craigslist-for-tickets/a

# License: The MIT License (MIT)

# Installation
# /etc/opt/craigslistscraper.conf - configuration file, contains email access password!
# /var/opt/craigslistscraper - output data directory
# /usr/local/bin - script directory

from bs4 import BeautifulSoup
from urllib import request
from urllib import parse
from datetime import datetime
import sys
import smtplib
import pandas as pd
import configparser

# {0} site name, {1} search params
SEARCH_URL = 'http://{0}.craigslist.org/search/cta?{1}'
# {0} site name, {1} listing path
DETAIL_URL = 'http://{0}.craigslist.org{1}'

config = configparser.ConfigParser()

def search_query(site):
    search_params = parse.urlencode(config['search'])
    search_url = SEARCH_URL.format(site, search_params)
    return BeautifulSoup(request.urlopen(search_url).read(), "lxml")

def parse_results(site, soup):

    def get_data_item(tag, class_, field=''):
        try:
            if field == '':
                res = row.find(tag, class_=class_).text
            else:
                res = row.find(tag, class_=class_).get(field)
        except Exception as e:
            print('**** Exception (', tag, ',', class_, ',', field, '): ', str(e))
            #print(row)
            res = None
        return res


    results = []
    # <ul class="rows">
    # <li class="result-row" data-pid="5881531840">
    rows = soup.find('ul', class_='rows').find_all('li')
    for row in rows:
        try:
            lst_pid = int(row.get('data-pid'))
            # <a class="result-image gallery" .... href="/cto/5881531840.html">
            lst_url = get_data_item('a', 'result-image gallery', 'href')
            # <time class="result-date" datetime="2016-11-17 21:13" title="Thu 17 Nov 09:13:17 PM">Nov 17</time>
            lst_time = get_data_item('time', 'result-date', 'datetime')
            # <a class="result-title hdrlnk" data-id="5881531840" href="/cto/5881531840.html">2004 Jeep ...</a>
            lst_title = get_data_item('a', 'result-title hdrlnk')
            # <span class="result-price">$8995</span>
            lst_price = get_data_item('span', 'result-price')
            # < span class="result-hood"> (Mahwah)</span>
            lst_hood = get_data_item('span', 'result-hood')
            lst_url_detail = DETAIL_URL.format(site, lst_url)

            results.append({'pid':lst_pid, 'site':site, 'url': lst_url, 'create_time': lst_time,
                            'title': lst_title, 'price': lst_price, 'hood': lst_hood,
                            'url_detail': lst_url_detail})
        except Exception as e:
            print('**** Exception: ', str(e))
            print(row)
    return results

def write_results(results):
    """Writes list of dictionaries to file."""
    results.to_csv(config['paths']['results_path'])

def write_new_res(results):
    """Writes list of dictionaries to file."""
    results.to_csv(config['paths']['new_res_path'])

def read_results():
    resdf = pd.DataFrame.from_csv(config['paths']['results_path'])
    resdf.index.rename('pid', inplace=True)
    return resdf

def read_ignored():
    resdf = pd.DataFrame.from_csv(config['paths']['ignored_path'])
    resdf.index.rename('pid', inplace=True)
    return resdf

def get_current_time():
    return datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

def find_new_records(resdf):
    if len(resdf) <= 0:
        return pd.DataFrame()
    try:
        resdf_old = read_results()
    except:
        return resdf

    resdf = resdf[~resdf.index.isin(resdf_old.index)].dropna(how = 'all')
    return resdf

def query_sites():
    results_all = []
    for site in config['craigslist']['sites'].split(','):
        try:
            print('### site: ', site)
            soup = search_query(site)
            results = parse_results(site, soup)
            results_all += results
            print(len(results), len(results_all))
        except Exception as e:
            print('**** Exception: ', str(e))

    resdf = pd.DataFrame(results_all)
    resdf.set_index('pid', inplace=True)

    try:
        resdf_ign = read_ignored()
        resdf = resdf[~resdf.index.isin(resdf_ign.index)].dropna(how = 'all')
    except:
        pass

    newresdf = find_new_records(resdf)
    if len(newresdf) > 0:
        print("There are new Craigslist posts for: {0}".format(config['search']['auto_make_model'].strip()))

        write_results(resdf)
        write_new_res(newresdf)
        def_max_colwidth = pd.get_option('display.max_colwidth')
        try:
            pd.set_option('display.max_colwidth', -1)  # make sure that the URL is not truncated with '...'
            message = newresdf.to_string(columns=['create_time', 'hood', 'price', 'title', 'url_detail'])
        finally:
            pd.set_option('display.max_colwidth', def_max_colwidth)
        send_email(message)
    else:
        print("[{0}] No new results - will try again later".format(get_current_time()))

def send_email(msg):
    fromaddr = "Craigslist Checker"
    toaddrs = config['notifications']['to_email']
    msg = ("From: {0}\r\nTo: {1}\r\nSubject: New listings\r\n\r\n{2}").format(fromaddr, toaddrs, msg)
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(config['email']['user'], config['email']['password'])
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()

if __name__ == '__main__':
    try:
         config_file_path = sys.argv[1]
    except:
        config_file_path = "..\..\..\OpenSource.secret\CraigsListScraper\scraper.config"
    config.read(config_file_path)
    query_sites()

