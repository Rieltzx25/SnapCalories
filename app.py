import os
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Konfigurasi database SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///food_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model database untuk histori makanan
class FoodHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# Fungsi untuk memuat data nutrisi dari file CSV
def load_nutrition_data():
    nutrition_dict = {}
    try:
        # Pastikan file CSV berada di direktori yang sama dengan app.py atau sesuaikan path-nya
        df = pd.read_csv("Food_and_Calories_Sheet1.csv")
        # Asumsikan kolom: FoodName, Calories
        for index, row in df.iterrows():
            nutrition_dict[row['FoodName'].strip()] = int(row['Calories'])
    except Exception as e:
        print("Error loading CSV:", e)
    return nutrition_dict

nutrition_data = load_nutrition_data()

# Fungsi dummy untuk mengklasifikasikan gambar
# Mengembalikan indeks acak antara 0 dan 4
def classify_image(file_path):
    # Di sini seharusnya Anda memuat model AI (misalnya Keras/TensorFlow) dan melakukan inferensi
    # Untuk contoh, kita cukup kembalikan nilai acak
    return random.randint(0, 4)

# Mapping indeks ke nama makanan
def get_food_name_from_index(index):
    food_names = ["Nasi Goreng", "Mie Goreng", "Sate Ayam", "Gado-Gado", "Bakso"]
    if 0 <= index < len(food_names):
        return food_names[index]
    return "Unknown Food"

# Route: Home (form perhitungan kalori harian)
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            weight = float(request.form["weight"])
            height = float(request.form["height"])
            age = float(request.form["age"])
            # Rumus Harris-Benedict untuk pria: BMR = 66 + (13.7 x berat) + (5 x tinggi) - (6.8 x umur)
            bmr = 66 + (13.7 * weight) + (5 * height) - (6.8 * age)
            return render_template("calculate.html", bmr=int(bmr))
        except Exception as e:
            flash("Masukkan data yang valid!")
            return redirect(url_for("index"))
    return render_template("index.html")

# Konfigurasi folder upload
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg", "gif"])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route: Upload foto makanan dan proses klasifikasi
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            flash("Tidak ada file yang diupload")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("File tidak dipilih")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            # Lakukan inferensi menggunakan fungsi dummy
            predicted_index = classify_image(file_path)
            food_name = get_food_name_from_index(predicted_index)
            # Ambil kalori dari data CSV; jika tidak ada, default 500
            calories = nutrition_data.get(food_name, 500)
            # Simpan histori makanan ke database
            new_entry = FoodHistory(food_name=food_name, calories=calories)
            db.session.add(new_entry)
            db.session.commit()
            return render_template("upload_result.html", food_name=food_name, calories=calories)
    return render_template("upload.html")

# Route: Menampilkan histori makanan
@app.route("/history")
def history():
    all_history = FoodHistory.query.order_by(FoodHistory.date.desc()).all()
    return render_template("history.html", history=all_history)

# Route: Menampilkan rekomendasi pola makan berdasarkan rata-rata kalori
@app.route("/recommendation")
def recommendation():
    all_history = FoodHistory.query.all()
    if all_history:
        avg_calories = sum(entry.calories for entry in all_history) / len(all_history)
        if avg_calories > 2200:
            rec = "Asupan kalori cenderung berlebih. Cobalah kurangi porsi dan tambah sayuran."
        elif avg_calories < 1800:
            rec = "Asupan kalori Anda rendah. Pastikan mendapatkan nutrisi yang cukup."
        else:
            rec = "Pola makan Anda cukup seimbang. Pertahankan variasi nutrisi."
    else:
        avg_calories = 0
        rec = "Belum ada data. Silakan upload gambar makanan untuk memulai."
    return render_template("recommendation.html", avg_calories=int(avg_calories), recommendation=rec)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Buat tabel database jika belum ada
    app.run(debug=True)
