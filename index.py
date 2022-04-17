import os
from collections import defaultdict
from itertools import chain
import traceback
from pkg_resources import require
from selenium.webdriver.common.by import By
import datetime
from selenium import webdriver
import requests
import json
import time
from tqdm import tqdm
import argparse

class Browser():

    def __init__(self):
        self.url = 'https://www.zerogangnam.com/reservation'

    def get_driver(self):
        driver = self._create_session()
        driver.get(url=self.url)
        return driver

    def _create_session(self):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument("disable-gpu")
        options.add_argument(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36")
        options.add_argument('window-size=1920,1080')

        driver = webdriver.Chrome('chromedriver', chrome_options=options)
        driver.implicitly_wait(5)

        return driver

    def quit(self, driver):
        driver.quit()


class Worker():
    def __init__(self, driver):
        self.driver = driver

    def get_schedule(self, dt, theme_name):
        self.click_calendar(dt)
        self.click_theme(theme_name)
        times = self.get_times()

        return times

    def click_calendar(self, dt):
        date_q = f'''div[data-year="{dt.year}"][data-month="{dt.month - 1}"][data-date="{dt.day}"]'''
        
        if not len(self.driver.find_elements(by=By.CSS_SELECTOR, value=date_q)):
            self.move_to_available_month()

        self.driver.find_element(by=By.CSS_SELECTOR, value=date_q).click()
        time.sleep(3)

    def get_times(self):
        r = {}

        for el in self.driver.find_elements(by=By.CSS_SELECTOR, value='input[name="reservationTime"]'):
            hms = el.get_attribute('value')
            dt = datetime.datetime.strptime(hms, '%H:%M:%S')
            r[hms] = {
                'reservation': True if el.get_attribute('disabled') else False,
                'hour': dt.hour,
                'minute': dt.minute,
                'second': dt.second
            }

        return r

    def click_theme(self, theme_name):
        for el in self.driver.find_elements(by=By.CSS_SELECTOR, value=f'#themeChoice > label > span'):
            if el.text.strip() == theme_name:
                el.find_element(by=By.XPATH, value='./..').click()
                time.sleep(3)
                return

        raise ValueError('cannot found theme name')


    def _get_available_dates_current_page(self):
        r = []
        for el in self.driver.find_elements(by=By.CSS_SELECTOR, value='''div.datepicker--cell-day'''):
            if el.get_attribute('class').find('-disabled-') == -1:
                year, month, day = int(el.get_attribute('data-year')), int(
                    el.get_attribute('data-month')) + 1, int(el.get_attribute('data-date'))

                r.append(datetime.datetime(year, month, day).date())
        return r

    def get_available_dates(self):
        available_dates = []

        available_dates.extend(self._get_available_dates_current_page())

        self.move_to_available_month()

        available_dates.extend(self._get_available_dates_current_page())

        return available_dates

    def move_to_available_month(self):
        return self.move_calendar(self.get_arrow_direction())
    
    def move_calendar(self, direction):
        '''
            prev | next
        '''
        for el in self.driver.find_elements(by=By.CSS_SELECTOR, value=
            f'''div.datepicker--nav-action[data-action="{direction}"]'''):
            if el.get_attribute('class').find('-disabled-') == -1:
                el.click()
                
        time.sleep(3)
    
    def get_arrow_direction(self):
        return 'prev' if len(self.driver.find_elements(by=By.CSS_SELECTOR, value=
            f'''div.datepicker--nav-action[data-action="prev"]''')) else 'next'
        

class Slack():
    def __init__(self):
        self.url = 'https://hooks.slack.com/services/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'

    def send(self, message):
        return requests.post(self.url, data=json.dumps({'text': message}, ensure_ascii=False).encode('utf-8'), headers={'Content-type': 'application/json'})


class Statistics():
    def __init__(self, schedules):
        self.schedules = schedules

    def get_items(self, type_='all'):
        
        r = defaultdict(lambda: dict())
        for p1 in self.schedules:
            if type_ == 'available':
                condition = lambda p2: not p2['reservation']
            elif type_ =='unavailable':
                condition = lambda p2: p2['reservation']
            elif type_ == 'all':
                condition = lambda _: True
            else:
                raise ValueError(f'invalid type {type_}')

            
            r[p1['date']] = list(filter(condition, p1['schedule'].values()))
            # r.extend([{'item': p, 'date': p1['date']} for p in )

        return r

    def get_items_values(self, items):
        return list(chain(*items.values()))

class Formatter():

    def __init__(self, stat):
        self.stat = stat
        self.ok_sign = '👋'
        self.not_ok_sign = '😷'
        # self.ok_sign = 'O'
        # self.not_ok_sign = 'X'        

    def get(self, theme_name, important_datetimes=[]):

        important_dt_exists = self.is_exists(important_datetimes, type_='available')
        # 🟢🔴⚪🟢🔵
        return f'''

\t*{theme_name} (제로월드 강남점) *
>\t😐 전체: {self.get_items_length()}
>\t😀 가능: {self.get_items_length('available')}
>\t😷 불가능: {self.get_items_length('unavailable')}
>\t🤔 알람설정: {self.get_datetimes_format(important_datetimes)} {'<!channel>' if important_dt_exists else ''} 

{self.get_items_info('available')}

        '''

    def get_datetimes_format(self, dts):
        r = []
        for dt in dts:
            r.append(dt.strftime('%Y년 %m월 %d일'))

        return ' / '.join(r)

    def get_items_length(self, type_='all'):
        return len(self.stat.get_items_values(self.stat.get_items(type_)))

    def get_ko_weekday(self, dt):
        return {0: '월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}[dt.weekday()]

    def get_items_info(self, type_='all'):
        if type_ == 'all':
            mark = ''
        elif type_ == 'available':
            mark = self.ok_sign
        elif type_ =='unavailable':
            mark = self.not_ok_sign

        # mark = self.not_ok_sign if p2['reservation'] else self.ok_sign
        r = []
        for date, p1 in self.stat.get_items(type_).items():
            dt = datetime.datetime.strptime(date, '%Y-%m-%d')
            if len(p1):
                r.append(f'\t*{dt.year}년 {dt.month}월 {dt.day}일 ({self.get_ko_weekday(dt)})*')
            m = []
            for p2 in p1:
                hour, minute = [p2['hour'], p2['minute']]
                
                m.append(f'{hour}시 {minute}분')
                # r.append(f'>\t{mark} {hour}시 {minute}분')

            if len(m):
                r.append(f'> \t{mark} '+ ' | '.join(m))
        return '\n'.join(r)
    
    def is_exists(self, dts, type_='all'):
        for dt in dts:
            items = self.stat.get_items(type_)
            key = dt.strftime('%Y-%m-%d')
            if key in items:
                print(key, items.keys())
                if len(items[key]):
                    return True

        return False

class Argument():
    def parse(self):
        parser = argparse.ArgumentParser()

        parser.add_argument('--theme-name', help='theme name(ex: [강남] 링)', required=True)
        parser.add_argument('--important-datetimes', help='important datetimes(ex: 2021-01-01,2021-02-01)', default='')

        args = parser.parse_args()
        args.important_datetimes = [datetime.datetime.strptime(s, '%Y-%m-%d') for s in args.important_datetimes.split(',') if s.strip()]

        return args

driver = None
try:
    args = Argument().parse()
    print(args)

    browser = Browser()
    driver = browser.get_driver()

    worker = Worker(driver)

    available_dates = worker.get_available_dates()


    schedules = []
    for i, dt in enumerate(tqdm(available_dates)):
        schedules.append({
            'date': dt.strftime('%Y-%m-%d'),
            'schedule': worker.get_schedule(dt, theme_name=args.theme_name)
        })
        # if i > 1:
        #     break
        # break

    basename = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    os.makedirs('dest', exist_ok=True)
    with open(f'dest/{basename}.json', 'w', encoding='utf-8') as fp:
        fp.write(json.dumps(schedules, ensure_ascii=False, indent=4))

    # with open(f'dest/{basename}.json', 'r', encoding='utf-8') as fp:
    #     schedules = json.loads(fp.read())

    stat = Statistics(schedules)
    message = Formatter(stat).get(theme_name=args.theme_name, important_datetimes=args.important_datetimes)
    Slack().send(message)
except:
    Slack().send(traceback.format_exc())
finally:
    if driver:
        driver.quit()
