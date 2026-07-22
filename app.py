from flask import Flask, render_template, request, redirect, session
import os, json, csv, cv2, pyttsx3, smtplib
from deepface import DeepFace
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from flask import send_file
app = Flask(__name__)
app.secret_key = "smart_attendance_secret"

HOD_FILE = "hod.json"
TEACHERS_FILE = "teachers.json"
STUDENTS_FILE = "students.json"
SESSION_FILE = "session.json"
ATTENDANCE_FILE = "attendance.csv"
CONTROL_FILE = "control.txt"
DATASET = "dataset"

SENDER_EMAIL    = "xxxxxxxxxxxxxxx"
SENDER_PASSWORD = "xxxxxxxxxxx"

TWILIO_SID   = "Your_twilio_account_sid"
TWILIO_TOKEN = "Your_twilio_auth_token"
TWILIO_PHONE = "+1xxxxxxxxxx"
COURSES = [
    "Data Mining",
    "Data Mining Lab",
    "Internet Technology",
    "Internet Technology Lab",
    "Project"
]

CLASS_HOURS = ["1 Hour", "2 Hours", "3 Hours"]

os.makedirs(DATASET, exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


def load_json(file):
    try:
        if not os.path.exists(file) or os.path.getsize(file) == 0:
            return {}
        with open(file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        if file == HOD_FILE:
            data = {"username": "", "password": ""}
        elif file == SESSION_FILE:
            data = {
                "active": False,
                "course": "",
                "class_hour": "",
                "esp32_verified": False,
                "class_no": 0
            }
        else:
            data = {}
        save_json(file, data)
        return data


def create_files():
    if not os.path.exists(HOD_FILE):
        save_json(HOD_FILE, {"username": "", "password": ""})

    if not os.path.exists(TEACHERS_FILE):
        save_json(TEACHERS_FILE, {})

    if not os.path.exists(STUDENTS_FILE):
        save_json(STUDENTS_FILE, {})

    if not os.path.exists(SESSION_FILE):
        save_json(SESSION_FILE, {
            "active": False,
            "course": "",
            "class_hour": "",
            "esp32_verified": False,
            "class_no": 0
        })

    if not os.path.exists(CONTROL_FILE):
        with open(CONTROL_FILE, "w") as f:
            f.write("OFF")

    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Class_No", "Student_ID", "Name", "Course",
                "Class_Hour", "Date", "Time", "Status"
            ])


create_files()


def valid_password(password):
    return len(password) >= 6


def phone_exists(phone):
    students = load_json(STUDENTS_FILE)
    for data in students.values():
        if data["student_phone"] == phone or data["parent_phone"] == phone:
            return True
    return False


def email_exists(email):
    students = load_json(STUDENTS_FILE)
    for data in students.values():
        if data["student_email"] == email or data["parent_email"] == email:
            return True
    return False


def speak(text):
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("Voice Error:", e)


