import requests
from bs4 import BeautifulSoup, SoupStrainer
import pandas as pd

import config
import re

class craigslist_search_scrape(object):
    def __init__(self):
        self.base_url = 'https://sfbay.craigslist.org/search/sss?query='
        self.result_set = []
        self.i = 0

    def generate_query(self, kwlist):
        assert type(kwlist) == list, "Must pass list of keywords"
        kw_join = '+'.join(kwlist)
        return kw_join

    def execute_query(self, kwlist):
        ### Primary Query
        self.result_set = []
        query_url = self.base_url + self.generate_query(kwlist)
        response = requests.get(query_url)
        ####### show url
        print(response.url)
        self.extract_items(response)
        next_href = self.page_check(response)
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
                price=          self._search_details(item, 'price').text.strip('$').astype(float) if not None else None
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
    def gather_page_info(self, links):
        results = []
        for page in links:
            craig_p = craigslist_page_search(page)
            result_details = [{
                'link':page,
                'price':craig_p.conduct_search('price').strip('$'),
                'lens_length':craig_p.conduct_search('lens_length'),
                'lens_aperture':craig_p.conduct_search('lens_aperture')
            }]
            results = results + result_details
        return results
    def process_all_pages(self):
        self.df = pd.DataFrame.from_dict(self.results, orient='index')
        page_results = self.gather_page_info(self.df['link'].tolist())
        final_df = self.df.merge(pd.DataFrame(page_results), on='link', suffixes=['_headline','_page'])
        return final_df

class craigslist_page_search(object):
    def retrieve_page(self):
        response = requests.get(self.link)
        self.soup = BeautifulSoup(response.text, 'html.parser')
        return 'Successful retrieval'
    def __init__(self, link):
        self.link = link
        self.retrieve_page()
        self.soup_params = {'price':{0:['span',{'class':'price'}],
                                     1:['span',{'id':'titletextonly'}],
                                     2:['section',{'id':'postingbody'}]},
                            'lens_length':{0:['span',{'id':'titletextonly'}],
                                           1:['section',{'id':'postingbody'}]},
                            'lens_specs':{0:['span',{'id':'titletextonly'}],
                                          1:['section',{'id':'postingbody'}]},
                            'lens_aperture':{0:['span',{'id':'titletextonly'}],
                                          1:['section',{'id':'postingbody'}]}}
        self.search_params = {'price':['\$\w+'],
                              'lens_length':['\d+mm', 'Nikon \d+','Nikor \d+','\d+-\d+mm'],
                              'lens_specs': ['\d+mm f/\d+.\d+','\d+mm f\d+.\d+','\d+ \d\.\d','\d+-\d+ \d\.\d',
                                             '\d+-\d+mm \d\.\d','\d+-\d+mm \d\.\d-\d\.\d','\d+-\d+ \d\.\d-\d\.\d'],
                              'lens_aperture':['f/\d\.\d+','f\d+\.\d+','f\d+','\d+\.\d+','\d\.\d-\d\.\d','F\d-\d.\d']}
    def regex_search(self, text, expression):
        m = re.search(expression, text)
        found = m.group()
        return found
    def parse_foundlist(self, found):
        rep = {'Nikon':'',
               'nikon':'',
               'mm':'',
               'f/':'',
               'f':'',
               '/':'',
               ' ':''}
        def replacer(item, rep):
            for k, v in rep.items():
                item = item.replace(k,v)
            return item
        for u,item in enumerate(found):
            found[u] = replacer(item, rep)
        max_len = ''
        for val in set(found):
            if len(val) > len(max_len):
                max_len = val
        return max_len
    def conduct_search(self, find_item):
        soup_params = self.soup_params[find_item]
        search_params = self.search_params[find_item]
        found = []
        if type(soup_params) == dict:
            self.soup_segment = ''
            for soup_param in soup_params.values():
                try:
                    self.soup_segment = self.soup_segment + ' ' + self.soup.find(soup_param[0], soup_param[1]).text
                except:
                    pass
        else:
            self.soup_segment = self.soup.find(soup_params[0], id=soup_params[1]).text
        for param in search_params:
            try:
                cur_found = self.regex_search(self.soup_segment, param)
                if type(cur_found) == list:
                    pass
                else:
                    cur_found = [cur_found.strip(' ')]
                found = found + cur_found
            except:
                continue
        return self.parse_foundlist(found)