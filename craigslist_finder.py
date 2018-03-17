import requests
from bs4 import BeautifulSoup, SoupStrainer
import pandas as pd

import config

class craigslist_search_scrape(object):
    def __init__(self, online=False):
        self.base_url = 'https://sfbay.craigslist.org/search/sss'
        self.result_set = []
        self.online = online
        self.i = 0

    def generate_query(self, kwlist):
        assert type(kwlist) == list, "Must pass list of keywords"
        keywords = '+'.join(kwlist)
        return keywords

    def execute_query(self, kwlist):
        ### Primary Query
        self.result_set = []
        params = {'query':self.generate_query(kwlist)}
        if self.online == False:
            response = r
        else:
            response = requests.get(self.base_url, params)
        self.extract_items(response)
        next_href = self.page_check(response)
        if self.online == False:
                next_href = False
        while next_href != False:
            next_url = '{base}{page}'.format(base=self.base_url, page=next_href)
            response = requests.get(next_url)
            self.extract_items(response)
            next_href = self.page_check(response)
        return "Query Complete"
        
    def extract_items(self, response):
        result_table = SoupStrainer(id="sortable-results")
        soup = BeautifulSoup(response.text, 'html.parser', parse_only=result_table)
        result_items = soup.find_all("li")
        self.result_set = self.result_set + result_items
        
    def page_check(self, response):
        next_button = SoupStrainer(class_="button next")
        soup = BeautifulSoup(response.text, 'html.parser', parse_only=next_button)
        next_href = soup.find('a')['href']
        if len(next_href) > 0:
            return soup.find('a')['href'].split('/search/sss')[1]
        else:
            return False
    def _search_details(self, item, key):
        key_match = {'price':['span','result-price'],
                    'location':['span','result-hood'],
                    'post_datetime':['time','result-date'],
                    'link':['a','result-title hdrlnk'],
                    'title':['a','result-title hdrlnk']}
        assert key in key_match.keys(), "Invalid Key"
        try:
            value = item.find(key_match[key][0], class_=key_match[key][1])
            return value
        except:
            return None
    def result_set_to_dict(self):
        self.results = {}
        for item in self.result_set:
            item_id = item['data-pid']
            try:
                price=          self._search_details(item, 'price').text.strip('$') if not None else None
            except:
                price= None
            try:
                location=      self._search_details(item, 'location').text.strip(' (').strip(')') if not None else None
            except:
                location= None
            try:
                post_datetime= self._search_details(item, 'post_datetime')['datetime'] if not None else None
            except:
                post_datetime= None
            try:
                link=          self._search_details(item, 'link')['href'] if not None else None
            except:
                link= None
            try:
                title=         self._search_details(item, 'title').text if not None else None
            except:
                title= None
            try:
                _id=            item_id
            except:
                _id = None
            ########### Instead make a function that searches for each base on input if not found then return null
            item_dict = {'price':          price,
              'location':      location,
              'post_datetime': post_datetime,
              'link':          link,
              'title':         title,
              'id':            item_id}
            self.results.update({item_id:item_dict})
            