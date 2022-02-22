import hashlib
import io
import logging
import os
import re
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import datetime
import pyodbc
import pandas as pd
from PIL import Image

logging.basicConfig(format='%(asctime)s %(levelname)s %(process)d --- %(name)s %(funcName)20s() : %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)

class CompetitorScraper:
    logger = logging.getLogger('ImageScraper')

    def __init__(self):
        self._tmp_folder = '/tmp/img-scrpr-chrm/'
        self.driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', options=self.__get_default_chrome_options())

    def get_image_urls(self, query: str, max_urls: int, sleep_between_interactions: int = 1):
        search_url = "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img"
        self.driver.get(search_url.format(q=query))

        image_urls = set()
        image_count = 0
        results_start = 0
        while image_count < max_urls:
            self.__scroll_to_end(sleep_between_interactions)
            thumbnail_results = self.driver.find_elements_by_css_selector("img.Q4LuWd")
            number_results = len(thumbnail_results)
            self.logger.info(f"Found: {number_results} search results. Extracting links from {results_start}:{number_results}")

            for img in thumbnail_results[results_start:number_results]:
                self.__click_and_wait(img, sleep_between_interactions)
                self.__add_image_urls_to_set(image_urls)
                image_count = len(image_urls)
                if image_count >= max_urls:
                    self.logger.info(f"Found: {len(image_urls)} image links, done!")
                    break
            else:
                self.logger.info(f"Found: {len(image_urls)} image links, looking for more ...")

                load_more_button = self.driver.find_element_by_css_selector(".mye4qd")
                if load_more_button:
                    self.logger.info("loading more...")
                    self.driver.execute_script("document.querySelector('.mye4qd').click();")

            # move the result startpoint further down
            results_start = len(thumbnail_results)

        return image_urls

    def ScrapeKOA(self, count: int, location: str, rv_type: str, rv_length: str):
        competitor = 'KOA'
        ## Scraping KOA for campsites around preferred location
        for c in range(count, count+5):
            global_scrape_date = datetime.datetime.today().strftime('%d-%m-%Y')
            date = self.GetDates(c)
            print(f"----Scraping KOA {location} {datetime.datetime.now().strftime('%H:%M:%S')}::{date['start_date']}")
            koa_url = f"https://koa.com/search/?txtLocation={location}&checkInDate={date['start_mm']}%2F{date['start_dd']}%2F{date['start_yy']}&checkOutDate={date['end_mm']}%2F{date['end_dd']}%2F{date['end_yy']}&Adults=1&Children=0&ChildrenAgesList=&EquipmentType={rv_type}&EquipmentLength={rv_length}&SlideOuts=No&Pets=No&chkRvSite=true&chkRvSite=false&chkCampingCabin=false&chkTentSite=false&chkUniqueLodging=false&chkGroups=false&chkExtendedStay=false&chkKampGreen=false&chkPool=false&chkHotTub=false&chkWiFi=false&chkPavilion=false&chkCableTV=false&chkMiniGolf=false&chkBikeRental=false&chkSnackBar=false&chkFirewood=false&chkPropane=false&chkFishing=false&chkTourShuttle=false&ddlDistance=250"
            self.driver.get(koa_url)
            time.sleep(2)
            num = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'row campground-listing')]")
            for x in range(len(num)):
                coordinates = num[x].location
                self.driver.execute_script(f"window.scrollTo(0,{coordinates['y']})")
                try:
                    WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.XPATH, f"/html/body/div[1]/div[4]/div/div/div[2]/div[3]/div[4]/div/div[{x+1}]/div[2]/div[3]/div/div[1]/div/a")))
                except:
                    ''
            time.sleep(3)
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            koa_rvSites = soup.find_all('a', {'class': 'button-small chevron-right koa-red-bg text-uppercase full-width-button'})

            ## Scraping all collected KOA campsites
            for anchor in koa_rvSites:
                koa_data = []
                amenities = []
                price_list = []
                site_type = []
                site_url = anchor['href']
                full_url = f'https://koa.com/{site_url}'

                self.driver.get(full_url)
                soup = BeautifulSoup(self.driver.page_source, 'lxml')
                
                try:
                    num_of_sites = soup.find('span', {'class': 'text-success font-weight-bold font-italic'}).text
                except:
                    self.logger.info(f"No sites available on {date['start_date']} for this site")
                    continue
                num_of_sites = int(''.join(re.findall("[0-99]+", num_of_sites[0])))

                street = ''.join(soup.find('span', {'class': 'camp-street'}).text).strip()
                city = ''.join(soup.find('span', {'class': 'camp-city'}).text).strip()
                state = ''.join(soup.find('span', {'class': 'camp-state'}).text).strip()
                address = f'{street} {city}, {state}'
                zipcode = ''.join(soup.find('span', {'class': 'camp-zip'}).text).strip()
                site_name = ''.join(soup.find('h2', {'class': 'no-top-margin reserve-koa-icon'}).text).strip()

                prices = self.driver.find_elements(By.XPATH, "//div[@class = 'reserve-quote-per-night']//span[@class = 'notranslate']")
                for x in prices:
                    price_list.append(float((x.text).replace('$', '')))
                for x in range(num_of_sites - len(price_list)):
                    price_list.append(0)
                ## Scraping KOA amenities data
                details = self.driver.find_elements(By.XPATH, "//div[contains(@class,'col-lg-3')]/ul[@class='bullet-list3']")
                sitetype = self.driver.find_elements(By.XPATH, "//h4[contains(@class, 'reserve-sitetype-title')]")
                for x in range(num_of_sites):
                    site_amenities = []
                    for a in range(x*4, (x*4)+4):
                        array = [li.get_attribute("innerText") for li in details[a].find_elements(By.XPATH, './li')]
                        for b in array:
                            site_amenities.append(b)
                    amenities.append(site_amenities)
                    site_type.append(sitetype[x].text)

                rating = 0 #ScrapeRatings(f'{site_name} {city} {state}', driver)

                for x in range (num_of_sites):
                    koa_data.append([global_scrape_date, date['start_date'], competitor, site_name, address, city, state, zipcode, rating, rv_type, rv_length, price_list[x], site_type[x], amenities[x]])
                df = pd.DataFrame(koa_data, columns=['Scrape_Date', 'Search_Date', 'Competitor', 'Site_Name', 'Address', 'City', 'State', 'Zipcode', 'Google_Rating', 'RV_Type', 'RV_Length', 'Price', 'SiteType', 'Amenities'])
                self.logger.info(f"Injection to sql server - Started")
                server = 'rossreportingserver.database.windows.net' 
                database = 'RjourneyML_Dev' 
                username = 'TripAI' 
                password = 'umyWkv^2Pe'
                cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
                cursor = cnxn.cursor()
                for index, row in df.iterrows():
                    cursor.execute('''INSERT INTO dbo.CompetitorDataRaw(Scrape_Date,Search_Date,Competitor,Site_Name,Address,Zipcode,Google_Rating,RV_Type,RV_Length,Price,Amenities,SiteType,City,State) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (row.Scrape_Date, row.Search_Date, row.Competitor, row.Site_Name, row.Address, row.Zipcode, row.Google_Rating, row.RV_Type, row.RV_Length, row.Price, row.Amenities, row.SiteType, row.City, row.State))
                cnxn.commit()
                cursor.close()
                self.logger.info(f"Injection to sql server - Finished")

    def GetDates(self, count):
        checkin_date = datetime.datetime.today()
        if count > 0: checkin_date += datetime.timedelta(days=count)
        checkin_date_YY = checkin_date.strftime('%y')
        checkin_date_MM = checkin_date.strftime('%m')
        checkin_date_DD = checkin_date.strftime('%d')
        checkout_date = checkin_date + datetime.timedelta(days=1)
        checkout_date_YY = checkout_date.strftime('%y')
        checkout_date_MM = checkout_date.strftime('%m')
        checkout_date_DD = checkout_date.strftime('%d')
        dailydates = {'start_date': checkin_date.strftime('%Y-%m-%d'), 'end_date': checkout_date.strftime('%Y-%m-%d'),'start_yy': checkin_date_YY, 'start_mm': checkin_date_MM, 'start_dd': checkin_date_DD, 'end_yy': checkout_date_YY, 'end_mm': checkout_date_MM, 'end_dd': checkout_date_DD}
        return dailydates
    
    def persist_image(self, folder_path: str, url: str):
        image_content = self.__download_image_content(url)
        try:
            image_file = io.BytesIO(image_content)
            image = Image.open(image_file).convert('RGB')
            file_path = os.path.join(folder_path, hashlib.sha1(image_content).hexdigest()[:10] + '.jpg')
            with open(file_path, 'wb') as f:
                image.save(f, "JPEG", quality=85)
            self.logger.info(f"SUCCESS - saved {url} - as {file_path}")
        except Exception as e:
            self.logger.error(f"ERROR - Could not save {url} - {e}")

    def get_in_memory_image(self, url: str, format: str):
        image_content = self.__download_image_content(url)
        image_hash = hashlib.sha1(image_content).hexdigest()[:10] + '.jpeg'
        try:
            image_file = io.BytesIO(image_content)
            pil_image = Image.open(image_file).convert('RGB')
            in_mem_file = io.BytesIO()
            pil_image.save(in_mem_file, format=format)
            return in_mem_file.getvalue(), image_hash
        except Exception as e:
            self.logger.error(f"Could not get image data: {e}")

    def close_connection(self):
        self.driver.quit()

    def __download_image_content(self, url):
        try:
            return requests.get(url).content
        except Exception as e:
            self.logger.error(f"ERROR - Could not download {url} - {e}")

    def __scroll_to_end(self, sleep_time):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_time)

    def __click_and_wait(self, img, wait_time):
        try:
            img.click()
            time.sleep(wait_time)
        except Exception:
            return

    def __add_image_urls_to_set(self, image_urls: set):
        actual_images = self.driver.find_elements_by_css_selector('img.n3VNCb')
        for actual_image in actual_images:
            if actual_image.get_attribute('src') and 'http' in actual_image.get_attribute('src'):
                image_urls.add(actual_image.get_attribute('src'))

    def __get_default_chrome_options(self):
        chrome_options = webdriver.ChromeOptions()

        lambda_options = [
            '--autoplay-policy=user-gesture-required',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-breakpad',
            '--disable-client-side-phishing-detection',
            '--disable-component-update',
            '--disable-default-apps',
            '--disable-dev-shm-usage',
            '--disable-domain-reliability',
            '--disable-extensions',
            '--disable-features=AudioServiceOutOfProcess',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-notifications',
            '--disable-offer-store-unmasked-wallet-cards',
            '--disable-popup-blocking',
            '--disable-print-preview',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-setuid-sandbox',
            '--disable-speech-api',
            '--disable-sync',
            '--disk-cache-size=33554432',
            '--hide-scrollbars',
            '--ignore-gpu-blacklist',
            '--ignore-certificate-errors',
            '--metrics-recording-only',
            '--mute-audio',
            '--no-default-browser-check',
            '--no-first-run',
            '--no-pings',
            '--no-sandbox',
            '--no-zygote',
            '--password-store=basic',
            '--use-gl=swiftshader',
            '--use-mock-keychain',
            '--single-process',
            '--headless']

        #chrome_options.add_argument('--disable-gpu')
        for argument in lambda_options:
            chrome_options.add_argument(argument)
        chrome_options.add_argument('--user-data-dir={}'.format(self._tmp_folder + '/user-data'))
        chrome_options.add_argument('--data-path={}'.format(self._tmp_folder + '/data-path'))
        chrome_options.add_argument('--homedir={}'.format(self._tmp_folder))
        chrome_options.add_argument('--disk-cache-dir={}'.format(self._tmp_folder + '/cache-dir'))

        return chrome_options
