document.addEventListener("DOMContentLoaded", function () {
  initDragAndDrop();
});

function initDragAndDrop() {
  const components = document.querySelectorAll(".component-item");
  const dropZone = document.getElementById("resume-drop-zone");
  const emptyMessage = document.getElementById("empty-message");

  components.forEach((component) => {
    component.addEventListener("dragstart", handleDragStart);
    component.addEventListener("dragend", handleDragEnd);
  });

  dropZone.addEventListener("dragover", handleDragOver);
  dropZone.addEventListener("dragleave", handleDragLeave);
  dropZone.addEventListener("drop", handleDrop);

  // Enable sorting of added sections
  new Sortable(dropZone, {
    animation: 150,
    handle: ".section-handle",
    ghostClass: "dragging",
  });
}

function handleDragStart(e) {
  e.dataTransfer.setData("text/plain", e.target.dataset.type);
  e.target.classList.add("dragging");
}

function handleDragEnd(e) {
  e.target.classList.remove("dragging");
}

function handleDragOver(e) {
  e.preventDefault();
  e.currentTarget.classList.add("drag-over");
}

function handleDragLeave(e) {
  e.currentTarget.classList.remove("drag-over");
}

function handleDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.remove("drag-over");

  const sectionType = e.dataTransfer.getData("text/plain");
  addSection(sectionType);

  // Hide empty message if there are sections
  document.getElementById("empty-message").style.display =
    document.querySelectorAll(".resume-section").length > 0 ? "none" : "block";
}

function addSection(type) {
  const section = createSectionElement(type);
  document.getElementById("resume-drop-zone").appendChild(section);
}

function createSectionElement(type) {
  const section = document.createElement("div");
  section.className = "resume-section";
  section.innerHTML = `
          <div class="section-handle">
              <i class="fas fa-grip-lines"></i>
          </div>
          <div class="section-actions">
              <button class="btn btn-sm btn-outline-primary" onclick="editSection(this)">
                  <i class="fas fa-edit"></i>
              </button>
              <button class="btn btn-sm btn-outline-danger" onclick="removeSection(this)">
                  <i class="fas fa-trash"></i>
              </button>
          </div>
          ${getSectionTemplate(type)}
      `;
  return section;
}

