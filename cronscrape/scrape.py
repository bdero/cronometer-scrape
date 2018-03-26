from contextlib import contextmanager

from pyvirtualdisplay.smartdisplay import SmartDisplay
from selenium import webdriver

from cronscrape import settings


@contextmanager
def get_display(**kwargs):
    defaults = {
        'visible': 0,
        'bgcolor': 'black',
        'size': (1920, 1080),
    }.update(kwargs)

    if settings.is_production():
        with SmartDisplay(**kwargs) as display:
            yield display
    else:
        # Don't use a virtual display when running locally.
        yield


def _login(driver):
    driver.get('https://cronometer.com/')

    driver.implicitly_wait(0.5)
    driver.find_element_by_css_selector('#loginli > a').click()
    driver.find_element_by_name('username').send_keys(settings.get('cronometer_email'))
    driver.find_element_by_name('password').send_keys(settings.get('cronometer_password'))
    driver.find_element_by_id('login-button').click()


def fetch_kcal_table():
    with get_display():
        driver = webdriver.Chrome()
        _login(driver)
