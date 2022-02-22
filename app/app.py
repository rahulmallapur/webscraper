import scraper
import aws_s3 as s3s


def handler(event, context):
    scrap = scrap.CompetitorScraper()
    urls = scrap.get_image_urls(query=event['query'], max_urls=event['count'], sleep_between_interactions=1)
    scrap.ScrapeKOA(count=event['count'], location =event['location'], rv_type=event['rv_type'], rv_length=event['rv_length'])
    scrap.close_connection()
    return "Successfully loaded from {} +5 days from now of data from {} with RV Type = {} and Length = {}.".format(event['count'],
                                                                                                event['location'],
                                                                                                event['rv_type'],
                                                                                                event['rv_length'])