function getSectionTemplate(type) {
  const templates = {
    header: `
              <h4>Personal Information</h4>
              <div class="row">
                  <div class="col-md-6 mb-3">
                      <input type="text" class="form-control" placeholder="Full Name">
                  </div>
                  <div class="col-md-6 mb-3">
                      <input type="text" class="form-control" placeholder="Professional Title">
                  </div>
                  <div class="col-md-6 mb-3">
                      <input type="email" class="form-control" placeholder="Email">
                  </div>
                  <div class="col-md-6 mb-3">
                      <input type="tel" class="form-control" placeholder="Phone">
                  </div>
              </div>
          `,
    experience: `
              <h4>Work Experience</h4>
              <div class="work-entry mb-3">
                  <input type="text" class="form-control mb-2" placeholder="Company Name">
                  <input type="text" class="form-control mb-2" placeholder="Position">
                  <div class="row mb-2">
                      <div class="col-md-6">
                          <input type="month" class="form-control" placeholder="Start Date">
                      </div>
                      <div class="col-md-6">
                          <input type="month" class="form-control" placeholder="End Date">
                      </div>
                  </div>
                  <textarea class="form-control" rows="3" placeholder="Description of responsibilities and achievements"></textarea>
              </div>
              <button class="btn btn-sm btn-outline-secondary" onclick="addWorkEntry(this)">
                  <i class="fas fa-plus"></i> Add Another Position
              </button>
          `,
    summary: `
              <h4>Professional Summary</h4>
              <div class="form-group">
                  <textarea class="form-control" rows="4" placeholder="Write a compelling summary of your professional background and career goals"></textarea>
              </div>
          `,
    education: `
              <h4>Education</h4>
              <div class="education-entry mb-3">
                  <input type="text" class="form-control mb-2" placeholder="Degree/Certificate">
                  <input type="text" class="form-control mb-2" placeholder="Institution">
                  <div class="row mb-2">
                      <div class="col-md-6">
                          <input type="month" class="form-control" placeholder="Start Date">
                      </div>
                      <div class="col-md-6">
                          <input type="month" class="form-control" placeholder="End Date">
                      </div>
                  </div>
                  <textarea class="form-control" rows="2" placeholder="Description or achievements"></textarea>
              </div>
          `,
    skills: `
              <h4>Skills</h4>
              <div class="form-group">
                  <input type="text" class="form-control mb-2" placeholder="Skill Category (e.g., Technical Skills)">
                  <textarea class="form-control" rows="2" placeholder="List your skills, separated by commas"></textarea>
              </div>
          `,
    projects: `
              <h4>Projects</h4>
              <div class="project-entry mb-3">
                  <input type="text" class="form-control mb-2" placeholder="Project Name">
                  <input type="text" class="form-control mb-2" placeholder="Role/Position">
                  <div class="row mb-2">
                      <div class="col-md-6">
                          <input type="month" class="form-control" placeholder="Start Date">
                      </div>
                      <div class="col-md-6">
                          <input type="month" class="form-control" placeholder="End Date">
                      </div>
                  </div>
                  <textarea class="form-control" rows="3" placeholder="Project description and achievements"></textarea>
              </div>
          `,
    certifications: `
              <h4>Certifications</h4>
              <div class="certification-entry mb-3">
                  <input type="text" class="form-control mb-2" placeholder="Certification Name">
                  <input type="text" class="form-control mb-2" placeholder="Issuing Organization">
                  <div class="row mb-2">
                      <div class="col-md-6">
                          <input type="month" class="form-control" placeholder="Issue Date">
                      </div>
                      <div class="col-md-6">
                          <input type="month" class="form-control" placeholder="Expiry Date (if applicable)">
                      </div>
                  </div>
                  <input type="text" class="form-control" placeholder="Credential ID (optional)">
              </div>
          `,
  };
  return (
    templates[type] ||
    `<h4>${type.charAt(0).toUpperCase() + type.slice(1)}</h4>`
  );
}

function removeSection(button) {
  const section = button.closest(".resume-section");
  section.remove();

  // Show empty message if no sections remain
  document.getElementById("empty-message").style.display =
    document.querySelectorAll(".resume-section").length > 0 ? "none" : "block";
}

function editSection(button) {
  // Implement edit functionality
  const section = button.closest(".resume-section");
  // Add your edit logic here
}

function addWorkEntry(button) {
  const template = `
          <div class="work-entry mb-3">
              <input type="text" class="form-control mb-2" placeholder="Company Name">
              <input type="text" class="form-control mb-2" placeholder="Position">
              <div class="row mb-2">
                  <div class="col-md-6">
                      <input type="month" class="form-control" placeholder="Start Date">
                  </div>
                  <div class="col-md-6">
                      <input type="month" class="form-control" placeholder="End Date">
                  </div>
              </div>
              <textarea class="form-control" rows="3" placeholder="Description of responsibilities and achievements"></textarea>
          </div>
      `;
  const container = button.previousElementSibling;
  container.insertAdjacentHTML("beforeend", template);
}

function saveResume() {
  const resumeData = {
    sections: Array.from(document.querySelectorAll(".resume-section")).map(
      (section) => {
        return {
          type: section.querySelector("h4").textContent,
          content: section.innerHTML,
        };
      }
    ),
  };

  fetch("/seeker/save-resume", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(resumeData),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        alert("Resume saved successfully!");
      } else {
        alert("Error saving resume: " + data.message);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error saving resume");
    });
}

function exportResume() {
  // Implement PDF export functionality
  alert("Export functionality will be implemented here");
}
