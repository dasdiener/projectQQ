from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Служба УПК готова к запуску! Тимлид на связи."

if __name__ == "__main__":
    app.run(debug=True)
 