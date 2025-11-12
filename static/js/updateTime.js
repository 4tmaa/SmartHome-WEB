// Fungsi untuk memperbarui jam, tanggal, dan kalender secara dinamis
function updateTime() {
    fetch('/api/get_time')  // Memanggil API Flask untuk mendapatkan waktu terbaru
        .then(response => response.json())
        .then(data => {
            // Perbarui elemen waktu dan tanggal dengan data dari server
            document.getElementById('time').textContent = data.current_time;
            document.getElementById('date').textContent = data.current_date;

            // Perbarui kalender
            updateCalendar(data.current_date);
        })
        .catch(error => {
            console.error('Error fetching time:', error);
        });
}

// Fungsi untuk memperbarui kalender dengan tanggal saat ini
function updateCalendar(currentDate) {
    // Mengambil elemen kalender
    const dateObj = new Date(currentDate);
    const dayOfWeek = dateObj.getDay();  // Hari dalam seminggu (0=Sun, 1=Mon, ... 6=Sat)
    const month = dateObj.toLocaleString('default', { month: 'long' });  // Nama bulan dalam bahasa
    const dayOfMonth = dateObj.getDate();  // Tanggal dalam bulan

    // Update nama bulan dan tahun
    const monthElement = document.querySelector('.month-name');
    monthElement.textContent = `${month} ${dayOfMonth}, ${dateObj.getFullYear()}`;  // Contoh: "July 8, 2025";

    // Update hari yang aktif
    const dayElements = document.querySelectorAll('.calendar-day');
    dayElements.forEach((element, index) => {
        element.classList.remove('text-indigo-500', 'font-semibold');  // Reset styling
        if (index === dayOfWeek) {
            element.classList.add('text-indigo-500', 'font-semibold');  // Highlight current day
        }
    });

    // Update tanggal saat ini
    const currentDateElement = document.querySelector('.calendar-day-number');
    currentDateElement.textContent = dayOfMonth;
}

    function updateFailedAttempts() {
        $.get('/get_failed_attempts', function(data) {
            $('#failed_attempts').text(data.failed_attempts);
            $('#last_failed_time').text(data.last_failed_time ? data.last_failed_time : 'Tidak ada percobaan gagal');
        });
    }

    // Update setiap 10 detik
    setInterval(updateFailedAttempts, 10000);

// Perbarui waktu dan kalender setiap detik (1000ms)
setInterval(updateTime, 1000);
updateTime();  // Inisialisasi waktu saat pertama kali dimuat
