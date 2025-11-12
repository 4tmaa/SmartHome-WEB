#JANGAN LUPA ISI KOLOM YANG KOSONG
# app.config['MAIL_USERNAME'] = '' 
# app.config['MAIL_PASSWORD'] = ''  

# database=" "

# app.config['SECRET_KEY'] = ' '

# sender=' @gmail.com',

# local_flask_url = " "

from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from flask_mail import Mail, Message
import mysql.connector
from datetime import datetime
from datetime import datetime, timedelta
import pytz
from werkzeug.security import check_password_hash, generate_password_hash
import random
import string
import os
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = ' '

# Set the folder to store uploaded images
UPLOAD_FOLDER = 'SmartHome/static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# Konfigurasi Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''  # Ganti dengan email pengirim
app.config['MAIL_PASSWORD'] = ''  # Ganti dengan password email pengirim

mail = Mail(app)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",       # Atau "127.0.0.1"
        user="root",            # User default untuk XAMPP/MAMP
        password="",            # Password default XAMPP/MAMP biasanya kosong
        database=""  # Sesuaikan jika nama database lokal Anda berbeda
    )

# Routes
@app.route('/')
def index():
    # Koneksi ke database MySQL
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Query untuk mendapatkan jumlah percobaan gagal hari ini
    cursor.execute("""
        SELECT COUNT(*) as failed_attempts
        FROM access_logs
        WHERE status = 'failed' AND DATE(access_time) = CURDATE()
    """)
    failed_attempts_result = cursor.fetchone()
    failed_attempts = failed_attempts_result['failed_attempts']

    # Query untuk mendapatkan waktu percobaan gagal terakhir
    cursor.execute("""
        SELECT access_time
        FROM access_logs
        WHERE status = 'failed'
        ORDER BY access_time DESC LIMIT 1
    """)
    last_failed_time_result = cursor.fetchone()
    last_failed_time = last_failed_time_result['access_time'] if last_failed_time_result else None
    jakarta = pytz.timezone('Asia/Jakarta')
    if last_failed_time:
        if last_failed_time.tzinfo is None:
            last_failed_time = pytz.utc.localize(last_failed_time)
        last_failed_time = last_failed_time.astimezone(jakarta)


    # Mengambil data sensor terbaru dan status pencahayaan
    latest_sensor_data, light_status, lux = get_sensor_data()

     # Mengambil status pintu dari database
    cursor.execute("SELECT status FROM door_status WHERE id = 1")
    door_status = cursor.fetchone()['status']

    # Mengambil data aktivitas terbaru
    recent_activity = get_recent_activity()

    # Mengambil notifikasi (suhu dan percobaan akses gagal)
    notifications = get_notifications()

    # Mengambil suhu dan kelembapan dalam 24 jam terakhir
    cursor.execute("SELECT temperature, humidity, recorded_at FROM dht11_logs WHERE recorded_at > NOW() - INTERVAL 1 DAY ORDER BY recorded_at ASC")
    sensor_data = cursor.fetchall()

    cursor.close()
    conn.close()

    # Mendapatkan waktu dan tanggal saat ini
    current_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S")
    current_date = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d")

    # Memeriksa apakah user sudah login
    if 'username' in session:
        user_info = {'username': session['username'], 'role': session['role']}
    else:
        # Mode Guest jika tidak ada session
        user_info = {'username': 'Guest', 'role': 'Guest'}

    if sensor_data:
        temperature_data = [data['temperature'] for data in sensor_data]
        humidity_data = [data['humidity'] for data in sensor_data]
        jakarta = pytz.timezone('Asia/Jakarta')
        timestamps = [data['recorded_at'].astimezone(jakarta).strftime("%H:%M") for data in sensor_data]

    else:
        temperature_data, humidity_data, timestamps = [], [], []

    # Mengirimkan data ke template
    return render_template('index.html',
                           current_time=current_time,
                           current_date=current_date,
                           user=user_info,
                           door_status=door_status,
                           latest_sensor_data=latest_sensor_data,
                           light_status=light_status,
                           lux_data=lux,
                           recent_activity=recent_activity,
                           notifications=notifications,
                           failed_attempts=failed_attempts,
                           last_failed_time=last_failed_time,
                           temperature_data=temperature_data,
                           humidity_data=humidity_data,
                           timestamps=timestamps)

