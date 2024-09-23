import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class TestLogin(unittest.TestCase):
    def setUp(self):
        # Initialize the WebDriver (Chrome in this example)
        self.driver = webdriver.Chrome()
        self.driver.get("http://127.0.0.1:5000/")  # Updated URL
        # Wait for the page to load
        self.wait = WebDriverWait(self.driver, 10)

    def find_element_with_wait(self, by, value):
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def test_successful_login(self):
        try:
            # Try to find the email input
            email_input = self.find_element_with_wait(By.ID, "email")
            password_input = self.find_element_with_wait(By.ID, "password")
            
            # If found, proceed with the test
            email_input.send_keys("antonthomas2025@mca.ajce.in")  # Replace with a valid test email
            password_input.send_keys("Anton123")  # Replace with a valid test password

            # Find and click the login button
            login_button = self.find_element_with_wait(By.ID, "signin")
            login_button.click()

            # Wait for successful login (adjust as needed)
            self.wait.until(
                EC.url_changes("http://127.0.0.1:5000/")
            )

            # Verify that login was successful (you may need to adjust this based on your app's behavior)
            # For example, check if a certain element exists on the logged-in page
            logged_in_element = self.find_element_with_wait(By.ID, "logged-in-element")
            self.assertTrue(
                logged_in_element.is_displayed()
            )

        except TimeoutException:
            # If element not found, print the page source for debugging
            print("Page source:", self.driver.page_source)
            raise

    def test_failed_login(self):
        try:
            # Find the email and password input fields
            email_input = self.find_element_with_wait(By.ID, "email")
            password_input = self.find_element_with_wait(By.ID, "password")

            # Enter invalid credentials
            email_input.send_keys("invalid@example.com")
            password_input.send_keys("wrongpassword")

            # Find and click the login button
            login_button = self.find_element_with_wait(By.ID, "signin")
            login_button.click()

            # Wait for error message
            error_message = self.find_element_with_wait(By.CLASS_NAME, "alert-danger")

            # Verify that the error message is displayed
            self.assertTrue(error_message.is_displayed())
            self.assertIn("Invalid email or password", error_message.text)

        except TimeoutException:
            # If element not found, print the page source for debugging
            print("Page source:", self.driver.page_source)
            raise

    def tearDown(self):
        # Close the browser
        self.driver.quit()

if __name__ == "__main__":
    unittest.main()
