from django.test import LiveServerTestCase

import sys
import time
import re
import os
import os.path
import shutil

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException, WebDriverException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class FunctionalTest(LiveServerTestCase):
    DEFAULT_UI_ENDPOINT = 'localhost:8080'
    DEFAULT_WAIT = 5

    BY_ALERT = (By.CLASS_NAME, 'alert')

    @classmethod
    def setUpClass(cls):
        # IMPORTANT: Make sure the window size is big enough to see
        # everything (e.g. links in the nav bar).  Otherwise tests
        # will fail mysteriously because PhantomJS will clip the
        # viewport.
        cls.browser = webdriver.PhantomJS()
        cls.browser.set_window_size(1024, 768)

        # Set up API and UI URLs.  This is intended for future testing
        # against a staging server.  Don't know if it works properly
        # yet (and there are other concerns to be dealt with for
        # staging testing, like database fixtures).
        cls.api_url = None
        cls.ui_url = 'http://' + cls.DEFAULT_UI_ENDPOINT
        for arg in sys.argv:
            if 'ui' in arg:
                cls.ui_url = 'http://' + arg.split('=')[1]
            if 'api' in arg:
                cls.api_url = 'http://' + arg.split('=')[1]
        if cls.api_url is None:
            super().setUpClass()
            cls.api_url = cls.live_server_url

        print('Live server URL:', cls.live_server_url)
        print('        API URL:', cls.api_url)
        cls.screenshot_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'screenshots'
        )
        if os.path.exists(cls.screenshot_dir):
            shutil.rmtree(cls.screenshot_dir)
        os.makedirs(cls.screenshot_dir, exist_ok=True)
        cls.screenshot_index = 1

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super(FunctionalTest, cls).tearDownClass()

    def form(self, f):
        """Find a form of a given class."""
        return self.browser.find_element_by_xpath(
            "//form[contains(@class,'{}')]".format(f)
        )

    def form_field(self, f, field):
        """Find a field in a form of a given class."""
        return self.form(f).find_element_by_xpath("//" + field)

    def wait_for(self, function_with_assertion, timeout=DEFAULT_WAIT):
        """Wait for an assertion to become true."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                return function_with_assertion()
            except (AssertionError, WebDriverException):
                time.sleep(0.1)
        return function_with_assertion()

    def click_through(self, button, wait, screenshot=None):
        """Click a button or link and wait for something to appear."""
        button.click()
        if screenshot is not None:
            self.screenshot(screenshot)
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located(wait)
        )

    def wait_for_no_alerts(self):
        """Wait for all alerts to be cleared by a page reload."""
        WebDriverWait(self.browser, 10).until_not(
            EC.presence_of_element_located((By.CLASS_NAME, 'alert'))
        )

    def assert_has_message(self, msg_type, msg):
        """Check for the presence of a message of a particular type containing
        given text.

        """
        msgs = self.browser.find_element_by_xpath("//div[@id='messages']")
        try:
            msgs.find_element_by_xpath(
                ("div[contains(@class,'{}')]//p[contains(.,'{}')]").
                format(msg_type, msg)
            )
        except NoSuchElementException as e:
            # Debugging help.
            print("Messages: " + msgs.text)
            raise e

    def assert_field_has_error(self, field):
        """Check whether a form field has an error marker: this will be a
        ``has_error`` class on the field's immediate parent.

        """
        cls = field.find_element_by_xpath('..').get_attribute('class')
        assert re.search(r'\bhas-error\b', cls)

    def assert_field_has_no_error(self, field):
        """Check that a form field has no error marker: this will be a
        ``has_error`` class on the field's immediate parent.

        """
        cls = field.find_element_by_xpath('..').get_attribute('class')
        assert not re.search(r'\bhas-error\b', cls)

    def screenshot(self, title=None):
        if title is not None:
            f, _ = unique_file(self.screenshot_dir, title, 1)
        else:
            f, self.screenshot_index = unique_file(self.screenshot_dir,
                                                   'screenshot',
                                                   self.screenshot_index)
        self.browser.save_screenshot(f)


def unique_file(dir, base, startidx):
    f = os.path.join(dir, base + '.png')
    idx = startidx
    if os.path.exists(f):
        f = os.path.join(dir, base + '-{:04d}.png'.format(idx))
        while os.path.exists(f):
            idx = idx + 1
            f = os.path.join(dir, base + '-{:04d}.png'.format(idx))
    return f, idx
