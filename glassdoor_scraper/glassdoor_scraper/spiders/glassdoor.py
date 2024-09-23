import scrapy
from scrapy.crawler import CrawlerProcess

class GlassdoorSpider(scrapy.Spider):
    name = 'glassdoor'
    allowed_domains = ['glassdoor.com']
    
    # Job search term and locations
    job_title = "data scientist"
    locations = [
        'Atlanta, GA', 'Austin, TX', 'Boston, MA',
        'Cambridge, MA', 'Chicago, IL', 'Los Angeles, CA',
        'New York, NY', 'Palo Alto, CA', 'Philadelphia, PA',
        'San Diego, CA', 'San Francisco, CA', 'San Jose, CA',
        'Seattle, WA', 'Washington, DC', 'TX'
    ]

    # Start URLs (for each location)
    def start_requests(self):
        for location in self.locations:
            url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={self.job_title}&locT=C&locId=&locKeyword={location.replace(' ', '%20')}"
            yield scrapy.Request(url=url, callback=self.parse_location, meta={'location': location})

    def parse_location(self, response):
        location = response.meta['location']
        
        # Loop over job listings
        job_listings = response.xpath('//li[@class="react-job-listing"]')
        
        for job in job_listings:
            job_url = job.xpath('.//a[@class="jobLink"]/@href').get()
            full_url = response.urljoin(job_url)
            job_title = job.xpath('.//a[@class="jobLink"]/text()').get()
            company_name = job.xpath('.//div[@class="jobHeader"]/span/text()').get()
            location = job.xpath('.//span[@class="loc"]/text()').get()
            salary = job.xpath('.//span[@class="salaryText"]/text()').get(default='N/A')
            
            # Scrape detailed job information by following the job link
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_job_details,
                meta={
                    'job_title': job_title,
                    'company_name': company_name,
                    'location': location,
                    'salary': salary
                }
            )

        # Follow pagination
        next_page = response.xpath('//li[@class="pagination__PaginationStyle__next"]/a/@href').get()
        if next_page:
            yield scrapy.Request(url=response.urljoin(next_page), callback=self.parse_location, meta={'location': location})

    def parse_job_details(self, response):
        # Job details from the listing page
        job_title = response.meta['job_title']
        company_name = response.meta['company_name']
        location = response.meta['location']
        salary = response.meta['salary']
        
        job_description = response.xpath('//*[@id="JobDescriptionContainer"]/text()').get(default='No description available')
        company_size = response.xpath('//span[text()="Size"]/following-sibling::span/text()').get(default='N/A')
        company_type = response.xpath('//span[text()="Type"]/following-sibling::span/text()').get(default='N/A')
        company_revenue = response.xpath('//span[text()="Revenue"]/following-sibling::span/text()').get(default='N/A')
        company_industry = response.xpath('//span[text()="Industry"]/following-sibling::span/text()').get(default='N/A')

        # Save data
        yield {
            'job_title': job_title,
            'company_name': company_name,
            'location': location,
            'salary': salary,
            'job_description': job_description,
            'company_size': company_size,
            'company_type': company_type,
            'company_revenue': company_revenue,
            'company_industry': company_industry,
            'job_url': response.url
        }

# Run the spider programmatically (if you want to run it from a script)
process = CrawlerProcess(settings={
    "FEEDS": {
        "jobs.json": {"format": "json"},
    },
})
process.crawl(GlassdoorSpider)
process.start()
