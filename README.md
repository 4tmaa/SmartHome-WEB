#  SmartHome - Dashboard & API Web
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/) [![Flask](https://img.shields.io/badge/Flask-2.x-black.svg)](https://flask.palletsprojects.com/) [![Database](https://img.shields.io/badge/Database-MySQL-orange.svg)](https://www.mysql.com/)

Sebuah sistem Smart Home berbasis web dengan Flask, terintegrasi dengan perangkat keras (seperti ESP32) untuk monitoring sensor, kontrol pintu, dan keamanan.

![Contoh Screenshot Dashboard](https://github.com/user-attachments/assets/e68752cf-6097-41d5-8ebe-6fbfd44789e6)

## 🌟 Fitur Utama

### 🏡 Dashboard & Monitoring
* **Real-time Monitoring:** Menampilkan suhu, kelembapan (DHT11), dan status pencahayaan (LDR/Lux) terbaru.
* **Grafik Sensor:** Visualisasi data suhu dan kelembapan selama 24 jam terakhir.
* **Kontrol Perangkat:** Tombol untuk membuka (`/open_gate`) dan mengunci (`/lock_gate`) pintu dari jarak jauh.
* **Notifikasi:** Panel notifikasi terpusat untuk peringatan penting (suhu tinggi, percobaan akses gagal).
* **Log Aktivitas:** Menampilkan 5 aktivitas akses terakhir di dashboard.

### 🔐 Keamanan & Akses
* **Statistik Keamanan:** Menampilkan jumlah percobaan akses gagal hari ini dan waktu kejadian terakhir.
* **Log Akses:** Halaman `/access_logs` dengan pagination untuk melihat semua riwayat akses.
* **Log Gagal & Bukti Foto:** Halaman `/failed_attempts` khusus untuk admin, menampilkan log dan foto yang ditangkap kamera saat terjadi kesalahan PIN.
* **Integrasi Kamera:** Menerima gambar (`/upload-image`) dari perangkat keras saat akses gagal dan menyimpannya.

### 👨‍💼 Manajemen & Pengguna
* **Sistem Otentikasi:** Registrasi, Login, dan Logout untuk pengguna web.
* **Reset Password:** Fitur "Lupa Password" (`/change_password`) yang mengirimkan link reset via email (menggunakan Flask-Mail).
* **Manajemen Sesi:** Menggunakan Flask Session dan opsi "Remember Me".
* **Berbasis Peran (Role):** Sistem peran sederhana (Admin, User, Guest) untuk melindungi halaman sensitif.

### ⚙️ Panel Admin
* **Manajemen Pengguna:** Admin dapat melihat, mengubah peran, dan menghapus pengguna web (`/web_user_management`).
* **Aturan Lampu:** Admin dapat mengatur jadwal waktu ON dan OFF untuk lampu (`/light_rules`).
* **Reset PIN:** Admin dapat mengubah PIN yang digunakan oleh perangkat keras (keypad) (`/reset-pin`).

### 📡 API untuk Perangkat Keras (ESP32/IoT)
Proyek ini menyediakan beberapa endpoint API penting untuk komunikasi dengan perangkat keras:

* `POST /store-sensor-data`: Menerima data JSON (suhu, kelembapan, lux) dari sensor.
* `POST /store-log-data`: Menerima data JSON (username, tipe akses, status) dari perangkat akses.
* `POST /upload-image`: Menerima file gambar (foto percobaan gagal) dari kamera.
* `GET /get_door_status`: Mengirim status pintu saat ini (open/locked) ke perangkat.
* `GET /get-pin`: Mengirim PIN yang valid saat ini ke perangkat.

## 🛠️ Teknologi yang Digunakan

* **Backend:** Python 3, Flask
* **Database:** MySQL
* **Email:** Flask-Mail (untuk reset password)
* **Keamanan:** Werkzeug (Password Hashing), Flask Session
* **Lainnya:** Pytz (Timezone), Requests
* **Target Hardware (Implied):** ESP32, DHT11, LDR, Keypad, ESP32-CAM (atau sejenisnya).

## 🚀 Instalasi & Konfigurasi

Untuk menjalankan proyek ini secara lokal:

1.  **Clone Repository**
    ```bash
    git clone [https://github.com/4tmaa/SmartHome-WEB.git](https://github.com/4tmaa/SmartHome-WEB.git)
    cd repository-anda
    ```

2.  **Buat Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # (Di Windows: venv\Scripts\activate)
    ```

3.  **Install Dependencies**
    *Buat file `requirements.txt` terlebih dahulu:*
    ```bash
    pip freeze > requirements.txt
    ```
    *Kemudian install (atau install manual: `pip install Flask mysql-connector-python Flask-Mail pytz requests`)*
    ```bash
    pip install -r requirements.txt
    ```

4.  **Setup Database**
    * Pastikan Anda memiliki server MySQL (misalnya XAMPP, MAMP, atau Docker).
    * Buat database baru (misal: `SmartHome`).
    * Impor file `.sql` Anda (jika ada) untuk membuat tabel (`web_users`, `access_logs`, `dht11_logs`, `lux_logs`, dll).

5.  **Konfigurasi Environment Variables (PENTING!)**
    Seperti yang didiskusikan sebelumnya, **JANGAN** memasukkan kredensial Anda langsung ke `app.py`. Gunakan Environment Variables. Buat file `.env` di root proyek:

    ```ini
    # File: .env
    # Kunci rahasia Flask
    SECRET_KEY='kunci_rahasia_acak_dan_panjang_anda'

    # Kredensial Database
    DB_HOST='localhost'
    DB_USER='root'
    DB_PASS=''
    DB_NAME='SmartHome'

    # Kredensial Flask-Mail (Gunakan App Password jika pakai Gmail)
    MAIL_SERVER='smtp.gmail.com'
    MAIL_PORT=587
    MAIL_USE_TLS=True
    MAIL_USERNAME='email-anda@gmail.com'
    MAIL_PASSWORD='password-app-anda'
    MAIL_SENDER='email-anda@gmail.com'
    ```
    *(Pastikan Anda telah meng-install `python-dotenv` (`pip install python-dotenv`) dan memuatnya di `app.py` agar file `.env` terbaca)*

6.  **Jalankan Aplikasi**
    ```bash
    flask run
    # Atau
    python app.py
    ```
    Aplikasi akan berjalan di `https://gonzz.pythonanywhere.com/`.
