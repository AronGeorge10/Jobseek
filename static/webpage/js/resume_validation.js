// Validation helper functions
function showError(inputElement, message) {
  const formControl =
    inputElement.closest(".col-md-6") ||
    inputElement.closest(".col-md-5") ||
    inputElement.closest(".col-md-7");
  const existingError = formControl.querySelector(".error-message");

  if (!existingError) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "error-message text-danger small mt-1";
    errorDiv.textContent = message;
    formControl.appendChild(errorDiv);
  }
  inputElement.classList.add("is-invalid");
}

function clearError(inputElement) {
  const formControl =
    inputElement.closest(".col-md-6") ||
    inputElement.closest(".col-md-5") ||
    inputElement.closest(".col-md-7");
  const errorDiv = formControl.querySelector(".error-message");
  if (errorDiv) {
    errorDiv.remove();
  }
  inputElement.classList.remove("is-invalid");
}

// Section-specific validation functions
function validatePersonalInfo() {
  const section = document.getElementById("section-1");
  let isValid = true;

  // Full Name validation
  const fullNameCol = section.querySelector(
    ".row:first-child .col-md-6:first-child"
  );
  const fullName = fullNameCol.querySelector("input");
  if (!fullName.value.trim()) {
    showError(fullName, "Full name is required");
    isValid = false;
  } else if (!/^[a-zA-Z\s]{2,50}$/.test(fullName.value.trim())) {
    showError(
      fullName,
      "Please enter a valid name (2-50 characters, letters only)"
    );
    isValid = false;
  } else {
    clearError(fullName);
  }

  // Email validation
  const emailCol = section.querySelector(
    ".row:first-child .col-md-6:last-child"
  );
  const email = emailCol.querySelector("input");
  if (!email.value.trim()) {
    showError(email, "Email is required");
    isValid = false;
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) {
    showError(email, "Please enter a valid email address");
    isValid = false;
  } else {
    clearError(email);
  }

  // Position validation
  const positionCol = section.querySelector(
    ".row:nth-child(2) .col-md-6:first-child"
  );
  const position = positionCol.querySelector("input");
  if (!position.value.trim()) {
    showError(position, "Position is required");
    isValid = false;
  } else {
    clearError(position);
  }

  // LinkedIn URL validation
  const linkedinCol = section.querySelector(
    ".row:nth-child(2) .col-md-6:last-child"
  );
  const linkedin = linkedinCol.querySelector("input");
  if (
    linkedin.value.trim() &&
    !linkedin.value.trim().startsWith("https://www.linkedin.com/")
  ) {
    showError(linkedin, "Please enter a valid LinkedIn URL");
    isValid = false;
  } else {
    clearError(linkedin);
  }

  // Address validation
  const addressCol = section.querySelector(".row:nth-child(3) .col-md-7");
  const address = addressCol.querySelector("input");
  if (!address.value.trim()) {
    showError(address, "Address is required");
    isValid = false;
  } else {
    clearError(address);
  }

  // Phone validation
  const phoneCol = section.querySelector(".row:nth-child(3) .col-md-5");
  const phone = phoneCol.querySelector("input");
  if (!phoneInput.isValidNumber()) {
    showError(phone, "Please enter a valid phone number");
    isValid = false;
  } else {
    clearError(phone);
  }

  return isValid;
}

function validateProfessionalSummary() {
  const summary = document.querySelector("#section-2 textarea");
  let isValid = true;

  if (!summary.value.trim()) {
    showError(summary, "Professional summary is required");
    isValid = false;
  } else if (summary.value.trim().length < 100) {
    showError(
      summary,
      "Professional summary should be at least 100 characters"
    );
    isValid = false;
  } else {
    clearError(summary);
  }

  return isValid;
}

function validateEducation() {
  const educationEntries = document.querySelectorAll(".education-entry");
  let isValid = true;

  if (educationEntries.length === 0) {
    return false;
  }

  educationEntries.forEach((entry) => {
    const degree = entry.querySelector('input[type="text"]:first-of-type');
    const institution = entry.querySelector(
      '.col-md-6:nth-child(2) input[type="text"]'
    );
    const startDate = entry.querySelector('input[type="month"]:first-of-type');
    const endDate = entry.querySelector('input[type="month"]:last-of-type');

    if (!degree.value.trim()) {
      showError(degree, "Degree is required");
      isValid = false;
    } else {
      clearError(degree);
    }

    if (!institution.value.trim()) {
      showError(institution, "Institution is required");
      isValid = false;
    } else {
      clearError(institution);
    }

    if (!startDate.value) {
      showError(startDate, "Start date is required");
      isValid = false;
    } else {
      clearError(startDate);
    }

    // End date validation (if provided, should be after start date)
    if (endDate.value && startDate.value && endDate.value < startDate.value) {
      showError(endDate, "End date must be after start date");
      isValid = false;
    } else {
      clearError(endDate);
    }
  });

  return isValid;
}

