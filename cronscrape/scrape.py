from contextlib import contextmanager
import datetime as dt
from functools import wraps
import time

from pyvirtualdisplay.smartdisplay import SmartDisplay
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

from cronscrape import settings


IMPLICIT_WAIT = 10


@contextmanager
def get_display():
    kwargs = {
        'visible': 0,
        'bgcolor': 'black',
        'size': (1920, 1080),
    }

    with SmartDisplay(**kwargs) as display:
        yield display


def page_wait(func):
    @wraps(func)
    def wrapper(driver, *args, **kwargs):
        WebDriverWait(driver, IMPLICIT_WAIT).until(
            expected_conditions.presence_of_element_located((By.CLASS_NAME, 'diary_side_box'))
        )

        # Exit out of the cronometer upgrade popup if/when it comes up.
        driver.implicitly_wait(0.2)
        try:
            popup_panel = driver.find_element_by_class_name('gwt-PopupPanel')
        except NoSuchElementException:
            pass
        else:
            if popup_panel.is_displayed():
                popup_panel.find_element_by_xpath('//button').click()
                time.sleep(0.2)

        driver.implicitly_wait(IMPLICIT_WAIT)

        # The servings panel takes time to populate after the containers render.
        time.sleep(0.5)

        return func(driver, *args, **kwargs)
    return wrapper


def login(driver):
    driver.implicitly_wait(IMPLICIT_WAIT)

    driver.get('https://cronometer.com/')

    driver.find_element_by_css_selector('#loginli > a').click()
    driver.find_element_by_name('username').send_keys(settings.get('cronometer_email'))
    driver.find_element_by_name('password').send_keys(settings.get('cronometer_password'))
    driver.find_element_by_id('login-button').click()

    remove_ads(driver)


@page_wait
def remove_ads(driver):
    driver.execute_script(
        'let iframes = document.getElementsByTagName("iframe"); for (let x of iframes) { x.hidden = true; }'
    )


@page_wait
def advance_day(driver, previous=False):
    datepicker = driver.find_element_by_class_name('gwt-DatePicker')
    datepicker.find_element_by_xpath(
        '../div[1]//button[{button_num}]'.format(button_num=1 if previous else 2)
    ).click()


@page_wait
def collect_stats(driver):
    results = {
        'morning_weight': None,
        'night_weight': None,
    }

    elements = driver.find_elements_by_css_selector('.servingsPanel tr')[1:]
    for index, row in enumerate(elements):
        description, amount, unit = row.text.split('\n')[:3]

        if description == 'Weight':
            if index > len(elements)/2:
                results['night_weight'] = float(amount)
            elif results['morning_weight'] is None:
                results['morning_weight'] = float(amount)

    consumed_el = (
        driver.find_element_by_css_selector('.diary_side_box > .row')
        .find_element_by_xpath('./div[contains(@class, "column")][1]/div/div[1]')
    )
    burned_el = (
        driver.find_element_by_css_selector('.diary_side_box > .row')
        .find_element_by_xpath('./div[contains(@class, "column")][3]/div/div[1]')
    )
    results['consumed'] = float(consumed_el.text)
    results['burned'] = float(burned_el.text)

    page_element = driver.find_element_by_xpath('//table[@align="center"]/tbody')

    return results


def collect_days(days):
    now = dt.datetime.utcnow()
    time_diff = now - settings.get_start_time()
    days_diff = time_diff.days

    with get_display() as display:
        driver = webdriver.Chrome()
        login(driver)

        if now.hour < 6 + 8:  # 6 hours past midnight, PST
            advance_day(driver, previous=True)
            days_diff -= 1

        results = {}
        for day in range(days):
            results[days_diff] = collect_stats(driver)
            results[days_diff]['screenshot'] = display.waitgrab()

            advance_day(driver, previous=True)
            days_diff -= 1

        return results


if __name__ == '__main__':
    stats = collect_days(10)
