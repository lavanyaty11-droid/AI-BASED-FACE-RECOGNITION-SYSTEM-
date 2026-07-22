# AI-BASED-FACE-RECOGNITION-SYSTEM-
An AI-powered attendance system using face recognition (DeepFace, FaceNet, OpenCV, dlib) with a Flask backend, ESP32 hardware authentication, and role-based dashboards for HODs, teachers, and students. Includes Twilio/Gmail notifications, session guards against proxy attendance, and real-time Chart.js analytics for accurate, automated tracking.
**AI-Based Face Recognition Attendance System-**
An AI-powered attendance system using face recognition (DeepFace, FaceNet, OpenCV, dlib) with a Flask backend, ESP32 hardware authentication, and role-based dashboards for HODs, teachers, and students. Includes Twilio/Gmail notifications, session guards against proxy attendance, and real-time Chart.js analytics for accurate, automated tracking.
**Features**
Face recognition-based identification using DeepFace, FaceNet, OpenCV, and dlib
Flask-based web application backend
ESP32 hardware integration for authentication at entry points
Automated Twilio SMS and Gmail notifications to parents/students
HOD approval workflows and teacher session controls
Role-based dashboard access for HOD, Teacher, and Student roles
Real-time analytics and visualizations using Chart.js
Session guards to prevent unauthorized or unknown persons from being marked present
**Technical Highlights**
Switched from Euclidean to cosine distance metrics for improved recognition accuracy
Tuned recognition threshold to reduce false positives/negatives
Self-contained single-file HTML frontend with a dark dashboard aesthetic
**Tech Stack**
Python, Flask, DeepFace, FaceNet, OpenCV, dlib, ESP32, Twilio API, Chart.js, HTML/CSS/JS
**Known Limitations**
Accuracy can drop under poor lighting conditions
Performance tested on a relatively small dataset
Some latency during real-time recognition
**Usage**
Register students/faces through the admin dashboard
Configure ESP32 device for entry-point authentication
Teachers start a session; attendance is marked automatically via face recognition
HODs can review and approve attendance logs
Notifications are sent automatically via Twilio SMS / Gmail
