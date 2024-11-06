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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestEnterMeeting(unittest.TestCase):
    def setUp(self):
        # Set up Chrome options for full-screen mode
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")  # This will maximize the browser window
        
        # Initialize the WebDriver with the options
        self.driver = webdriver.Chrome(options=chrome_options)
        logging.info("Chrome browser initialized with maximized window")
        
        self.driver.get("http://127.0.0.1:5000/")  # Assuming this is the URL for index.html
        logging.info("Navigated to the application URL")
        self.wait = WebDriverWait(self.driver, 10)

    def test_enter_meeting(self):
        try:
            # Login
            email_input = self.find_element_with_wait(By.ID, "email")
            password_input = self.find_element_with_wait(By.ID, "password")
            
            email_input.send_keys("antonthomas2025@mca.ajce.in")  # Replace with a valid test email
            logging.info("Email entered")
            password_input.send_keys("Anton123")  # Replace with a valid test password
            logging.info("Password entered")

            login_button = self.find_element_with_wait(By.ID, "signin")
            login_button.click()
            logging.info("Login button clicked")

            # Wait for login to complete and page to load
            self.wait.until(EC.url_contains("http://127.0.0.1:5000/"))
            logging.info("Login successful, main page loaded")

            # Click on "Apply" in the navbar
            apply_link = self.find_element_with_wait(By.LINK_TEXT, "Apply")
            apply_link.click()
            logging.info("Clicked on 'Apply' in navbar")

            # Wait for job postings page to load
            self.wait.until(EC.url_contains("/job_postings"))
            logging.info("Job postings page loaded")

            # Click "View Details" on the first job listing
            view_details_button = self.find_element_with_wait(By.XPATH, "//a[contains(@class, 'btn-primary') and contains(text(), 'View Details')]")
            view_details_button.click()
            logging.info("Clicked on 'View Details' for the first job")

            # Wait for job details page to load
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "job-details")))
            logging.info("Job details page loaded")
            
            # Scroll down to the bottom of the page
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            import time
            time.sleep(1)

            # Click on the "Enter Meeting" button
            enter_meeting_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "enter-meeting-btn"))
            )
            enter_meeting_button.click()
            logging.info("Clicked on 'Enter Meeting' button")

            # Add any additional assertions or actions here

        except (TimeoutException, NoSuchElementException) as e:
            self.fail(f"Test failed: {str(e)}\nCurrent URL: {self.driver.current_url}\n"
                      f"Page title: {self.driver.title}\n"
                      f"Visible text: {self.driver.find_element(By.TAG_NAME, 'body').text[:500]}...")

    def find_element_with_wait(self, by, value):
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def tearDown(self):
        self.driver.quit()

def run_tests_without_stderr():
    # Redirect stderr to devnull
    stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    
    # Run the tests
    result = unittest.main(exit=False)
    
    # Restore stderr
    sys.stderr = stderr
    
    return result

if __name__ == "__main__":
    run_tests_without_stderr() 