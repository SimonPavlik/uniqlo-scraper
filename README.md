# UNIQLO Scraping
A simple script to extract tables with clothes sizes data from [UNIQLO.cn](https://www.uniqlo.cn/) website.

## Usage
The web uses JavaScript extensively, you need to run Splash Browser in the background before you start Scraping.
```
sudo docker run -p 8050:8050 scrapinghub/splash
```
The scraper will save the scraped tables into `output.jl`:  
```
scrapy crawl clothes -o output.jl --loglevel=DEBUG
```

## Requirements
You will need Docker and a pulled [Splash image](https://splash.readthedocs.io/en/stable/install.html) to start
 Splash container.

Python 2.7 Dependencies: 
```
Scrapy              1.6.0
scrapy-splash       0.7.2
```