function validateSkills() {
  const technicalSkills = document.getElementById("technical_skills");
  const softSkills = document.getElementById("soft_skills");
  let isValid = true;

  // At least one type of skill is required
  if (!technicalSkills.value.trim() && !softSkills.value.trim()) {
    showError(technicalSkills, "At least one type of skill is required");
    isValid = false;
  } else {
    clearError(technicalSkills);
  }

  return isValid;
}

// Main validation function
function validateSection(sectionNumber) {
  switch (sectionNumber) {
    case 1:
      return validatePersonalInfo();
    case 2:
      return validateProfessionalSummary();
    case 3:
      return validateEducation();
    case 4:
      return validateSkills();
    // Add more section validations as needed
    default:
      return true;
  }
}

// Event listeners for real-time validation
document.addEventListener("DOMContentLoaded", function () {
  // Add phone number input restrictions
  const phoneInput = document.getElementById("phone");
  if (phoneInput) {
    phoneInput.addEventListener("keypress", function (e) {
      // Allow only numbers and specific control keys
      if (
        e.key !== "Backspace" &&
        e.key !== "Delete" &&
        e.key !== "Tab" &&
        e.key !== "ArrowLeft" &&
        e.key !== "ArrowRight"
      ) {
        if (!/^\d$/.test(e.key)) {
          e.preventDefault();
        }
      }
    });

    // Prevent paste of non-numeric characters
    phoneInput.addEventListener("paste", function (e) {
      const pastedText = (e.clipboardData || window.clipboardData).getData(
        "text"
      );
      if (!/^\d+$/.test(pastedText)) {
        e.preventDefault();
      }
    });
  }

  // Add input event listeners for real-time validation
  const inputs = document.querySelectorAll("input, textarea, select");
  inputs.forEach((input) => {
    input.addEventListener("input", function () {
      const section = this.closest(".resume-section");
      if (section) {
        const sectionNumber = parseInt(section.id.split("-")[1]);

        // For section 1 (Personal Information), validate only the changed field
        if (sectionNumber === 1) {
          const fieldType = this.getAttribute("type");
          const parentCol = this.closest(".col-md-6, .col-md-5, .col-md-7");

          if (
            this ===
            document.querySelector(
              "#section-1 .row:first-child .col-md-6:first-child input"
            )
          ) {
            // Full Name validation
            if (!this.value.trim()) {
              showError(this, "Full name is required");
            } else if (!/^[a-zA-Z\s]{2,50}$/.test(this.value.trim())) {
              showError(
                this,
                "Please enter a valid name (2-50 characters, letters only)"
              );
            } else {
              clearError(this);
            }
          } else if (
            this ===
            document.querySelector(
              "#section-1 .row:first-child .col-md-6:last-child input"
            )
          ) {
            // Email validation
            if (!this.value.trim()) {
              showError(this, "Email is required");
            } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.value.trim())) {
              showError(this, "Please enter a valid email address");
            } else {
              clearError(this);
            }
          } else if (
            this ===
            document.querySelector(
              "#section-1 .row:nth-child(2) .col-md-6:first-child input"
            )
          ) {
            // Position validation
            if (!this.value.trim()) {
              showError(this, "Position is required");
            } else {
              clearError(this);
            }
          } else if (
            this ===
            document.querySelector(
              "#section-1 .row:nth-child(2) .col-md-6:last-child input"
            )
          ) {
            // LinkedIn validation
            if (
              this.value.trim() &&
              !this.value.trim().startsWith("https://www.linkedin.com/")
            ) {
              showError(this, "Please enter a valid LinkedIn URL");
            } else {
              clearError(this);
            }
          } else if (
            this ===
            document.querySelector(
              "#section-1 .row:nth-child(3) .col-md-7 input"
            )
          ) {
            // Address validation
            if (!this.value.trim()) {
              showError(this, "Address is required");
            } else {
              clearError(this);
            }
          } else if (this.id === "phone") {
            // Updated phone validation
            if (!this.value.trim()) {
              showError(this, "Phone number is required");
            } else if (!phoneInput.isValidNumber()) {
              showError(this, "Please enter a valid phone number");
            } else {
              clearError(this);
            }
          }
        } else {
          // For other sections, continue with the existing validation
          validateSection(sectionNumber);
        }
      }
    });
  });

  // Modify the nextSection function to include validation
  const originalNextSection = window.nextSection;
  window.nextSection = function () {
    if (validateSection(currentSection)) {
      originalNextSection();
    } else {
      // Show error toast
      const toastMessage = document.getElementById("toastMessage");
      toastMessage.textContent = "Please fill in all required fields correctly";
      toastMessage.parentElement.classList.remove("bg-success");
      toastMessage.parentElement.classList.add("bg-danger", "text-white");
      const saveToast = new bootstrap.Toast(
        document.getElementById("saveToast")
      );
      saveToast.show();
    }
  };
});
