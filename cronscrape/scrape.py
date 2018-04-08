import base64
from contextlib import contextmanager
import datetime as dt
from functools import wraps
from io import BytesIO
import logging
import time

from PIL import Image
from pyvirtualdisplay.smartdisplay import SmartDisplay
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

from cronscrape import settings


log = logging.getLogger(__name__)

IMPLICIT_WAIT = 10


@contextmanager
def get_display():
    kwargs = {
        'visible': 0 if settings.is_production() else 1,
        'bgcolor': 'black',
        'size': (1920, 1080),
    }

    if settings.is_production():
        with SmartDisplay(**kwargs):
            yield
    else:
        yield


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
    log.debug('Logging into Cronometer.')

    driver.implicitly_wait(IMPLICIT_WAIT)

    driver.get('https://cronometer.com/')

    driver.find_element_by_css_selector('#loginli > a').click()
    WebDriverWait(driver, IMPLICIT_WAIT).until(
        expected_conditions.element_to_be_clickable((By.NAME, 'username'))
    )
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
    if previous:
        log.debug('Advancing to previous day.')
    else:
        log.debug('Advancing to next day.')

    datepicker = driver.find_element_by_class_name('gwt-DatePicker')
    datepicker.find_element_by_xpath(
        '../div[1]//button[{button_num}]'.format(button_num=1 if previous else 2)
    ).click()


def resize_to_page(driver):
    body = driver.find_element_by_xpath('//body')
    driver.set_window_size(body.size['width'] + 20, body.size['height'] + 20)


def get_screenshot(driver, element):
    """
    This method is necessary because the Chrome and Firefox webdrivers don't implement screenshots for elements.
    """
    log.debug('Taking screenshot of page.')

    resize_to_page(driver)

    loc = element.location
    size = element.size
    screenshot = driver.get_screenshot_as_png()
    image = Image.open(BytesIO(screenshot))
    image = image.crop((
        loc['x'], loc['y'],
        loc['x'] + size['width'], loc['y'] + size['height']
    ))

    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return str(base64.b64encode(buffer.getvalue()))


@page_wait
def collect_day_stats(driver):
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

    log.debug('Collected stats: %s', str(results))

    page_element = driver.find_element_by_xpath('//table[@align="center"]/tbody')
    results['screenshot'] = get_screenshot(driver, page_element)

    return results


def collect_days(num_days):
    now = dt.datetime.utcnow()
    time_diff = now - settings.get_start_time()
    days_diff = time_diff.days

    with get_display():
        driver = webdriver.Firefox()

        login(driver)

        if now.hour < 6 + 8:  # 6 hours past midnight, PST
            advance_day(driver, previous=True)
            days_diff -= 1

        results = {}
        for day in range(num_days):
            log.debug('Scraping results for day %d.', days_diff)
            results[days_diff] = collect_day_stats(driver)
            advance_day(driver, previous=True)
            days_diff -= 1

        driver.close()

        return results


def render_reports(stats):
    log.debug('Rendering report results.')

    if len(stats) < 2:
        return []

    days = sorted(stats.items(), reverse=True)
    current_day, current_data = days[0]

    results = []
    missable = lambda x: x or "[unknown]"
    fl = lambda x: round(x, 1) if x is not None else None
    for previous_day, previous_data in days[1:]:
        consumed_diff = current_data["consumed"] - current_data["burned"]
        try:
            weight_diff = current_data["night_weight"] - previous_data["night_weight"]
        except TypeError:
            weight_diff = None

        start_weight = float(settings.get('start_weight'))
        ytd_weight = (fl(current_data["night_weight"] - start_weight)) if current_data["night_weight"] else '[unknown]'

        results.append({
            'report': (
                f'Day {current_day}:\n\n'
                f'Morning Weight: {missable(fl(current_data["morning_weight"]))} lbs\n'
                f'Consumed: {fl(current_data["consumed"])} kcal '
                f'({fl(consumed_diff)} kcal {"deficit" if consumed_diff < 0 else "surplus"})\n'
                f'Night weight: {missable(fl(current_data["night_weight"]))} lbs\n'
                f'Difference since yesterday: {missable(fl(weight_diff))} lbs '
                f'from {missable(fl(previous_data["night_weight"]))}\n'
                f'YTD: {ytd_weight} lbs from {fl(start_weight)}'
            ),
            'screenshot': current_data['screenshot'],
        })

        current_day, current_data = previous_day, previous_data
    return results


def collect_latest_reports(days):
    log.debug('Collecting latest reports for the last %d days.', days)
    return render_reports(collect_days(days + 1))
