// Get signup data
const student = JSON.parse(
    localStorage.getItem("student")
);


// Get student data
const studentData = JSON.parse(
    localStorage.getItem("studentData")
);


// Check data
if (!student || !studentData) {

    alert("Please complete your student information first.");

    window.location.href = "student-data.html";

}


// Convert values
const cgpa = Number(studentData.cgpa);
const attendance = Number(studentData.attendance);
const dsa = Number(studentData.dsa);
const projects = Number(studentData.projects);


// Display student name
document.getElementById("studentName").textContent =
    student.name;


// Display statistics
document.getElementById("cgpa").textContent =
    cgpa;

document.getElementById("attendance").textContent =
    attendance + "%";

document.getElementById("dsa").textContent =
    dsa + "%";

document.getElementById("projects").textContent =
    projects;


// Convert CGPA into percentage for chart
const cgpaPercentage = (cgpa / 10) * 100;


// Calculate technical skill score
const skills = studentData.skills;

const skillPercentage =
    Math.min(skills.length, 5) / 5 * 100;


// Set bar widths
document.getElementById("cgpaBar").style.width =
    cgpaPercentage + "%";

document.getElementById("attendanceBar").style.width =
    attendance + "%";

document.getElementById("dsaBar").style.width =
    dsa + "%";

document.getElementById("skillsBar").style.width =
    skillPercentage + "%";


// Display skills
const skillsContainer =
    document.getElementById("skills");

skillsContainer.innerHTML = "";


skills.forEach(function(skill) {

    const skillElement =
        document.createElement("span");

    skillElement.className = "skill";

    skillElement.textContent = skill;

    skillsContainer.appendChild(skillElement);

});