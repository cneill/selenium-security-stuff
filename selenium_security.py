import unittest
import re

from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.common import proxy
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
    'base_url': 'http://localhost:8888/',
    'screenshot_failures': True
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


class FuzzResponseObject():
    def __init__(self, driver):
        self.driver = driver
        self.url = driver.current_url
        self.page_source = driver.page_source
        self.cookies = driver.get_cookies()
        self.title = driver.title

        if config['screenshot_failures']:
            self.screenshot = driver.get_screenshot_as_png()


class FuzzRequestObject():
    def __init__(self, driver, fuzz_check, url, method='get', data=None):
        self.driver = driver
        self.fuzz_check = fuzz_check
        self.method = method
        self.url = url
        self.data = data

    def execute_fuzz_check(self, driver):
        # Check for a string in the body
        if self.fuzz_check.check == 'body':
            response = self.perform_request()
            if self.fuzz_check.fail_if in response.page_source:
                print "GOT ONE!"

        # Check for an alert box with a value
        elif self.fuzz_check.check == 'alert':
            try:
                self.driver.get(self.url)

            except UnexpectedAlertPresentException as e:
                if int(e.alert_text) is 1:
                    print "GOT ONE!"
                    self.vulnerable_urls.append(self.url)

    def perform_request(self):
        if self.method == 'get':
            self.driver.get(self.url)

        elif self.method == 'post':
            print 'hi'

        elif self.method == 'put':
            print 'hi'

        elif self.method == 'delete':
            print 'hi'


class FuzzCheck():
    def __init__(self, check, fail_if):
        self.check = check
        self.fail_if = fail_if

    def get_fuzz_request_object(self, url, method='get', data=None):
        return FuzzRequestObject(self, method, url, data)

    def check_fail(self):
        print 'hi'


# class TestSequenceFunctions(unittest.TestCase):
class SeleniumTestCase(unittest.TestCase):

    # Set up our class for each test case
    def setUp(self):
        # Set up our proxy if one is defined
        if config['proxy']:
            """
            Not using Firefox anymore...
            p = proxy.Proxy({
                'proxyType': proxy.ProxyType.MANUAL,
                'httpProxy': config['proxy'],
                'sslProxy': config['proxy']
            })
            self.driver = webdriver.Firefox(proxy=p)
            """
            args = ['--proxy=' + config['proxy'], '--proxy-type=http']
            self.driver = webdriver.PhantomJS(service_args=args)
        else:
            self.driver = webdriver.Firefox()

        self.base_url = config['base_url']
        self.failed_fuzz_checks = []

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

    # Get variables from the current URL
    # Returns list of tuples in (name, value) format.
    def get_url_variables(self):
        matches = re.findall(
            '[\?&]([^=]+)=([^\?&$ ]+)', self.driver.current_url
        )
        return matches

    # Get links from the current page
    # Returns a list of tuples in (link text, link URL) format
    def get_links(self):
        results = []
        links = self.driver.find_elements_by_tag_name('a')
        for link in links:
            url = link.get_attribute('href')
            text = link.text
            results.append((text, url))
        return results

    # Get forms with input fields from the current page
    # Returns a list of objects with 'form', 'method', and 'fields'
    def get_forms_with_inputs(self):
        form_fields = []
        forms = self.driver.find_elements_by_tag_name('form')

        for form in forms:
            fields = form.find_elements_by_tag_name('input')
            if len(fields) > 0:
                obj = {
                    'form': form,
                    'method': form.get_attribute('method'),
                    'fields': fields,
                    'num_fields': len(fields)
                }
                form_fields.append(obj)

        return form_fields

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

    def fuzz_url_variables(self, url, variables, attack_type='all'):
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

        # self.get_attack(attack_targets)
        self.test_fuzz_check()

    def fuzz_forms(self, url, forms, attack_type='all'):
        """Inject each of your fuzz strings into each form variable
        url = URL to begin attack from
        forms = List of form objects (returned from get_forms_with_inputs)
        attack_type = (all | single)
        """

    def test_fuzz_check(self, attack_targets, method='get'):
        """This method does the requesting, and checks to see if the fuzz check
        fails based on its 'fail_if' condition
        attack_targes = list of fuzz check objects
        method = (get | post | put | delete)
        """
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