@app.route('/open_gate', methods=['POST'])
def open_gate():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update status pintu menjadi 'open'
        cursor.execute("UPDATE door_status SET status = 'open' WHERE id = 1")
        conn.commit()

        # Menampilkan pesan atau kembali ke halaman yang sesuai
        flash('Pintu terbuka', 'success')
        return redirect(url_for('index'))  # Kembali ke halaman index

    except mysql.connector.Error as e:
        conn.rollback()
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))  # Kembali ke halaman index

    finally:
        cursor.close()
        conn.close()

@app.route('/lock_gate', methods=['POST'])
def lock_gate():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update status pintu menjadi 'locked'
        cursor.execute("UPDATE door_status SET status = 'locked' WHERE id = 1")
        conn.commit()

        # Menampilkan pesan atau kembali ke halaman yang sesuai
        flash('Pintu terkunci', 'success')
        return redirect(url_for('index'))  # Kembali ke halaman index

    except mysql.connector.Error as e:
        conn.rollback()
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))  # Kembali ke halaman index

    finally:
        cursor.close()
        conn.close()

@app.route('/get_door_status', methods=['GET'])
def get_door_status():
    # Koneksi ke database untuk mengambil status pintu
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM door_status WHERE id = 1")  # Mengambil status pintu
    door_status = cursor.fetchone()

    cursor.close()
    conn.close()

    # Jika status ada, kirimkan ke ESP32
    if door_status:
        return jsonify({'status': door_status[0]}), 200  # Mengembalikan status pintu ('open' atau 'locked')
    else:
        return jsonify({'status': 'error', 'message': 'Status pintu tidak ditemukan'}), 500

def get_security_data():
    # Koneksi ke database MySQL
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Mengambil jumlah percobaan gagal hari ini
    cursor.execute("SELECT COUNT(*) AS failed_attempts FROM access_logs WHERE status = 'Gagal' AND access_time >= CURDATE()")
    failed_attempts = cursor.fetchone()['failed_attempts']

    # Mengambil waktu terakhir percobaan gagal
    cursor.execute("SELECT access_time FROM access_logs WHERE status = 'Gagal' ORDER BY access_time DESC LIMIT 1")
    last_failed_time = cursor.fetchone()

    cursor.close()
    conn.close()

    return failed_attempts, last_failed_time['access_time'] if last_failed_time else None

def get_sensor_data():
    # Koneksi ke database MySQL
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Mengambil suhu dan kelembaban dalam 24 jam terakhir
    cursor.execute("SELECT temperature, humidity, recorded_at FROM dht11_logs ORDER BY recorded_at DESC LIMIT 1")
    latest_sensor_data = cursor.fetchone()  # Mengambil data terbaru
    print("Latest Sensor Data:", latest_sensor_data)  # Debugging print statement

    # Mengambil status pencahayaan berdasarkan LDR
    cursor.execute("SELECT lux FROM lux_logs ORDER BY created_at DESC LIMIT 1")
    lux = cursor.fetchone()
    print("LUX Data:", lux)  # Debugging print statement

    cursor.close()
    conn.close()

    if latest_sensor_data:
        # Menentukan status pencahayaan berdasarkan nilai LDR
        if lux and lux['lux'] < 100:
            light_status = 'ON'
        else:
            light_status = 'OFF'
        return latest_sensor_data, light_status, lux
    else:
        return None, 'No Data', None

def get_recent_activity():
    # Koneksi ke database MySQL
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Mengambil 5 aktivitas terbaru dari tabel akseslog
    cursor.execute("SELECT access_time, username, access_type, status FROM access_logs ORDER BY access_time DESC LIMIT 5")
    recent_activity = cursor.fetchall()  # Mengambil data aktivitas terbaru

    cursor.close()
    conn.close()

    # Konversi waktu access_time ke Asia/Jakarta
    jakarta = pytz.timezone('Asia/Jakarta')
    for row in recent_activity:
        if row['access_time'].tzinfo is None:
            row['access_time'] = pytz.utc.localize(row['access_time'])
        row['access_time'] = row['access_time'].astimezone(jakarta)

    return recent_activity