def send_email(to_email, subject, message):
    try:
        if SENDER_EMAIL == "your_email@gmail.com":
            print("Email not sent. Add real Gmail App Password.")
            return

        mail = MIMEMultipart()
        mail["From"] = SENDER_EMAIL
        mail["To"] = to_email
        mail["Subject"] = subject
        mail.attach(MIMEText(message, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(mail)
        server.quit()

    except Exception as e:
        print("Email Error:", e)


def send_sms(to_phone, message):
    try:
        if TWILIO_SID == "your_twilio_sid":
            print("SMS not sent. Add real Twilio settings.")
            return

        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(body=message, from_=TWILIO_PHONE, to=to_phone)

    except Exception as e:
        print("SMS Error:", e)


def send_notification(student_id, name, course, class_hour, date, time_now, status, class_no):
    students = load_json(STUDENTS_FILE)
    student = students[student_id]

    subject = f"Attendance Marked - {status}"

    student_message = f"""
Hello {name},

Your attendance has been marked {status}.

Class No: {class_no}
Student ID: {student_id}
Course: {course}
Class Hour: {class_hour}
Date: {date}
Time: {time_now}

AI Smart Attendance System
"""

    parent_message = f"""
Hello Parent,

Your child {name}'s attendance has been marked {status}.

Class No: {class_no}
Student ID: {student_id}
Course: {course}
Class Hour: {class_hour}
Date: {date}
Time: {time_now}

AI Smart Attendance System
"""

    send_email(student["student_email"], subject, student_message)
    send_email(student["parent_email"], subject, parent_message)
    send_sms(student["student_phone"], student_message)
    send_sms(student["parent_phone"], parent_message)


def get_next_class_no(course):
    max_class = 0

    if not os.path.exists(ATTENDANCE_FILE):
        return 1

    with open(ATTENDANCE_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Course"] == course:
                try:
                    max_class = max(max_class, int(row["Class_No"]))
                except:
                    pass

    return max_class + 1


def mark_all_students_absent(class_no, course, class_hour):
    students = load_json(STUDENTS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M:%S")

    existing = []

    if os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.append(row)

    with open(ATTENDANCE_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        for sid, student in students.items():
            already = False

            for row in existing:
                if row["Class_No"] == str(class_no) and row["Student_ID"] == sid and row["Course"] == course:
                    already = True
                    break

            if not already:
                writer.writerow([
                    class_no,
                    sid,
                    student["full_name"],
                    course,
                    class_hour,
                    today,
                    time_now,
                    "Absent"
                ])


def update_attendance_present(student_id, course, class_no):
    rows = []
    found = False
    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M:%S")

    with open(ATTENDANCE_FILE, "r") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            if (
                row["Student_ID"] == student_id
                and row["Course"] == course
                and row["Class_No"] == str(class_no)
            ):
                row["Status"] = "Present"
                row["Date"] = today
                row["Time"] = time_now
                found = True

            rows.append(row)

    with open(ATTENDANCE_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return found


@app.route("/")
def home():
    hod = load_json(HOD_FILE)

    if hod.get("username", "") == "" or hod.get("password", "") == "":
        return redirect("/hod_register")

    return redirect("/hod_login")


# ================= HOD MODULE =================

@app.route("/hod_register", methods=["GET", "POST"])
def hod_register():
    hod = load_json(HOD_FILE)

    if hod.get("username", "") != "" and hod.get("password", "") != "":
        return redirect("/hod_login")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not valid_password(password):
            return "Password must be minimum 6 characters"

        save_json(HOD_FILE, {
            "username": username,
            "password": password
        })

        return redirect("/hod_login")

    return render_template("hod_register.html")


@app.route("/hod_login", methods=["GET", "POST"])
def hod_login():
    hod = load_json(HOD_FILE)

    if hod.get("username", "") == "" or hod.get("password", "") == "":
        return redirect("/hod_register")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == hod["username"] and password == hod["password"]:
            session["hod"] = username
            return redirect("/hod_dashboard")

        return "Invalid HOD Login"

    return render_template("hod_login.html")


@app.route("/hod_dashboard")
def hod_dashboard():
    if "hod" not in session:
        return redirect("/hod_login")

    records = []

    if os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)

    return render_template(
        "hod_dashboard.html",
        teachers=load_json(TEACHERS_FILE),
        students=load_json(STUDENTS_FILE),
        courses=COURSES,
        records=records
    )


@app.route("/approve_teacher/<username>/<course>")
def approve_teacher(username, course):

    if "hod" not in session:
        return redirect("/hod_login")

    teachers = load_json(TEACHERS_FILE)

    if username in teachers:
        teachers[username]["approved"] = True

        if "courses" not in teachers[username]:
            teachers[username]["courses"] = []

        if course not in teachers[username]["courses"]:
            teachers[username]["courses"].append(course)

        if "course" in teachers[username]:
            del teachers[username]["course"]

        save_json(TEACHERS_FILE, teachers)

    return redirect("/hod_dashboard")

@app.route("/reject_teacher/<username>")
def reject_teacher(username):

    if "hod" not in session:
        return redirect("/hod_login")

    teachers = load_json(TEACHERS_FILE)

    if username in teachers:

        teachers[username]["approved"] = False
        teachers[username]["courses"] = []

        if "course" in teachers[username]:
            del teachers[username]["course"]

        save_json(TEACHERS_FILE, teachers)

    return redirect("/hod_dashboard")
# ================= TEACHER MODULE =================

@app.route("/teacher_register", methods=["GET", "POST"])
def teacher_register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        username = request.form["username"]
        password = request.form["password"]
        teacher_code = request.form["teacher_code"]

        teachers = load_json(TEACHERS_FILE)

        if not valid_password(password):
            return "Password must be minimum 6 characters"

        if username in teachers:
            return "Teacher username already exists"

        for t in teachers.values():
            if t.get("teacher_code") == teacher_code:
                return "Teacher code already exists"

        teachers[username] = {
            "full_name": full_name,
            "password": password,
            "teacher_code": teacher_code,
            "approved": False,
            "courses": []
        }

        save_json(TEACHERS_FILE, teachers)
        return redirect("/teacher_login")

    return render_template("teacher_register.html")


@app.route("/teacher_login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        teachers = load_json(TEACHERS_FILE)

        if username in teachers and teachers[username]["password"] == password:
            if not teachers[username].get("approved", False):
                return "Teacher not approved by HOD yet"

            session["teacher"] = username
            return redirect("/teacher_dashboard")

        return "Invalid Teacher Login"

    return render_template("teacher_login.html")


@app.route("/teacher_dashboard")
def teacher_dashboard():
    if "teacher" not in session:
        return redirect("/teacher_login")

    teachers = load_json(TEACHERS_FILE)
    teacher = teachers[session["teacher"]]

    records = []

    if os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Course"] in teacher.get("courses",[]):
                    records.append(row)

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        courses=teacher.get("courses",[]),
        class_hours=CLASS_HOURS,
        session_data=load_json(SESSION_FILE),
        students=load_json(STUDENTS_FILE),
        records=records
    )


@app.route("/create_session", methods=["POST"])
def create_session():
    if "teacher" not in session:
        return redirect("/teacher_login")

    teachers = load_json(TEACHERS_FILE)
    teacher = teachers[session["teacher"]]

    course = request.form["course"]
    class_hour = request.form["class_hour"]

    if course not in teacher.get("courses",[]):
        return "You are not approved for this course"

    class_no = get_next_class_no(course)

    data = {
        "active": True,
        "course": course,
        "class_hour": class_hour,
        "esp32_verified": False,
        "class_no": class_no
    }

    save_json(SESSION_FILE, data)

    with open(CONTROL_FILE, "w") as f:
        f.write("ON")

    mark_all_students_absent(class_no, course, class_hour)

    return redirect("/teacher_dashboard")


@app.route("/stop_session")
def stop_session():

    if "teacher" not in session:
        return redirect("/teacher_login")

    session_data = load_json(SESSION_FILE)

    class_no = session_data.get("class_no")
    course = session_data.get("course")
    class_hour = session_data.get("class_hour")

    students = load_json(STUDENTS_FILE)

    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M:%S")

    # ================= SEND ABSENT NOTIFICATIONS =================

    if os.path.exists(ATTENDANCE_FILE):

        with open(ATTENDANCE_FILE, "r") as f:

            reader = csv.DictReader(f)

            for row in reader:

                if (
                    row["Class_No"] == str(class_no)
                    and row["Course"] == course
                    and row["Status"] == "Absent"
                ):

                    sid = row["Student_ID"]

                    if sid in students:

                        send_notification(
                            sid,
                            students[sid]["full_name"],
                            course,
                            class_hour,
                            today,
                            time_now,
                            "Absent",
                            class_no
                        )

    # ================= STOP SESSION =================

    save_json(SESSION_FILE, {
        "active": False,
        "course": "",
        "class_hour": "",
        "esp32_verified": False,
        "class_no": 0
    })

    with open(CONTROL_FILE, "w") as f:
        f.write("OFF")

    return redirect("/teacher_dashboard")


# ================= ESP32 =================

@app.route("/esp32_auth")
def esp32_auth():
    data = load_json(SESSION_FILE)

    if not data.get("active"):
        return "No active session"

    data["esp32_verified"] = True
    save_json(SESSION_FILE, data)

    return redirect("/teacher_dashboard")


@app.route("/esp32_status")
def esp32_status():
    with open(CONTROL_FILE, "r") as f:
        return f.read()


# ================= STUDENT MODULE =================

@app.route("/student_register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":
        student_id = request.form["student_id"]
        full_name = request.form["full_name"]
        password = request.form["password"]
        student_phone = request.form["student_phone"]
        student_email = request.form["student_email"]
        parent_phone = request.form["parent_phone"]
        parent_email = request.form["parent_email"]

        students = load_json(STUDENTS_FILE)

        if not valid_password(password):
            return "Password must be minimum 6 characters"

        if student_id in students:
            return "Student ID already exists"

        if phone_exists(student_phone) or phone_exists(parent_phone):
            return "Phone number already used"

        if email_exists(student_email) or email_exists(parent_email):
            return "Email already used"

        students[student_id] = {
            "full_name": full_name,
            "password": password,
            "student_phone": student_phone,
            "student_email": student_email,
            "parent_phone": parent_phone,
            "parent_email": parent_email
        }

        save_json(STUDENTS_FILE, students)
        os.makedirs(os.path.join(DATASET, student_id), exist_ok=True)

        return redirect(f"/capture_faces/{student_id}")

    return render_template("student_register.html")


@app.route("/capture_faces/<student_id>")
def capture_faces(student_id):
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    count = 0
    student_folder = os.path.join(DATASET, student_id)
    os.makedirs(student_folder, exist_ok=True)

    while count < 5:
        ret, frame = cam.read()

        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = detector.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            if count >= 5:
                break

            count += 1
            face = frame[y:y + h, x:x + w]

            cv2.imwrite(os.path.join(student_folder, f"{count}.jpg"), face)

            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            cv2.putText(
                frame,
                f"Captured {count}/5",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        display_frame = cv2.resize(frame, (1100, 700))
        cv2.imshow("Capturing 5 Faces", display_frame)

        if cv2.waitKey(1000) == 13:
            break

    cam.release()
    cv2.destroyAllWindows()

    return "5 Face Images Captured Successfully. <a href='/student_login'>Student Login</a>"


@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        student_id = request.form["student_id"]
        password = request.form["password"]

        students = load_json(STUDENTS_FILE)

        if student_id in students and students[student_id]["password"] == password:
            session["student"] = student_id
            return redirect("/student_dashboard")

        return "Invalid Student Login"

    return render_template("student_login.html")


@app.route("/student_dashboard")
def student_dashboard():
    if "student" not in session:
        return redirect("/student_login")

    student_id = session["student"]

    students = load_json(STUDENTS_FILE)
    student = students[student_id]

    session_data = load_json(SESSION_FILE)

    attendance_records = []
    total_classes = 0
    total_present = 0
    total_absent = 0

    course_summary = {}

    if os.path.exists(ATTENDANCE_FILE):

        with open(ATTENDANCE_FILE, "r") as f:

            reader = csv.DictReader(f)

            for row in reader:

                if row["Student_ID"] == student_id:

                    attendance_records.append(row)

                    total_classes += 1

                    course = row["Course"]

                    if course not in course_summary:

                        course_summary[course] = {
                            "total": 0,
                            "present": 0,
                            "absent": 0
                        }

                    course_summary[course]["total"] += 1

                    if row["Status"] == "Present":

                        total_present += 1
                        course_summary[course]["present"] += 1

                    elif row["Status"] == "Absent":

                        total_absent += 1
                        course_summary[course]["absent"] += 1

    percentage = 0

    if total_classes > 0:
        percentage = round((total_present / total_classes) * 100, 2)

    return render_template(
        "student_dashboard.html",
        student=student,
        student_id=student_id,
        attendance_records=attendance_records,
        total_classes=total_classes,
        total_present=total_present,
        total_absent=total_absent,
        percentage=percentage,
        course_summary=course_summary,
        session_data=session_data
    )

# ================= STUDENT REPORT =================

@app.route("/student_report/<student_id>")
def student_report(student_id):

    records = []

    if os.path.exists(ATTENDANCE_FILE):

        with open(ATTENDANCE_FILE, "r") as f:

            reader = csv.DictReader(f)

            for row in reader:

                if row["Student_ID"] == student_id:
                    records.append(row)

    return render_template(
        "student_report.html",
        records=records,
        student_id=student_id
    )


# ================= DOWNLOAD PDF REPORT =================

@app.route("/download_student_report/<student_id>")
def download_student_report(student_id):

    filename = f"{student_id}_report.pdf"

    doc = SimpleDocTemplate(filename)

    elements = []

    data = [
        ["Class No", "Course", "Date", "Status"]
    ]

    if os.path.exists(ATTENDANCE_FILE):

        with open(ATTENDANCE_FILE, "r") as f:

            reader = csv.DictReader(f)

            for row in reader:

                if row["Student_ID"] == student_id:

                    data.append([
                        row["Class_No"],
                        row["Course"],
                        row["Date"],
                        row["Status"]
                    ])

    table = Table(data)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.blue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige)
    ]))

    elements.append(table)

    doc.build(elements)

    return send_file(filename, as_attachment=True)

# ================= STUDENT LOGOUT =================

@app.route("/student_logout")
def student_logout():

    session.pop("student", None)

    return redirect("/student_login")

# ================= ATTENDANCE =================

@app.route("/student_face_attendance")
def student_face_attendance():
    if "student" not in session:
        return redirect("/student_login")

    student_id = session["student"]
    session_data = load_json(SESSION_FILE)

    if not session_data.get("active"):
        return "No active attendance session"

    if not session_data.get("esp32_verified"):
        return "ESP32 verification required. You must be inside classroom."

    students = load_json(STUDENTS_FILE)

    if student_id not in students:
        return "Student not found"

    student = students[student_id]
    student_folder = os.path.join(DATASET, student_id)

    if not os.path.exists(student_folder):
        return "Face dataset not found. Please register face first."

    video = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    video.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    video.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    cv2.namedWindow("Student Face Attendance", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Student Face Attendance", 1200, 750)

    matched = False
    name = student["full_name"]

    while True:
        ret, frame = video.read()

        if not ret:
            video.release()
            cv2.destroyAllWindows()
            return "Camera not opening. Check webcam permission."

        frame = cv2.flip(frame, 1)

        current_frame_path = "student_current_frame.jpg"
        cv2.imwrite(current_frame_path, frame)

        display_frame = frame.copy()

        cv2.putText(
            display_frame,
            "Show your face clearly - Press ENTER to stop",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        cv2.imshow("Student Face Attendance", display_frame)

        key = cv2.waitKey(500)

        for image_name in os.listdir(student_folder):
            image_path = os.path.join(student_folder, image_name)

            try:
                result = DeepFace.verify(
                    img1_path=current_frame_path,
                    img2_path=image_path,
                    enforce_detection=False,
                    model_name="Facenet"
                )

                if result["verified"]:
                    matched = True
                    break

            except Exception as e:
                print("DeepFace Error:", e)

        if matched:
            cv2.putText(
                display_frame,
                f"Matched: {name}",
                (30, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            cv2.imshow("Student Face Attendance", display_frame)
            cv2.waitKey(2000)

            course = session_data["course"]
            class_hour = session_data["class_hour"]
            class_no = session_data["class_no"]

            today = datetime.now().strftime("%Y-%m-%d")
            time_now = datetime.now().strftime("%H:%M:%S")

            updated = update_attendance_present(student_id, course, class_no)

            if updated:
                speak(f"Attendance has been marked for {name}, ID {student_id}")

                send_notification(
                    student_id,
                    name,
                    course,
                    class_hour,
                    today,
                    time_now,
                    "Present",
                    class_no
                )

            video.release()
            cv2.destroyAllWindows()

            if os.path.exists(current_frame_path):
                os.remove(current_frame_path)

            return redirect("/student_dashboard")

        if key == 13:
            break

    video.release()
    cv2.destroyAllWindows()

    if os.path.exists("student_current_frame.jpg"):
        os.remove("student_current_frame.jpg")

    return "Face not matched. Attendance not marked."

@app.route("/send_absent_notifications")
def send_absent_notifications():
    if "teacher" not in session:
        return redirect("/teacher_login")

    session_data = load_json(SESSION_FILE)

    if not session_data.get("active"):
        return "No active session"

    class_no = session_data["class_no"]
    course = session_data["course"]
    class_hour = session_data["class_hour"]

    students = load_json(STUDENTS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M:%S")

    with open(ATTENDANCE_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Class_No"] == str(class_no) and row["Course"] == course and row["Status"] == "Absent":
                sid = row["Student_ID"]
                if sid in students:
                    send_notification(
                        sid,
                        students[sid]["full_name"],
                        course,
                        class_hour,
                        today,
                        time_now,
                        "Absent",
                        class_no
                    )

    return redirect("/teacher_dashboard")


@app.route("/view_attendance")
def view_attendance():
    records = []

    if os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)

    return render_template("view_attendance.html", records=records)


@app.route("/attendance_graph")
def attendance_graph():
    records = []

    if os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)

    present = 0
    absent = 0

    for r in records:
        if r["Status"] == "Present":
            present += 1
        elif r["Status"] == "Absent":
            absent += 1

    return render_template("attendance_graph.html", present=present, absent=absent)

# ================= MONTHLY REPORT =================

@app.route("/monthly_report")
def monthly_report():

    monthly_data = {}

    if os.path.exists(ATTENDANCE_FILE):

        with open(ATTENDANCE_FILE, "r") as f:

            reader = csv.DictReader(f)

            for row in reader:

                month = row["Date"][:7]

                if month not in monthly_data:

                    monthly_data[month] = {
                        "present": 0,
                        "absent": 0
                    }

                if row["Status"] == "Present":

                    monthly_data[month]["present"] += 1

                elif row["Status"] == "Absent":

                    monthly_data[month]["absent"] += 1

    return render_template(
        "monthly_report.html",
        monthly_data=monthly_data
    )


# ================= SUBJECT REPORT =================

@app.route("/subject_report")
def subject_report():

    subject_data = {}

    if os.path.exists(ATTENDANCE_FILE):

        with open(ATTENDANCE_FILE, "r") as f:

            reader = csv.DictReader(f)

            for row in reader:

                course = row["Course"]

                if course not in subject_data:

                    subject_data[course] = {
                        "present": 0,
                        "absent": 0
                    }

                if row["Status"] == "Present":

                    subject_data[course]["present"] += 1

                elif row["Status"] == "Absent":

                    subject_data[course]["absent"] += 1

    return render_template(
        "subject_report.html",
        subject_data=subject_data
    )
# ================= ATTENDANCE SHORTAGE BELOW 75% =================

@app.route("/attendance_shortage")
def attendance_shortage():

    shortage_list = []

    students = load_json(STUDENTS_FILE)

    for student_id, student in students.items():

        total_classes = 0
        total_present = 0

        if os.path.exists(ATTENDANCE_FILE):

            with open(ATTENDANCE_FILE, "r") as f:

                reader = csv.DictReader(f)

                for row in reader:

                    if row["Student_ID"] == student_id:

                        total_classes += 1

                        if row["Status"] == "Present":
                            total_present += 1

        percentage = 0

        if total_classes > 0:
            percentage = round((total_present / total_classes) * 100, 2)

        if percentage < 75:

            shortage_list.append({
                "student_id": student_id,
                "name": student["full_name"],
                "total_classes": total_classes,
                "present": total_present,
                "percentage": percentage
            })

    return render_template(
        "attendance_shortage.html",
        shortage_list=shortage_list
    )


@app.route("/send_shortage_alerts")
def send_shortage_alerts():

    if "hod" not in session:
        return redirect("/hod_login")

    students = load_json(STUDENTS_FILE)

    for student_id, student in students.items():

        total_classes = 0
        total_present = 0

        if os.path.exists(ATTENDANCE_FILE):

            with open(ATTENDANCE_FILE, "r") as f:

                reader = csv.DictReader(f)

                for row in reader:

                    if row["Student_ID"] == student_id:

                        total_classes += 1

                        if row["Status"] == "Present":
                            total_present += 1

        if total_classes > 0:

            percentage = round((total_present / total_classes) * 100, 2)

            if percentage < 75:

                message = f"""
Hello {student["full_name"]},

Your attendance is below 75%.

Student ID: {student_id}
Total Classes: {total_classes}
Present: {total_present}
Attendance Percentage: {percentage}%

Please attend classes regularly.

AI-Based Face Recognition Attendance System
"""

                parent_message = f"""
Hello Parent,

Your child {student["full_name"]}'s attendance is below 75%.

Student ID: {student_id}
Total Classes: {total_classes}
Present: {total_present}
Attendance Percentage: {percentage}%

Please take necessary action.
"""

                send_email(student["student_email"], "Attendance Shortage Alert", message)

                send_email(student["parent_email"], "Attendance Shortage Alert", parent_message)

                send_sms(student["student_phone"], message)

                send_sms(student["parent_phone"], parent_message)

    return redirect("/hod_dashboard")
            
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)