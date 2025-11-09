document.addEventListener("DOMContentLoaded", function () {
    const employeeForm = document.getElementById("employeeForm");
    const workHistoryTable = document.querySelector("#workHistoryTable tbody");
    const workHistoryModal = document.getElementById("workHistoryModal");
    const saveDataBtn = document.getElementById("saveDataBtn")

    let currentEmployeeId = null;

    // Save Employee to Flask API
    employeeForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        
        const id = document.getElementById("Id").value;
        const name = document.getElementById("name").value;
        const email = document.getElementById("email").value;
        const phone = document.getElementById("phone").value;
        const address = document.getElementById("address").value;

        const isEditing = id.trim() !== "";
        const apiUrl = isEditing 
            ? "http://localhost:5000/edit_employee" 
            : "http://localhost:5000/add_employee";

        const requestData = isEditing 
            ? { id: id, name, email, phone, address } 
            : { name, email, phone, address };

        const methodType = isEditing ? "PUT" : "POST";
        alert(id);
        const response = await fetch(apiUrl, {
            method: methodType,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();
        if (result.error) {
            alert("Error: " + result.error);
        } else {
            alert(result.message);
            if (!isEditing) {
                currentEmployeeId = result.employee_id; // อัปเดต ID ถ้าเป็นการเพิ่มใหม่
            }
        }
    });

    saveDataBtn.addEventListener("click", async function() {
        const rows = document.querySelectorAll("#workHistoryBody tr");
        const workHistoryData = [];
        const employeeId = document.getElementById("Id").value;
    
        rows.forEach(row => {
            const cells = row.querySelectorAll("input");
            alert('employeeId ' + employeeId);
            const data = {
                id: row.dataset.id || null,
                employee_id: employeeId,
                company: cells[0].value,
                position: cells[1].value,
                startDate: cells[2].value,
                endDate: cells[3].value || null,
            };
            workHistoryData.push(data);
        });
    
        // ส่งข้อมูลไปที่ Flask API
        try {
            const response = await fetch("http://localhost:5000/save_work_history", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ workHistory: workHistoryData })
            });
    
            const result = await response.json();
            alert(result.message);  // แสดงผลการบันทึกข้อมูล
        } catch (error) {
            console.error("Error saving data:", error);
            alert("Error saving data.");
        }
    });
    
    // Fetch Employees from Flask API
    async function fetchEmployees() {
        const response = await fetch("http://localhost:5000/get_employees");
        const employees = await response.json();
        console.log(employees);
    }

    // Fetch Work History from Flask API
    async function fetchWorkHistory() {
        if (!currentEmployeeId) return;
        const response = await fetch(`http://localhost:5000/get_work_history/${currentEmployeeId}`);
        const workHistory = await response.json();
        
        workHistoryTable.innerHTML = "";
        workHistory.forEach(work => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${work.company}</td>
                <td>${work.position}</td>
                <td>${work.start_date}</td>
                <td>${work.end_date}</td>
                <td>
                    <button onclick="deleteWorkHistory(${work.id})">Delete</button>
                </td>
            `;
            workHistoryTable.appendChild(row);
        });
    }
});

document.getElementById("addRowBtn").addEventListener("click", function() {
    const tableBody = document.getElementById("workHistoryBody");
    const newRow = document.createElement("tr");
    // ลบแถวข้อความ "No work history available" ถ้ามี
    const noDataRow = tableBody.querySelector("td[colspan]");
    if (noDataRow) {
        tableBody.removeChild(noDataRow.parentElement);
    }

    newRow.innerHTML = `
        <td><input type="text" name="company" placeholder="Company" required></td>
        <td><input type="text" name="position" placeholder="Position" required></td>
        <td><input type="date" name="startDate" required></td>
        <td><input type="date" name="endDate"></td>
        <td><button class="removeRowBtn">Remove</button></td>
    `;
    tableBody.appendChild(newRow);

    // เพิ่ม event listener สำหรับปุ่ม Remove
    newRow.querySelector(".removeRowBtn").addEventListener("click", function() {
        tableBody.removeChild(newRow);
        // ถ้าไม่มีแถวใดเหลืออยู่ แสดงข้อความ No work history
        if (tableBody.children.length === 0) {
            const noData = document.createElement("tr");
            noData.innerHTML = `<td colspan="5">No work history available</td>`;
            tableBody.appendChild(noData);
        }
    });
});





// Fetch Employee
let currentPage = 1;
const employeePerPage = 10;
let totalEmployees = 0;
let allEmployees = [];

function openModal(employee = null) {
    if (employee) {
        document.getElementById("modalTitle").textContent = "Edit Employee";
        document.getElementById("Id").value = employee.id;
        document.getElementById("name").value = employee.name;
        document.getElementById("email").value = employee.email;
        document.getElementById("phone").value = employee.phone;
        document.getElementById("address").value = employee.address;
        currentEmployeeId = employee.id;
        loadWorkHistory(employee.id);
    } else {
        document.getElementById("modalTitle").textContent = "Add New Employee";
        document.getElementById("Id").value = "";
        document.getElementById("name").value = "";
        document.getElementById("email").value = "";
        document.getElementById("phone").value = "";
        document.getElementById("address").value = "";
        currentEmployeeId = null;
    }
    document.getElementById("employeeModal").style.top = "50%";
    document.getElementById("employeeModal").style.left = "50%";
    document.getElementById("employeeModal").style.transform = "translate(-50%, -50%)";
    document.getElementById("employeeModal").style.display = "flex";
}

function closeModal() {
    document.getElementById("employeeModal").style.display = "none";
}

function fetchEmployee() {
    fetch("/get_employees")
    .then(response => response.json())
    .then(data => {
        allEmployees = data;
        totalEmployees = data.length;
        renderTable();
    })
    .catch(error => alert("Error fetching employees: " + error.message));
}

function renderTable() {
    const tableBody = document.getElementById("employeeTableBody");
    tableBody.innerHTML = ""; // Clear previous data

    const startIndex = (currentPage - 1) * employeePerPage;
    const endIndex = startIndex + employeePerPage;
    const employeeToShow = allEmployees.slice(startIndex, endIndex);

    employeeToShow.forEach(employee => {
        const row = document.createElement("tr");

        // Name column
        const nameCell = document.createElement("td");
        nameCell.textContent = employee.name;

        // Email column
        const emailCell = document.createElement("td");
        emailCell.textContent = employee.email;

        // Actions column
        const actionsCell = document.createElement("td");
        actionsCell.style.textAlign = "center"; // ✅ จัดให้อยู่ตรงกลาง
        actionsCell.style.whiteSpace = "nowrap"; // ✅ ป้องกันการขึ้นบรรทัดใหม่

        // Edit button
        const editBtn = document.createElement("button");
        editBtn.textContent = "Edit";
        editBtn.classList.add("action-btn", "edit-btn");
        editBtn.onclick = function() {
            openModal(employee);
        };

        // Delete button
        const deleteBtn = document.createElement("button");
        deleteBtn.textContent = "Delete";
        deleteBtn.classList.add("action-btn", "delete-btn");
        deleteBtn.onclick = function() {
            deleteUser(employee.id);
        };

        actionsCell.appendChild(editBtn);
        actionsCell.appendChild(document.createTextNode(" "));
        actionsCell.appendChild(deleteBtn);

        // Append cells to row
        row.appendChild(nameCell);
        row.appendChild(emailCell);
        row.appendChild(actionsCell);

        // Append row to table
        tableBody.appendChild(row);
        row.style.height = "2px"; // ปรับความสูงของแถว
    });

    updatePaginationButtons();
}

function updatePaginationButtons() {
    document.getElementById("pageInfo").textContent = `Page ${currentPage} of ${Math.ceil(totalEmployees / employeePerPage)}`;
    document.getElementById("prevPageBtn").disabled = currentPage === 1;
    document.getElementById("nextPageBtn").disabled = currentPage * employeePerPage >= totalEmployees;
}

function changePage(step) {
    currentPage += step;
    renderTable();
}

window.onload = function () {
    fetchEmployee();
};


async function loadWorkHistory(employeeId) {
    try {
        const response = await fetch(`http://localhost:5000/get_work_history/${employeeId}`);
        const data = await response.json();

        const tbody = document.querySelector("#workHistoryTable tbody");
        tbody.innerHTML = ""; // เคลียร์ข้อมูลเก่า

        if (data.length === 0) {
            const row = document.createElement("tr");
            row.innerHTML = `<td colspan="3">No work history available</td>`;
            tbody.appendChild(row);
            return;
        }

        data.forEach(history => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${history.company}</td>
                <td>${history.position}</td>
                <td>${history.start_date}</td>
                <td>${history.end_date}</td>
            `;
            tbody.appendChild(row);
        });
        renderWorkHistory(data);
    } catch (error) {
        console.error("Error loading work history:", error);
    }
}

function renderWorkHistory(data) {
    const tbody = document.getElementById("workHistoryBody");
    tbody.innerHTML = "";

    data.forEach(item => {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td><input type="text" value="${item.company}" /></td>
            <td><input type="text" value="${item.position}" /></td>
            <td><input type="date" value="${item.start_date || ''}" /></td>
            <td><input type="date" value="${item.end_date || ''}" /></td>
            <td><button type="button" class="removeRowBtn">Remove</button></td>
        `;

        // เพิ่ม hidden id ถ้าจะแก้ไข
        row.dataset.id = item.id || "";
        tbody.appendChild(row);

        const removeBtn = row.querySelector(".removeRowBtn");
        removeBtn.addEventListener("click", async () => {
            const workHistoryId = row.dataset.id;

            // ถ้าเป็นแถวใหม่ (ไม่มี id) ให้ลบจากหน้าจออย่างเดียว
            if (!workHistoryId) {
                row.remove();
                checkEmptyWorkHistory(tbody);
                return;
            }

            // Confirm ก่อนลบ
            if (!confirm("Are you sure you want to delete this work history?")) return;

            try {
                const response = await fetch(`http://localhost:5000/delete_work_history/${workHistoryId}`, {
                    method: "DELETE"
                });

                const result = await response.json();

                if (response.ok) {
                    alert(result.message);
                    row.remove();
                    checkEmptyWorkHistory(tbody);
                } else {
                    alert("Failed to delete: " + result.message);
                }
            } catch (error) {
                console.error("Error deleting work history:", error);
                alert("Error deleting work history.");
            }
        });
    });
}

function checkEmptyWorkHistory(tbody) {
    if (tbody.children.length === 0) {
        const emptyRow = document.createElement("tr");
        emptyRow.innerHTML = `<td colspan="5">No work history available</td>`;
        tbody.appendChild(emptyRow);
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const tableHeaders = document.querySelectorAll("#userTable th");

    tableHeaders.forEach((th) => {
        const resizer = th.querySelector(".resize-handle");
        let startX, startWidth;

        if (resizer) {
            resizer.addEventListener("mousedown", (event) => {
                startX = event.pageX;
                startWidth = th.offsetWidth;
                document.addEventListener("mousemove", resizeColumn);
                document.addEventListener("mouseup", stopResizing);
            });

            function resizeColumn(event) {
                const newWidth = startWidth + (event.pageX - startX);
                th.style.width = newWidth + "px";
            }

            function stopResizing() {
                document.removeEventListener("mousemove", resizeColumn);
                document.removeEventListener("mouseup", stopResizing);
            }
        }
    });
});
