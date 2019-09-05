# coding=utf-8
import scrapy
from scrapy_splash import SplashRequest

from scraper.items import ProductItem

WAIT_SEC = 15


def extend_dict(dictionary, data_path):
    """extend an existing nested dictionary with a new entry..."""
    def add_key(elements):
        result = dict()
        if len(elements) > 2:
            result[elements[-1]] = add_key(elements[:-1])
        else:
            result[elements[-1]] = elements[-2]
        return result

    def merge(a, b, path=None):
        """merges b into a"""
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    merge(a[key], b[key], path + [unicode(key)])
                elif isinstance(a[key], unicode) and isinstance(b[key], unicode):
                    a[key] = b[key]
                else:
                    raise Exception('Conflict at %s' % '.'.join(path + [unicode(key)]))
            else:
                a[key] = b[key]
        return a

    dictionary = merge(dictionary, add_key(data_path))

    return dictionary


def extract_table(selector):
    """scrape the table data and return its dict representation"""
    sizes_dicts = []
    for table in selector:
        first_cell = table.xpath(u'//td')[0]
        tree_depth = int(first_cell.attrib['rowspan'])
        table_rows = table.xpath('tr')
        table_header = table_rows[:tree_depth]
        table_body = table_rows[tree_depth:]

        table_structure = []

        first_row = table_header[0].xpath("td")[1:]
        table_structure.append(extract_header_row(first_row))

        for raw_row in table_header[1:]:
            row = raw_row.xpath("td")
            table_structure.append(extract_header_row(row))

        table_data = []
        for raw_row in table_body:
            table_data.append(raw_row.xpath("td/text()").extract())

        sizes_dict = {}

        for row in table_data:
            for idx, cell in enumerate(row[1:]):
                tree_data = [cell]
                for head_row in reversed(table_structure):
                    max_idx = -1
                    for caption, colspan in head_row:
                        max_idx += colspan
                        if idx <= max_idx:
                            tree_data.append(caption)
                            break
                tree_data.append(row[0])
                sizes_dict = extend_dict(sizes_dict, tree_data)

        sizes_dicts.append(sizes_dict)

    return sizes_dicts


def extract_header_row(row_selector):
    row_structure = []
    for cell in row_selector:
        cell_text = cell.xpath("text()").extract()[0]
        if 'colspan' in cell.attrib:
            cell_data = (cell_text, int(cell.attrib["colspan"]))
        else:
            cell_data = (cell_text, 1)
        row_structure.append(cell_data)
    return row_structure


class UQSpider(scrapy.Spider):
    """Spider class defines the crawling behavior on a website to be crawled."""

    name = "clothes"

    start_urls = ["https://www.uniqlo.cn/c/ALL.html"]

    def parse(self, response):
        """Parses all links on the current page and a link to the next page with links."""

        ad_pg_lua_script = """
            function main(splash)
              splash.private_mode_enabled = false
              local url = splash.args.url
              assert(splash:go(url))
              assert(splash:wait(20))
              return {
                html = splash:html(),
                png = splash:png(),
                har = splash:har(),
              }
            end
            """

        # follow links to ad pages
        for href in response.css('div.h-product > a::attr(href)').extract():
            yield SplashRequest(
                url=response.urljoin(href), callback=self.parse_ad, endpoint='execute',
                args={"lua_source": ad_pg_lua_script}
            )

        # follow pagination links
        next_page = response.xpath(u'//nav[@class="h-pagination"]/a[text()="下一页 >"]/@href').extract()
        if next_page:
            # pagination ends when there are no more buttons with links than a single one leading back.
            next_page = response.urljoin(next_page[0])
            yield SplashRequest(url=next_page, callback=self.parse, endpoint='render.html', args={"wait": WAIT_SEC})

    @staticmethod
    def parse_ad(response):
        """Parses the final desired page. Returns a scraped Items."""

        item = ProductItem()
        item['url'] = response.url
        item['title'] = response.css('div.product-detail-list-title::text').extract()[0]
        item['code'] = response.xpath(u'//ul[@class="detail_ul"]/li[text()="货号："]/@title').extract()[0]
        item['sizes_table'] = extract_table(response.xpath(u'//div[text()="产品尺寸"]/../div/table/tbody'))

        output_data = item

        # yield a dictionary with the final data record ready to be stored into a json, database, etc.
        yield output_data

    def start_requests(self):
        """Initializes crawling on the first page and yields the request leading to all links and the next page."""
        for url in self.start_urls:
            yield SplashRequest(url=url, callback=self.parse, endpoint='render.html', args={"wait": WAIT_SEC})
