import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

class JobApplicationTest(unittest.TestCase):
    
    def setUp(self):
        # Set up Chrome options
        chrome_options = Options()
        # Uncomment the line below to run in headless mode
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Initialize the Chrome driver
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.maximize_window()
        
        # Set up wait
        self.wait = WebDriverWait(self.driver, 10)
        
    def test_job_application_flow(self):
        driver = self.driver
        
        # 1. Navigate to the login page
        driver.get("http://localhost:5000/")
        
        # 2. Log in with valid credentials
        email_input = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
        password_input = driver.find_element(By.ID, "password")
        
        email_input.send_keys("antonthomas2025@mca.ajce.in")
        password_input.send_keys("Anton123")
        
        # Click the login button - using ID instead of text content
        login_button = driver.find_element(By.ID, "signin")
        login_button.click()
        
        # 3. Wait for the home page to load
        try:
            self.wait.until(EC.url_contains("/index"))
            print("Successfully logged in and redirected to index page")
        except TimeoutException:
            print("Failed to redirect to index page after login")
            driver.save_screenshot("login_failed.png")
            self.fail("Login failed or redirect didn't happen")
        
        # 4. Click on the "Apply" link in the navbar
        try:
            apply_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/seeker/job_postings')]")))
            apply_link.click()
            print("Clicked on Apply link")
        except TimeoutException:
            print("Could not find or click the Apply link")
            driver.save_screenshot("apply_link_not_found.png")
            self.fail("Apply link not found or not clickable")
        
        # 5. Wait for the job postings page to load
        try:
            self.wait.until(EC.url_contains("/seeker/job_postings"))
            print("Successfully navigated to job postings page")
        except TimeoutException:
            print("Failed to navigate to job postings page")
            driver.save_screenshot("job_postings_navigation_failed.png")
            self.fail("Navigation to job postings failed")
        
        # 6. Wait for job listings to load
        time.sleep(3)  # Give more time for AJAX to load job listings
        
        # 7. Click on the "View Details" button of the first job
        try:
            view_details_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'View Details')]"))
            )
            # Scroll to the button to make sure it's visible
            driver.execute_script("arguments[0].scrollIntoView(true);", view_details_button)
            time.sleep(1)  # Small pause after scrolling
            
            view_details_button.click()
            print("Clicked on View Details button")
        except TimeoutException:
            print("Could not find or click the View Details button")
            self.fail("View Details button not found or not clickable")
        
        # 8. Wait for the job details page to load
        try:
            self.wait.until(EC.url_contains("/seeker/view_job/"))
            print("Successfully navigated to job details page")
        except TimeoutException:
            print("Failed to navigate to job details page")
            self.fail("Navigation to job details failed")
        
        # 9. Scroll down to the Apply Now button
        try:
            apply_now_button = self.wait.until(
                EC.presence_of_element_located((By.ID, "apply-job"))
            )
            # Scroll to the button
            driver.execute_script("arguments[0].scrollIntoView(true);", apply_now_button)
            time.sleep(1)  # Small pause after scrolling
            
            # 10. Click on the Apply Now button
            apply_now_button.click()
            print("Clicked on Apply Now button")
            
            # Wait for the application to be processed
            time.sleep(2)
            
            # Verify application was successful (check for "Applied" text or similar)
            page_source = driver.page_source
            self.assertTrue("Applied" in page_source or "Cancel Application" in page_source, 
                           "Application confirmation not found on page")
            print("Application was successful")
            
        except TimeoutException:
            print("Could not find or click the Apply Now button")
            self.fail("Apply Now button not found or not clickable")
    
    def tearDown(self):
        # Close the browser
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(verbosity=2) 