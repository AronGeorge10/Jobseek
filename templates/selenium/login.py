import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestLogin(unittest.TestCase):
    def setUp(self):
        # Initialize the WebDriver (Chrome in this example)
        self.driver = webdriver.Chrome()
        self.driver.get("http://127.0.0.1:5000/")
        logging.info("Browser opened and navigated to login page")
        # Wait for the page to load
        self.wait = WebDriverWait(self.driver, 10)

    def find_element_with_wait(self, by, value):
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def test_successful_login(self):
        # Find and fill in the email input
        email_input = self.find_element_with_wait(By.ID, "email")
        email_input.send_keys("antonthomas2025@mca.ajce.in")
        logging.info("Email entered")

        # Find and fill in the password input
        password_input = self.find_element_with_wait(By.ID, "password")
        password_input.send_keys("Anton123")
        logging.info("Password entered")

        # Find and click the login button
        login_button = self.find_element_with_wait(By.ID, "signin")
        login_button.click()
        logging.info("Login button clicked")

        # Wait for the URL to change, indicating successful login
        self.wait.until(EC.url_changes("http://127.0.0.1:5000/"))
        logging.info("URL changed, indicating successful login")

        # Print success message
        logging.info("Login successful!")

    def tearDown(self):
        # Close the browser
        self.driver.quit()
        logging.info("Browser closed")

if __name__ == "__main__":
    unittest.main()
