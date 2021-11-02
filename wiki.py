import sys
import requests
import bs4

def wikiScrape(url):
    res = requests.get(url + ' '.join(sys.argv[1:]))

    res.raise_for_status()
    wiki = bs4.BeautifulSoup(res.text,"lxml")
    elems = wiki.select('p') + wiki.select('li')
    
    
    for i in range(len(elems)):
        print(elems[i].getText())
    print(i)

wikiScrape('https://en.wikipedia.org/wiki/Web_scraping')