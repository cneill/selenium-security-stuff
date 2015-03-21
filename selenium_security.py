import unittest
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common import proxy
from selenium.common.exceptions import UnexpectedAlertPresentException

"""Cool toys:

driver.save_screenshot(file_path) - save a screenshot of the page to a file
driver.back() / driver.forward() - browser history
driver.find_element*() - basically sizzle
driver.execute_script(javascript) - execute arbitrary JavaScript in the browser
driver.page_source - get the page's HTML source code

"""


config = {
    'proxy': 'localhost:8080',
    'base_url': 'http://localhost:8888/'
}


# Helper function to get all the GET variables in a given URL.
# Returns a list of tuples with (name, value) pairs

def get_generic_fuzz_checks():
    strings = {
        'XSS': {
            'string': '\'"><img src=x onerror=alert(1)>',
            'check': 'alert',
            'fail_if': True
        },
        'SQL': {
            'string': '\'" or 1=1',
            'check': 'body',
            'fail_if': 'SQL syntax'
        },
        """
        'Random_chars': {
            'string': chr(0) + chr(80) + unichr(255) + unichr(0xffff),
            'check': 'body',
            'fail_if': 'fail'
        },
        """
        'CMD_injection': {
            'string': chr(0) + ';`cat /etc/passwd`',
            'check': 'body',
            'fail_if': 'root:'
        }

    }
    return strings


# class TestSequenceFunctions(unittest.TestCase):
class SeleniumTestCase(unittest.TestCase):

    # Set up our class for each test case
    def setUp(self):
        # Set up our proxy if one is defined
        if config['proxy']:
            p = proxy.Proxy({
                'proxyType': proxy.ProxyType.MANUAL,
                'httpProxy': config['proxy'],
                'sslProxy': config['proxy']
            })
            self.driver = webdriver.Firefox(proxy=p)
        else:
            self.driver = webdriver.Firefox()

        self.base_url = config['base_url']
        self.vulnerable_urls = []

    # Tear down our class after each test case, print vulnerabilities if any
    def tearDown(self):
        self.driver.close()
        if len(self.vulnerable_urls) > 0:
            print "\nFound vulnerabilities!\n"
            for vuln in self.vulnerable_urls:
                print vuln
        else:
            print "\nNo vulnerabilities found\n"
        print "=" * 70, "\n"

    # Helper method to extract variables from the current URL
    # Returns list of tuples in (name, value) format.
    def get_url_variables(self):
        matches = re.findall(
            '[\?&]([^=]+)=([^\?&$ ]+)', self.driver.current_url
        )
        return matches

    # Helper method to get the links for the current page
    # Returns a list of tuples in (link text, link URL) format
    def get_links(self):
        results = []
        links = self.driver.find_elements_by_css_selector('a')
        for link in links:
            url = link.get_attribute('href')
            text = link.text
            results.append((text, url))
        return results

    # Pass in a dictionary of variables and values, add these to a URL
    # Returns a URL with all the variables defined
    def define_url_variables_with_dict(self, url, variables_dict):
        # Strip out any current URL variables
        temp_url = re.sub('[\?&]([^=]+)=([^\?&$ ]+)', '', url).strip()
        first = True

        for variable in variables_dict:
            if first:
                first = False
                temp_url = "{0}?{1}={2}".format(
                    temp_url, variable, variables_dict[variable]
                )
            else:
                temp_url = "{0}&{1}={2}".format(
                    temp_url, variable, variables_dict[variable]
                )
        return temp_url

    # Inject each of your fuzz strings into each variable in 'variables'
    # attack_type = (all | single)
    def fuzz_url_variables(self, url, variables, attack_type):
        """Inject each of your fuzz strings into each variable
        url = base URL to begin attack from
        variables = list of variables to inject into the URL
        attack_type = (all | single)
        """

        if not isinstance(variables, list):
            print "Unknown type for variables"

        attack_targets = []
        variables_dict = {}

        url_variables = self.get_url_variables()
        fuzz_checks = get_generic_fuzz_checks()

        for fuzz_check in fuzz_checks:
            variables_dict = {}
            for i, variable in enumerate(url_variables):
                if attack_type == "single":
                    variables_dict = {}

                variables_dict[variable[0]] = fuzz_checks[fuzz_check]['string']

                if attack_type == "single":
                    attack_url = self.define_url_variables_with_dict(
                        url, variables_dict
                    )

                    attack_targets.append({
                        'check': fuzz_checks[fuzz_check], 'url': attack_url
                    })

                elif attack_type == "all":
                    if i == len(url_variables) - 1:
                        attack_url = self.define_url_variables_with_dict(
                            url, variables_dict
                        )

                        attack_targets.append({
                            'check': fuzz_checks[fuzz_check], 'url': attack_url
                        })

        self.get_attack(attack_targets)

    def get_attack(self, attack_targets):
        for target in attack_targets:
            if target['check']['check'] == 'body':
                self.driver.get(target['url'])
                if target['check']['fail_if'] in self.driver.page_source:
                    print "GOT ONE!"
                    self.vulnerable_urls.append(target['url'])
            elif target['check']['check'] == 'alert':
                try:
                    self.driver.get(target['url'])

                except UnexpectedAlertPresentException as e:
                    if int(e.alert_text) is 1:
                        print "GOT ONE!"
                        self.vulnerable_urls.append(target['url'])

    # TEST-SPECIFIC CODE STARTS HERE #

    def login(self):
        self.driver.get(self.base_url + 'login.php')

        user_field = self.driver.find_element_by_name('user')
        pass_field = self.driver.find_element_by_name('pass')
        submit_field = self.driver.find_element_by_name('signin')

        user_field.send_keys("demo")
        pass_field.send_keys("demo")
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
            if "SQL syntax" in self.driver.page_source:
                self.vulnerable_urls.append(self.driver.current_url)

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
            if 'login' not in link:
                self.driver.get(link)

            url_variables = self.get_url_variables()
            self.fuzz_url_variables(
                self.driver.current_url, url_variables, 'all'
            )
    """


if __name__ == '__main__':
    unittest.main(verbosity=0)
