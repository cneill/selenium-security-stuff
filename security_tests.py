import unittest

from selenium_security import SeleniumTestCase
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import UnexpectedAlertPresentException

config = {
    'proxy': 'localhost:8080',
    'base_url': 'http://localhost:8888/',
    'screenshot_failures': True
}


class TrackerDBTest(SeleniumTestCase):

    def login(self):
        self.driver.get(self.base_url + 'login.php')

        user_field = self.driver.find_element_by_name('user')
        pass_field = self.driver.find_element_by_name('pass')
        submit_field = self.driver.find_element_by_name('signin')

        user_field.send_keys('demo')
        pass_field.send_keys('demo')
        submit_field.send_keys(Keys.RETURN)

    # Test for SQL injection on the billing.php page
    def test_sqli1(self):
        self.login()

        us_billing_link = self.driver.find_element_by_name('us_billing')
        us_billing_link.click()

        variables = self.get_url_variables()

        print "-" * 70, "\nStarting SQLi attack...\n", "-" * 70

        for variable in variables:
            attack_url = self.base_url + 'billing.php?{0}={1}'
            test_payload = "'"

            self.driver.get(attack_url.format(variable[0], test_payload))
            # Look for a common SQL server error message to determine success
            assert("SQL syntax" not in self.driver.page_source)
            # if "SQL syntax" in self.driver.page_source:
            #    self.vulnerable_urls.append(self.driver.current_url)

    # Test for Cross-site scripting on the billing.php page
    def test_xss1(self):
        self.login()

        us_billing_link = self.driver.find_element_by_name('us_billing')
        us_billing_link.click()

        variables = self.get_url_variables()

        print "-" * 70, "\nStarting XSS attack...\n", "-" * 70

        for variable in variables:
            attack_url = self.base_url + 'billing.php?{0}={1}'
            test_payload = "'\"><img src=x onerror=alert(1)>"

            try:
                self.driver.get(attack_url.format(variable[0], test_payload))

            # Deal with the Selenium exception raised when an alert box pops up
            # If we got an alert box with the text "1", we sere successful
            except UnexpectedAlertPresentException as e:
                if int(e.alert_text) is 1:
                    self.vulnerable_urls.append(self.driver.current_url)

    """
    def test_fuzz_all(self):
        self.login()
        self.driver.get(config['base_url'] + 'billing.php')
        links = self.get_links()
        for text, link in links:

            url_variables = self.get_url_variables()
            self.fuzz_url_variables(
                self.driver.current_url, url_variables, 'all'
            )
    """

if __name__ == '__main__':
    unittest.main(verbosity=0)
