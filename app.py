# -*- coding: utf-8 -*-
"""Сайт «Ульяновск — мой город»: Flask-сервер."""
import os
from flask import Flask, render_template, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR, static_folder=None)

C = "https://upload.wikimedia.org/wikipedia/commons/"

FLAG = C + "f/f3/Flag_of_Russia.svg"
ARMS = C + "f/f2/Coat_of_Arms_of_the_Russian_Federation.svg"
# ✅ АУДИО (ogg), а не видео
AUDIO = C + "2/2e/National_Anthem_of_Russia_%282000%29%2C_three_verses.ogg"

# ✅ Проверенные ссылки на фото с Commons
SIGHTS = [
    {"title": "Ленинский мемориал",
     "img": C + "thumb/1/15/Ulyanovsk_Leninskiy_memorial.jpg/960px-Ulyanovsk_Leninskiy_memorial.jpg",
     "q": "Ulyanovsk Leninskiy memorial",
     "text": "Мемориальный комплекс открыли в 1970 году к 100-летию со дня рождения В. И. Ленина. Внутри здания, во дворе, стоит дом, где родился Владимир Ленин. Это самое известное место города."},
    {"title": "Дом-музей В. И. Ленина",
     "img": C + "thumb/c/c2/%D0%94%D0%BE%D0%BC-%D0%BC%D1%83%D0%B7%D0%B5%D0%B9_%D0%9B%D0%B5%D0%BD%D0%B8%D0%BD%D0%B0_%281%29_%28%D0%A3%D0%BB%D1%8C%D1%8F%D0%BD%D0%BE%D0%B2%D1%81%D0%BA%29.jpg/960px-%D0%94%D0%BE%D0%BC-%D0%BC%D1%83%D0%B7%D0%B5%D0%B9_%D0%9B%D0%B5%D0%BD%D0%B8%D0%BD%D0%B0_%281%29_%28%D0%A3%D0%BB%D1%8C%D1%8F%D0%BD%D0%BE%D0%B2%D1%81%D0%BA%29.jpg",
     "q": "Lenin house museum Ulyanovsk",
     "text": "В этом деревянном доме семья Ульяновых жила в 1878–1887 годах. Сохранилась обстановка, как при маленьком Володе. Музей помогает представить жизнь семьи в Симбирске."},
    {"title": "Музей-заповедник «Родина В. И. Ленина»",
     "img": C + "thumb/1/11/%D0%94%D0%BE%D0%BC-%D0%BC%D1%83%D0%B7%D0%B5%D0%B9_%D0%9B%D0%B5%D0%BD%D0%B8%D0%BD%D0%B0_%D1%81%D0%BE_%D1%81%D1%82%D0%BE%D1%80%D0%BE%D0%BD%D1%8B_%D0%B4%D0%B2%D0%BE%D1%80%D0%B0.jpg/960px-%D0%94%D0%BE%D0%BC-%D0%BC%D1%83%D0%B7%D0%B5%D0%B9_%D0%9B%D0%B5%D0%BD%D0%B8%D0%BD%D0%B0_%D1%81%D0%BE_%D1%81%D1%82%D0%BE%D1%80%D0%BE%D0%BD%D1%8B_%D0%B4%D0%B2%D0%BE%D1%80%D0%B0.jpg",
     "q": "Ulyanovsk Lenin memorial house",
     "text": "Это целый музейный комплекс из десятков домов и выставок в центре города. Здесь можно узнать, как жили симбиряне в XIX веке. Территорию называют историческим сердцем Ульяновска."},
    {"title": "Краеведческий музей имени Гончарова",
     "img": C + "thumb/a/ad/Dom_Goncharov1.jpg/960px-Dom_Goncharov1.jpg",
     "q": "Goncharov museum Ulyanovsk",
     "text": "Музей рассказывает о природе и истории Ульяновской области. Он носит имя писателя Ивана Гончарова, автора романа «Обломов». Гончаров родился в Симбирске."},
    {"title": "Музей гражданской авиации",
     "img": C + "thumb/0/03/Tupolev_Tu-144%2C_Ulyanovsk_Aircraft_Museum.jpg/960px-Tupolev_Tu-144%2C_Ulyanovsk_Aircraft_Museum.jpg",
     "q": "Ulyanovsk aircraft museum",
     "text": "Здесь стоят настоящие самолёты и вертолёты, внутрь некоторых можно зайти. Ульяновск называют авиационной столицей России. Рядом находится училище лётчиков."},
    {"title": "Соборная площадь",
     "img": C + "thumb/2/2b/%D0%92%D1%8B%D1%81%D1%82%D0%B0%D0%B2%D0%BA%D0%B0_%D0%BD%D0%B0_%D0%A1%D0%BE%D0%B1%D0%BE%D1%80%D0%BD%D0%BE%D0%B9_%D0%BF%D0%BB%D0%BE%D1%89%D0%B0%D0%B4%D0%B8_%281%29.jpg/960px-%D0%92%D1%8B%D1%81%D1%82%D0%B0%D0%B2%D0%BA%D0%B0_%D0%BD%D0%B0_%D0%A1%D0%BE%D0%B1%D0%BE%D1%80%D0%BD%D0%BE%D0%B9_%D0%BF%D0%BB%D0%BE%D1%89%D0%B0%D0%B4%D0%B8_%281%29.jpg",
     "q": "Sobornaya square Ulyanovsk",
     "text": "Главная площадь города, где проходят праздники и выставки. Рядом стоит Спасо-Вознесенский собор. Это любимое место прогулок ульяновцев."},
    {"title": "Волжская набережная (бульвар Новый Венец)",
     "img": C + "thumb/d/da/The_city_of_Ulyanovsk%2C_Russia.jpg/960px-The_city_of_Ulyanovsk%2C_Russia.jpg",
     "q": "Novy Venets Ulyanovsk",
     "text": "Бульвар тянется по высокому берегу Волги. Отсюда открываются огромные виды на реку и заволжские дали. Вечером здесь гуляют семьи с детьми."},
    {"title": "Президентский мост",
     "img": C + "thumb/c/cd/%D0%9F%D1%80%D0%B5%D0%B7%D0%B8%D0%B4%D0%B5%D0%BD%D1%82%D1%81%D0%BA%D0%B8%D0%B9_%D0%BC%D0%BE%D1%81%D1%82_%D1%87%D0%B5%D1%80%D0%B5%D0%B7_%D1%80._%D0%92%D0%BE%D0%BB%D0%B3%D1%83.jpg/960px-%D0%9F%D1%80%D0%B5%D0%B7%D0%B8%D0%B4%D0%B5%D0%BD%D1%82%D1%81%D0%BA%D0%B8%D0%B9_%D0%BC%D0%BE%D1%81%D1%82_%D1%87%D0%B5%D1%80%D0%B5%D0%B7_%D1%80._%D0%92%D0%BE%D0%BB%D0%B3%D1%83.jpg",
     "q": "President bridge Ulyanovsk",
     "text": "Один из самых длинных мостов Европы, он перекинут через Волгу. Длина моста около 5,8 километра. Ночью его огни отражаются в воде."},
    {"title": "Памятник букве «Ё»",
     "img": C + "4/4e/Monument_%D0%811.jpg",
     "q": "Monument letter Yo Ulyanovsk",
     "text": "Гранитную букву открыли в 2005 году на бульваре Новый Венец, рядом с областной научной библиотекой. Она весит больше трёх тонн. Букву «ё» в печати одним из первых использовал писатель Николай Карамзин, уроженец Симбирской губернии."},
    {"title": "Ульяновский драматический театр",
     "img": C + "thumb/3/3f/Ulyanovsk_Spasskaya_zdanie_na_meste_teatra.jpg/960px-Ulyanovsk_Spasskaya_zdanie_na_meste_teatra.jpg",
     "q": "Ulyanovsk drama theatre",
     "text": "Один из старейших театров Поволжья, он работает с XIX века. На его сцене идут спектакли для взрослых и для детей. Здание стоит в самом центре города."},
]

ANTHEM = {
    "title": "Государственный гимн Российской Федерации",
    "authors": "Музыка А. Александрова, слова С. Михалкова",
    "audio": AUDIO,
    "flag": FLAG,
    "arms": ARMS,
    "verses": [
        "Россия — священная наша держава,\nРоссия — любимая наша страна.\nМогучая воля, великая слава —\nТвоё достоянье на все времена!",
        "От южных морей до полярного края\nРаскинулись наши леса и поля.\nОдна ты на свете! Одна ты такая —\nХранимая Богом родная земля!",
        "Широкий простор для мечты и для жизни\nГрядущие нам открывают года.\nНам силу даёт наша верность Отчизне.\nТак было, так есть и так будет всегда!",
    ],
    "chorus": "Славься, Отечество наше свободное,\nБратских народов союз вековой,\nПредками данная мудрость народная!\nСлавься, страна! Мы гордимся тобой!",
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/sights")
def api_sights():
    return jsonify(SIGHTS)

@app.route("/api/anthem")
def api_anthem():
    return jsonify(ANTHEM)

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Страница не найдена"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Ошибка сервера"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
