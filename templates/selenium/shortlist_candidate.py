import unittest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import sys
import os
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestShortlistCandidate(unittest.TestCase):
    def setUp(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(options=chrome_options)
        logging.info("Chrome browser initialized with maximized window")
        self.driver.get("http://127.0.0.1:5000/")
        logging.info("Navigated to the application URL")
        self.wait = WebDriverWait(self.driver, 10)

    def test_shortlist_candidate(self):
        try:
            # Login as recruiter
            self.login_as_recruiter()

            # Open profile dropdown menu
            profile_dropdown = self.find_element_with_wait(By.ID, "profileDropdown")
            profile_dropdown.click()
            logging.info("Profile dropdown clicked")

            # Wait for the dropdown menu to be visible
            self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "dropdown-menu")))
            logging.info("Dropdown menu is visible")

            # Click on "Posted Jobs" within the dropdown
            posted_jobs_link = self.find_element_with_wait(By.LINK_TEXT, "Posted Jobs")
            posted_jobs_link.click()
            logging.info("Clicked on 'Posted Jobs' in dropdown")

            # Wait for the posted jobs page to load
            self.wait.until(EC.url_contains("/recruiter/posted_jobs"))
            logging.info("Posted jobs page loaded")

            # Scroll to the bottom to ensure all jobs are loaded
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Allow time for dynamic content loading
            logging.info("Scrolled to the bottom of the page")

            # Locate the first View Applications button
            view_applications_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "(//a[contains(@class, 'main-btn') and contains(text(), 'View Applications')])[1]")
                )
            )
            # Scroll the button into view and click using JavaScript
            self.driver.execute_script("arguments[0].scrollIntoView(true);", view_applications_button)
            time.sleep(1)  # Small delay after scrolling
            self.driver.execute_script("arguments[0].click();", view_applications_button)
            logging.info("Clicked View Applications button using JavaScript")

            # Wait for applications page to load
            self.wait.until(EC.url_contains("view_applications"))
            logging.info("Applications page loaded")

            # Find and click the Shortlist button
            shortlist_button = self.find_element_with_wait(
                By.XPATH,
                "//button[contains(text(), 'Shortlist')]"
            )
            shortlist_button.click()
            logging.info("Clicked Shortlist button")

            # Wait for and click the confirm button in the modal
            confirm_button = self.find_element_with_wait(By.ID, "confirmShortlist")
            confirm_button.click()
            logging.info("Confirmed shortlisting")

            # Verify the status change
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Unshortlist')]"))
            )
            logging.info("Successfully shortlisted candidate")

        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Test failed: {str(e)}")
            logging.error(f"Current URL: {self.driver.current_url}")
            logging.error("Test failed, please check the application state and selectors.")
            self.fail(f"Test failed: {str(e)}")

    def login_as_recruiter(self):
        email_input = self.find_element_with_wait(By.ID, "email")
        password_input = self.find_element_with_wait(By.ID, "password")
        
        email_input.send_keys("arongeorgejain2025@mca.ajce.in")
        logging.info("Recruiter email entered")
        password_input.send_keys("Aron2002")
        logging.info("Recruiter password entered")

        login_button = self.find_element_with_wait(By.ID, "signin")
        login_button.click()
        logging.info("Login button clicked")

        # Wait for login to complete
        self.wait.until(EC.url_contains("/recruiter/index"))
        logging.info("Recruiter login successful")

    def find_element_with_wait(self, by, value):
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def tearDown(self):
        self.driver.quit()
        logging.info("Browser closed")

def run_tests_without_stderr():
    stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    result = unittest.main(exit=False)
    sys.stderr = stderr
    return result

if __name__ == "__main__":
    run_tests_without_stderr()
