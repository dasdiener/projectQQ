from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# Функция для быстрого подключения к созданной вами базе данных
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Это позволит читать данные по именам колонок
    return conn

# Главная страница (запускает index.html, который сейчас делает ваш HTML-разработчик)
@app.route("/")
def home():
    return render_template("index.html")

# Страница создания заявки
@app.route("/create")
def create_page():
    conn = get_db_connection()
    # Вытаскиваем список кабинетов из базы, чтобы показать их в выпадающем списке
    locations = conn.execute('SELECT * FROM locations').fetchall()
    conn.close()
    return render_template("create.html", locations=locations)

if __name__ == "__main__":
    app.run(debug=True)
