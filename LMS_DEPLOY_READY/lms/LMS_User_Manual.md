# Learning Management System (LMS) - User Manual

Welcome to the official LMS documentation. This guide is designed to help management, staff, and students navigate the system efficiently.

---

## 1. Role-Based Overview

The LMS uses a robust role-based access control system to ensure every user has exactly what they need for their specific tasks.

### 🔍 Super Admin (Full Control)

* **Purpose**: Strategic oversight and system configuration.
* **Key Capabilities**:
  * **User Management**: Create and manage Admins, Lecturers, and Students.
  * **Advanced Configuration**: Access to technical settings and full system logs via the Django Admin interface.
  * **Audit**: View all student performance, payment records, and assignment metrics across the entire institution.
  * **Global Security**: Can approve or reject any password reset request or enrollment change.

### ⚙️ Admin (Operations Management)

* **Purpose**: Day-to-day coordination of student and course data.
* **Key Capabilities**:
  * **Enrollment Control**: Add students to specific cohorts and ensure they have the correct course assignments.
  * **Payment Verification**: Monitor the "Action Center" for blinking amber dots indicating pending fee payments. Verify and approve receipts.
  * **Security Governance**: Review and approve "Password Reset Requests" submitted by users.
  * **Cohort Management**: Create new cohorts, set start/end dates, and assign lecturers to them.

### 🎓 Lecturer (Academic Oversight)

* **Purpose**: Teaching, mentoring, and assessment.
* **Key Capabilities**:
  * **Assignments**: Create assignments with specific deadlines, total marks, and passmark percentages.
  * **Evaluation Queue**: Access the "Submissions Queue" on the dashboard to see student work waiting to be marked.
  * **Grading & Feedback**: Download student files (Packet Tracer, PDF, JPG) and provide numeric marks and detailed text feedback.
  * **Performance Tracking**: Monitor the progress of students within assigned cohorts.

### 👤 Student (Learning & Progress)

* **Purpose**: Study, submission, and self-tracking.
* **Key Capabilities**:
  * **Study Dashboard**: View overall average marks, academic status (PASS/FAIL), and active timelines.
  * **Work Submission**: Upload multiple files per assignment. The system captures the original filename (e.g., `lab1_final.pkt`) for lecturer clarity.
  * **Academic History**: View graded work, read instructor feedback, and track performance over time.
  * **Documents**: Download Official Transcripts and Certificates once a cohort period has concluded.

---

## 2. Key System Features & Workflows

### 🔔 Smart Notifications (Action Center)

* The system uses **Pulse Dot** technology. If you see a **blinking amber dot** next to a section (like "Grades" or "Payments"), it means there is an item waiting for your immediate action.
* This keeps the dashboard clean and ensures nothing is overlooked.

### 🔐 Secure Password Reset

1. **Request**: Any user can go to the login page and click "Request Password Reset."
2. **Input**: The user must provide their **Username**, **Current Password**, and the **New Password** they wish to use.
3. **Submission**: The system verifies the current password immediately for security.
4. **Admin Approval**: The request appears in the Admin's "Security" dashboard with a blinking alert. An Admin reviews the request and clicks **Approve** to finalize the change.

### 📂 Assignment Workflow

1. **Lecturer** creates an assignment for a cohort.
2. **Student** sees the assignment on their dashboard and uploads their work.
3. **Lecturer** receives a blinking alert, reviews the original files, and assigns a grade.
4. **Admin** (optional) oversees the final approval of grades to ensure consistency.

---

## 3. Best Practices for Users

* **Browser**: For the best experience, use Google Chrome or Microsoft Edge. If you don't see a change you expected, perform a "Hard Refresh" (**Ctrl + F5**).
* **Files**: When uploading work, ensure your filenames are descriptive (e.g., `Name_Subject_Assignment.pdf`).
* **Security**: Never share your login credentials. Use the request reset feature if you feel your account is compromised.