def get_notifications(limit=5):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT message, timestamp
        FROM notifications
        ORDER BY timestamp DESC
        LIMIT %s
    """, (limit,))
    notifications = cursor.fetchall()
    cursor.close()
    conn.close()

    # Format timestamp lokal WIB tanpa offset
    jakarta = pytz.timezone('Asia/Jakarta')
    for notif in notifications:
        ts = notif['timestamp']
        if ts.tzinfo is None:
            ts = jakarta.localize(ts)
        notif['formatted_time'] = ts.astimezone(jakarta).strftime('%d-%m %H:%M WIB')

    return notifications


@app.route('/api/get_time')
def get_time():
    # Mendapatkan waktu dan tanggal saat ini
    current_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S")
    current_date = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d")
    return jsonify({'current_time': current_time, 'current_date': current_date})

@app.route('/store-sensor-data', methods=['POST'])
def store_sensor_data():
    # Mendapatkan data JSON yang dikirim dari client
    data = request.get_json()

    # Mengambil nilai dari data JSON
    temperature = data['temperature']
    humidity = data['humidity']
    lux = data['lux']  # Mengubah ldr_value menjadi lux

    # Menentukan status cahaya berdasarkan nilai lux
    light_status = 'ON' if lux < 50 else 'OFF'  # Menggunakan lux, bukan ldr_value

    # Menyimpan data ke database
    connection = get_db_connection()
    cursor = connection.cursor()

    # Menyimpan data suhu dan kelembapan ke tabel dht11_logs
    cursor.execute("INSERT INTO dht11_logs (temperature, humidity) VALUES (%s, %s)", (temperature, humidity))

    # Menyimpan data Lux ke tabel ldr_logs (ubah nama tabel jika perlu)
    cursor.execute("INSERT INTO lux_logs (lux, light_status) VALUES (%s, %s)", (lux, light_status))  # Ubah nama tabel menjadi lux_logs

    # Commit transaksi dan menutup koneksi
    connection.commit()
    cursor.close()
    connection.close()

    # Mengirim respon sukses kembali ke client
    return jsonify({'status': 'success', 'message': 'Data stored successfully'}), 200

@app.route('/store-log-data', methods=['POST'])
def store_log_data():
    data = request.get_json()  # Mengambil data JSON yang diterima untuk log akses

    # Debugging: Menampilkan data JSON yang diterima untuk log
    print(f"Data JSON Log yang diterima: {data}")

    # Ambil data dari JSON
    username = data['username']  # Ganti user_id dengan username
    access_type = data['access_type']
    status = data['status']

    # Koneksi ke database
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Menyimpan log akses ke tabel access_logs
        cursor.execute("""
            INSERT INTO access_logs (username, access_type, status)
            VALUES (%s, %s, %s)
        """, (username, access_type, status))

        # Commit perubahan ke database
        connection.commit()
        return jsonify({'status': 'success', 'message': 'Log data stored successfully.'}), 200

    except mysql.connector.Error as e:
        print(f"Error inserting data: {e}")
        connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@app.route('/receive-failed-attempt', methods=['POST'])
def receive_failed_attempt():
    # Mengambil data JSON yang diterima
    data = request.get_json()

    # Debugging: Menampilkan data yang diterima
    print(f"Received data: {data}")

    # Ambil data dari JSON
    username = data['username']  # Ganti user_id dengan username
    access_type = data['access_type']
    status = data['status']

    # Memeriksa apakah data lengkap
    if not username or not access_type or not status:
        return jsonify({"message": "Invalid data!"}), 400

    # Jika event_type adalah "keypad" dan status adalah "failed", kirim data ke Flask Lokal
    if access_type == 'keypad' and status == 'failed':
        # Kirim data percobaan gagal ke Flask Lokal
        local_flask_url = " (isi sendiri)"  # Ganti dengan alamat Flask Lokal yang benar

        # Menggunakan `requests` untuk mengirim data ke Flask Lokal
        response = requests.post(local_flask_url, json=data)

        # Memeriksa apakah data berhasil dikirim ke Flask Lokal
        if response.status_code == 200:
            return jsonify({"message": "Data sent to Flask Local and image will be captured."}), 200
        else:
            return jsonify({"message": "Failed to send data to Flask Local."}), 500

    return jsonify({"message": "Log data stored successfully."}), 200

@app.route('/upload-image', methods=['POST'])
def upload_image():
    image = request.files.get('image')
    event_type = request.form.get('event_type')  # Ambil event_type dari data
    age = request.form.get('age')
    gender = request.form.get('gender')
    # Ambil waktu UTC langsung dari server
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    if image:
        # Menyimpan gambar ke filesystem
        image_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        image_path = os.path.join('static/uploads', image_filename)
        image.save(image_path)
        face_count = request.form.get('face_count')
        faces_raw = request.form.get('faces')  # ini adalah string, misalnya "[{'age': 25, 'gender': 'Man'}]"


        # Menyimpan informasi gambar ke dalam database dengan path relatif
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO photos_and_events (event_type, filepath, timestamp, age, gender, face_count, faces)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            event_type,
            f"uploads/{image_filename}",
            timestamp,
            age,
            gender,
            face_count,
            faces_raw
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Image uploaded and saved successfully."}), 200
    else:
        return jsonify({"message": "No image found."}), 400

@app.route('/temperature_logs')
def temperature_logs():
    # Koneksi ke database MySQL
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Menentukan jumlah data per halaman
    per_page = 25

    # Mendapatkan nomor halaman dari query string (default ke halaman 1 jika tidak ada)
    page = request.args.get('page', 1, type=int)

    # Menghitung offset berdasarkan halaman yang dipilih
    offset = (page - 1) * per_page

    # Query untuk mengambil data suhu dan kelembapan dengan LIMIT dan OFFSET untuk paginasi
    cursor.execute("""
        SELECT recorded_at, temperature, humidity
        FROM dht11_logs
        ORDER BY recorded_at DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))

    logs = cursor.fetchall()  # Menyimpan data log dari database
    # 🔁 Konversi timezone
    jakarta = pytz.timezone('Asia/Jakarta')
    for log in logs:
        if log['recorded_at']:
            if log['recorded_at'].tzinfo is None:
                log['recorded_at'] = pytz.utc.localize(log['recorded_at'])
            log['recorded_at'] = log['recorded_at'].astimezone(jakarta)

    # Query untuk menghitung total jumlah data log
    cursor.execute("SELECT COUNT(*) FROM dht11_logs")
    total_logs = cursor.fetchone()['COUNT(*)']

    cursor.close()
    conn.close()

    # Menambahkan notifikasi jika suhu atau kelembapan tinggi
    for log in logs:
        if log['temperature'] > 30 or log['humidity'] > 80:
            message = f"High temperature: {log['temperature']}°C or humidity: {log['humidity']}%"
            add_notification(message, "Sensor Reading", "Sensor")

    # Menghitung jumlah halaman berdasarkan total data log
    total_pages = (total_logs // per_page) + (1 if total_logs % per_page > 0 else 0)

    # Mengirim data log dan informasi paginasi ke template
    return render_template('temperature_logs.html', logs=logs, page=page, total_pages=total_pages)

@app.route('/light_logs')
def light_logs():
    # Koneksi ke database MySQL
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Menentukan jumlah data per halaman
    per_page = 25

    # Mendapatkan nomor halaman dari query string (default ke halaman 1 jika tidak ada)
    page = request.args.get('page', 1, type=int)

    # Menghitung offset berdasarkan halaman yang dipilih
    offset = (page - 1) * per_page

    # Query untuk mengambil data dari tabel lux_logs dengan LIMIT dan OFFSET untuk paginasi
    cursor.execute("""
        SELECT created_at, lux, light_status
        FROM lux_logs
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))

    logs = cursor.fetchall()  # Menyimpan data log dari database
    # 🔁 Konversi timezone
    jakarta = pytz.timezone('Asia/Jakarta')
    for log in logs:
        if log['created_at']:
            if log['created_at'].tzinfo is None:
                log['created_at'] = pytz.utc.localize(log['created_at'])
            log['created_at'] = log['created_at'].astimezone(jakarta)

    # Query untuk menghitung total jumlah data log
    cursor.execute("SELECT COUNT(*) FROM lux_logs")
    total_logs = cursor.fetchone()['COUNT(*)']

    cursor.close()
    conn.close()

    # Menambahkan notifikasi jika status cahaya berubah
    for log in logs:
        if log['light_status'] == 'ON':  # Menyesuaikan status cahaya dengan 'ON' atau 'OFF'
            message = f"Light turned on at {log['created_at'].strftime('%d-%m-%Y %H:%M')}"
            add_notification(message, "Light Update", "Sensor", timestamp=log['created_at'])

        elif log['light_status'] == 'OFF':
            message = f"Light turned off at {log['created_at'].strftime('%d-%m-%Y %H:%M')}"
            add_notification(message, "Light Update", "Sensor", timestamp=log['created_at'])

    # Menghitung jumlah halaman berdasarkan total data log
    total_pages = (total_logs // per_page) + (1 if total_logs % per_page > 0 else 0)

    # Mengirim data log dan informasi paginasi ke template
    return render_template('light_logs.html', logs=logs, page=page, total_pages=total_pages)

@app.route('/web_user_management')
def web_user_management():
    # Pastikan pengguna sudah login dan role-nya sesuai
    if 'username' not in session:
        return render_template('web_user_management.html', message="You must be logged in to view this page.", user_role='guest')

    # Dapatkan role pengguna dari session
    user_role = session.get('role')

    # Fetch user data from the 'web_users' table
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM web_users")  # Mengambil semua pengguna
    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('web_user_management.html', users=users, user_role=user_role)

@app.route('/update_user/<int:user_id>', methods=['GET', 'POST'])
def update_user(user_id):
    # Memastikan hanya admin yang dapat mengakses
    if session.get('role') != 'admin':
        return redirect(url_for('login'))  # Redirect jika bukan admin

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Ambil data pengguna yang ingin diubah
    cursor.execute("SELECT * FROM web_users WHERE web_user_id = %s", (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        # Mengambil data dari form
        username = request.form['username']
        role = request.form['role']

        # Update nama dan role
        cursor.execute(
            "UPDATE web_users SET username = %s, role = %s WHERE web_user_id = %s",
            (username, role, user_id)
        )

        conn.commit()
        cursor.close()
        conn.close()

        flash('User updated successfully!', 'success')
        return redirect(url_for('web_user_management'))

    cursor.close()
    conn.close()

    return render_template('update_user.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['GET'])
def delete_user(user_id):
    # Pastikan hanya admin yang dapat mengakses
    if session.get('role') != 'admin':
        return redirect(url_for('login'))  # Redirect jika bukan admin

    conn = get_db_connection()
    cursor = conn.cursor()

    # Hapus pengguna dari database
    cursor.execute("DELETE FROM web_users WHERE web_user_id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('User deleted successfully!', 'success')
    return redirect(url_for('web_user_management'))

@app.route('/access_logs')
def access_logs():
    # 1. Pastikan pengguna sudah login
    if 'username' not in session:
        return render_template('access_logs.html', message="You must be logged in to view this page.", user_role='guest', page=1, total_pages=1, logs=[])

    user_role = session.get('role')

    # 2. Tolak akses jika 'guest'
    if user_role == 'guest':
        return render_template('access_logs.html', message="Access restricted. Please log in as a user or admin to view content.", user_role='guest', page=1, total_pages=1, logs=[])

    # 3. Pengaturan Pagination (mengikuti contoh Anda)
    per_page = 10  # Anda bisa ubah ini (contoh: 10 log per halaman)
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * per_page

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 4. Query untuk MENGHITUNG total log (hanya sekali)
        cursor.execute("SELECT COUNT(*) FROM access_logs")
        total_logs = cursor.fetchone()['COUNT(*)']

        # 5. Query untuk MENGAMBIL log halaman ini
        query = """
            SELECT log_id, username, access_time, access_type, status 
            FROM access_logs 
            ORDER BY access_time DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (per_page, offset))
        logs = cursor.fetchall()  # Mengambil data logs untuk halaman ini

    except mysql.connector.Error as err:
        flash(f"Database error: {err}")
        return redirect(url_for('dashboard')) # Arahkan ke tempat aman
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

    # 6. Perhitungan Total Halaman (tanpa import math)
    total_pages = (total_logs // per_page) + (1 if total_logs % per_page > 0 else 0)
    
    # Jika total_pages adalah 0, jadikan 1 (untuk kasus database kosong)
    if total_pages == 0:
        total_pages = 1

    # 7. Konversi Timezone
    jakarta = pytz.timezone('Asia/Jakarta')
    for log in logs:
        if log['access_time'] and log['access_time'].tzinfo is None:
            log['access_time'] = pytz.utc.localize(log['access_time'])
        log['access_time'] = log['access_time'].astimezone(jakarta)

    # 8. Logika Notifikasi (jika ada)
    for log in logs:
        if log['status'] == 'failed':
            message = f"Failed access attempt by {log['username']}"
            add_notification(message, "Access Attempt", log['username'])

    # 9. Kirim data logs dan data pagination ke template
    return render_template('access_logs.html', 
                           logs=logs, 
                           user_role=user_role,
                           page=page,
                           total_pages=total_pages)

@app.route('/failed_attempts')
def failed_attempts():
    if session.get('role') != 'admin':
        return render_template('failed_attempts.html', message="You must be logged as admin to view this page.", user_role='guest')

    user_role = session.get('role')

    per_page = 25
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT log_id, username, access_time, access_type, 'failed' AS status
        FROM access_logs
        WHERE username = 'Orang Asing' AND status = 'failed'
        ORDER BY access_time DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    access_logs_failed = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) FROM access_logs
        WHERE username = 'Orang Asing' AND status = 'failed'
    """)
    total_failed_logs = cursor.fetchone()['COUNT(*)']
    cursor.close()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM photos_and_events
        WHERE event_type = 'Wrong PIN'
        ORDER BY timestamp DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    photos_and_events_failed = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) FROM photos_and_events
        WHERE event_type = 'Wrong PIN'
    """)
    total_failed_events = cursor.fetchone()['COUNT(*)']
    cursor.close()
    conn.close()

    all_failed_attempts = access_logs_failed + photos_and_events_failed
    total_logs = total_failed_logs + total_failed_events
    total_pages = (total_logs // per_page) + (1 if total_logs % per_page > 0 else 0)

    jakarta = pytz.timezone('Asia/Jakarta')
    for attempt in all_failed_attempts:
        if 'access_time' in attempt and attempt['access_time']:
            if attempt['access_time'].tzinfo is None:
                attempt['access_time'] = pytz.utc.localize(attempt['access_time'])
            attempt['access_time'] = attempt['access_time'].astimezone(jakarta)

        if 'timestamp' in attempt and attempt['timestamp']:
            if attempt['timestamp'].tzinfo is None:
                attempt['timestamp'] = pytz.utc.localize(attempt['timestamp'])
            attempt['timestamp'] = attempt['timestamp'].astimezone(jakarta)

        if attempt.get('access_type') == 'keypad':
            attempt['event_type'] = 'Wrong PIN'

    return render_template(
        'failed_attempts.html',
        attempts=all_failed_attempts,
        user_role=user_role,
        page=page,
        total_pages=total_pages
    )

@app.route('/attempt/<int:attempt_id>')
def view_attempt(attempt_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM photos_and_events WHERE id = %s", (attempt_id,))
    attempt = cursor.fetchone()

    cursor.close()
    conn.close()

    if not attempt:
        return "Attempt not found", 404

    # Parse JSON string dari kolom faces
    import json
    try:
        faces = json.loads(attempt['faces']) if attempt['faces'] else []
    except json.JSONDecodeError:
        faces = []

    return render_template("view_attempt.html", attempt=attempt, faces=faces)

@app.route('/light_rules', methods=['GET', 'POST'])
def light_rules():
    # Memastikan hanya admin yang dapat mengakses halaman ini
    if session.get('role') != 'admin':
        return render_template('light_rules.html', message="You must be logged as admin in to view this page.", user_role='guest')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Ambil data waktu nyala dan mati LED dari tabel led_schedule
    cursor.execute("SELECT * FROM led_schedule WHERE status = 'on' OR status = 'off'")
    light_rules = cursor.fetchall()

    if request.method == 'POST':
        status = request.form['status']

        # Update waktu berdasarkan status yang dipilih
        if status == 'on':
            on_time = request.form['on_time']
            cursor.execute("UPDATE led_schedule SET time = %s WHERE status = 'on'", (on_time,))
            message = f"Lights turned on at {on_time}"
            add_notification(message, "Light Update", "Admin")
        elif status == 'off':
            off_time = request.form['off_time']
            cursor.execute("UPDATE led_schedule SET time = %s WHERE status = 'off'", (off_time,))
            message = f"Lights turned off at {off_time}"
            add_notification(message, "Light Update", "Admin")

        conn.commit()
        flash('Light rules updated successfully!', 'success')
        return redirect(url_for('light_rules'))  # Redirect kembali ke halaman Light Rules

    cursor.close()
    conn.close()

    # Kirim data waktu nyala dan mati ke template
    on_time = light_rules[0].get('time') if light_rules[0]['status'] == 'on' else None
    off_time = light_rules[1].get('time') if light_rules[1]['status'] == 'off' else None

    return render_template('light_rules.html', light_rules=light_rules, on_time=on_time, off_time=off_time, user_role=session.get('role'))

@app.route('/update_light_time/<string:status>', methods=['GET', 'POST'])
def update_light_time(status):
    # Memastikan hanya admin yang dapat mengakses
    if session.get('role') != 'admin':
        return redirect(url_for('login'))  # Redirect jika bukan admin

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Ambil data berdasarkan status (on atau off)
    cursor.execute("SELECT * FROM led_schedule WHERE status = %s LIMIT 1", (status,))
    light_schedule = cursor.fetchone()

    if request.method == 'POST':
        # Ambil waktu baru dari form
        new_time = request.form['time']

        # Perbarui hanya waktu berdasarkan status yang dipilih
        cursor.execute("UPDATE led_schedule SET time = %s WHERE status = %s", (new_time, status))
        conn.commit()

        # Debugging: Pastikan notifikasi ditambahkan
        print(f"Updating {status.capitalize()} time to {new_time}")

        # Menambahkan notifikasi setelah update waktu LED
        message = f"{status.capitalize()} time updated to {new_time}"
        add_notification(message, "Light Update", "Admin")

        cursor.close()
        conn.close()

        flash(f'{status.capitalize()} time updated successfully!', 'success')
        return redirect(url_for('light_rules'))  # Redirect ke halaman utama light rules

    cursor.close()
    conn.close()

    return render_template('update_light_time.html', light_schedule=light_schedule, status=status)

def add_notification(message, type, user, timestamp=None):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Kolom timestamp disisipkan secara eksplisit!
        cursor.execute(
            "INSERT INTO notifications (message, type, user, timestamp) VALUES (%s, %s, %s, %s)",
            (message, type, user, now)
        )
        conn.commit()

        cursor.close()
        conn.close()
        flash('Notification added successfully!', 'success')

    except Exception as e:
        print(f"Error adding notification: {e}")
        flash('An error occurred while adding the notification.', 'danger')


@app.route('/notifications')
def notifications():
    # Pastikan pengguna sudah login dan role-nya sesuai
    if 'username' not in session:
        return render_template('notifications.html', message="You must be logged in to view this page.", user_role='guest')

    # Dapatkan role pengguna dari session
    user_role = session.get('role')

    # Koneksi ke database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Menentukan jumlah data per halaman
    per_page = 25

    # Mendapatkan nomor halaman dari query string (default ke halaman 1 jika tidak ada)
    page = request.args.get('page', 1, type=int)

    # Menghitung offset berdasarkan halaman yang dipilih
    offset = (page - 1) * per_page

    # Query untuk mengambil data notifikasi dengan LIMIT dan OFFSET untuk paginasi
    cursor.execute("""
        SELECT * FROM notifications
        ORDER BY timestamp DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))

    notifications = cursor.fetchall()

    # Query untuk menghitung total jumlah notifikasi
    cursor.execute("SELECT COUNT(*) FROM notifications")
    total_notifications = cursor.fetchone()['COUNT(*)']

    cursor.close()
    conn.close()

    # Menghitung jumlah halaman berdasarkan total data notifikasi
    total_pages = (total_notifications // per_page) + (1 if total_notifications % per_page > 0 else 0)

    # Mengirim data notifikasi dan informasi paginasi ke template
    return render_template('notifications.html', notifications=notifications, user_role=user_role, page=page, total_pages=total_pages)

@app.route('/reset-pin', methods=['GET', 'POST'])
def reset_pin():
    # Memastikan hanya admin yang dapat mengakses halaman ini
    if session.get('role') != 'admin':
        return render_template('reset_pin.html', message="You must be logged as admin in to view this page.", user_role='guest')

    # Dapatkan role pengguna dari session
    user_role = session.get('role')

    # Koneksi ke database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Mendapatkan PIN baru dari formulir
        new_pin = request.form.get('new_pin')

        if not new_pin:
            return jsonify({'status': 'error', 'message': 'PIN tidak valid'}), 400

        # Koneksi ke database
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Update PIN dalam tabel 'settings'
            cursor.execute("UPDATE settings SET pin = %s WHERE id = 1", (new_pin,))

            # Commit perubahan ke database
            connection.commit()

            return jsonify({'status': 'success', 'message': 'PIN berhasil direset'}), 200

        except mysql.connector.Error as e:
            print(f"Error updating PIN: {e}")
            connection.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500

        finally:
            cursor.close()
            connection.close()
            return redirect(url_for('reset_pin'))  # Redirect ke halaman utama light rules

    # Jika method GET, tampilkan halaman reset PIN
    return render_template('reset_pin.html', user_role=user_role)

@app.route('/get-pin', methods=['GET'])
def get_pin():
    # Mengambil PIN dari database
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT pin FROM settings WHERE id = 1")
        pin = cursor.fetchone()

        if pin:
            return jsonify({'status': 'success', 'pin': pin[0]}), 200
        else:
            return jsonify({'status': 'error', 'message': 'PIN not found'}), 404
    except mysql.connector.Error as e:
        print(f"Error fetching PIN: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = request.form.get('remember')

        # Database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM web_users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        # Verifikasi user dan password
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']  # Menyimpan username di session
            session['email'] = user['email']        # Menyimpan email di session
            session['role'] = user['role']          # Menyimpan role di session

            # Remember me
            if remember:
                response = make_response(redirect(url_for('index')))
                expires = datetime.now() + timedelta(days=30)
                response.set_cookie('username', user['username'], expires=expires)
                response.set_cookie('email', user['email'], expires=expires)
                response.set_cookie('role', user['role'], expires=expires)
                flash("Login berhasil dengan Remember Me!", "success")
                return response
            else:
                flash("Login berhasil!", "success")
                return redirect(url_for('index'))
        else:
            flash("Email atau password salah.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # Menghapus session saat logout
    session.pop('username', None)
    session.pop('email', None)
    session.pop('role', None)

    # Mengarahkan kembali ke halaman index sebagai guest
    flash("Logged out successfully!", "success")
    return redirect(url_for('index'))  # Redirect ke halaman index setelah logout

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        email = request.form['email']  # Ambil email pengguna dari form

        # Cari user berdasarkan email
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM web_users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            # Membuat token reset password (misalnya menggunakan string acak)
            reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

            # Simpan token di kolom reset_token
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE web_users SET reset_token = %s WHERE email = %s", (reset_token, email))
            conn.commit()
            cursor.close()

            # Membuat link reset password
            reset_link = url_for('reset_password', token=reset_token, _external=True)

            # Kirim email untuk reset password
            send_reset_email(user['email'], reset_link)

            flash("Password reset link has been sent to your email.", "success")
            return redirect(url_for('login'))  # Arahkan ke halaman login setelah mengirim email
        else:
            flash("User not found. Please check your email.", "danger")
            return redirect(url_for('change_password'))  # Kembali ke halaman ganti password jika user tidak ditemukan

    return render_template('change_password.html')


def send_reset_email(to_email, reset_link):
    msg = Message(
        'IoT Smart Home - Reset Password Request',
        sender=' ',  # Ganti dengan email pengirim yang valid
        recipients=[to_email]  # Alamat email penerima
    )
    msg.body = f'Click the link below to reset your password:\n{reset_link}'

    try:
        mail.send(msg)
        print("Reset email sent successfully.")
    except Exception as e:
        print(f"Error: {e}")
        flash("Error sending reset email. Please try again later.", "danger")

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token')  # Mengambil token dari URL
    if not token:
        flash("Invalid token", "danger")
        return redirect(url_for('index'))  # Redirect jika token tidak ada

    # Verifikasi token (cek apakah token valid di database)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM web_users WHERE reset_token = %s", (token,))
    user = cursor.fetchone()
    cursor.close()

    if not user:
        flash("Invalid or expired token.", "danger")
        return redirect(url_for('index'))  # Jika token tidak valid, redirect ke index

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Cek apakah password baru dan konfirmasi password sama
        if new_password != confirm_password:
            flash("Passwords don't match", "danger")
            return redirect(url_for('reset_password', token=token))  # Jika password tidak cocok, tetap di halaman reset

        # Enkripsi password baru dan update
        hashed_password = generate_password_hash(new_password)

        # Update password dan hapus reset_token setelah berhasil reset
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE web_users SET password = %s, reset_token = NULL WHERE reset_token = %s", (hashed_password, token))
        conn.commit()
        cursor.close()

        flash("Your password has been reset successfully.", "success")
        return redirect(url_for('login'))  # Redirect ke login setelah password berhasil diubah

    return render_template('reset_password.html')  # Jika GET request, tampilkan halaman reset password


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        # Ambil data dari form
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validasi: Cek jika password dan confirm password cocok
        if password != confirm_password:
            flash("Passwords don't match", "danger")
            return redirect(url_for('registration'))  # Kembali ke halaman registrasi jika tidak cocok

        # Periksa apakah username atau email sudah ada di database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM web_users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()

        cursor.execute("SELECT * FROM web_users WHERE email = %s", (email,))
        existing_email = cursor.fetchone()
        cursor.close()
        conn.close()

        # Jika username atau email sudah ada, beri pesan kesalahan
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('registration'))  # Kembali ke halaman registrasi jika username sudah ada

        if existing_email:
            flash('Email is already registered. Please use a different one.', 'danger')
            return redirect(url_for('registration'))  # Kembali ke halaman registrasi jika email sudah ada

        # Enkripsi password
        hashed_password = generate_password_hash(password)

        # Simpan data pengguna ke database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO web_users (username, password, email) VALUES (%s, %s, %s)",
                       (username, hashed_password, email))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Registration successful!', 'success')
        return redirect(url_for('login'))  # Redirect ke halaman login setelah registrasi berhasil

    return render_template('registration.html')  # Tampilkan form registrasi

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='0.0.0.0', port=5000, debug=True)

