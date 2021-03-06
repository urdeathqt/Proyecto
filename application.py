from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
import requests
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///gaming.db")

@app.route("/")
@login_required
def index():

    publis = []

    juegos = db.execute(
            "SELECT id_api FROM publicaciones")

    for juego in juegos:
        publis.append(requests.get(f"https://api.rawg.io/api/games/{juego['id_api']}?key=0650e803ab5149dbb7d94030438d7d7a").json())


    return render_template("index.html", publis=publis)

@app.route("/buscar", methods=["GET", "POST"])
@login_required
def buscar():
    if request.method == "POST":
        if not request.form.get("juego"):
            flash("Ingrese un nombre de juego para buscar")

            return render_template("buscar.html")
        else:
            nombre = request.form.get("juego")
            juegos = db.execute(f"SELECT * FROM publicaciones WHERE nombre like '%{nombre}%'")
            busquedas = []

            for juego in juegos:

                busquedas.append(requests.get(f"https://api.rawg.io/api/games/{juego['id_api']}?key=0650e803ab5149dbb7d94030438d7d7a").json())

            return render_template("buscar.html", busquedas=busquedas)

    else:
        return render_template("buscar.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Debe ingresar un nombre de usuario")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Debe ingresar una contrase??a")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM usuarios WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["contrase??a"], request.form.get("password")):
            flash("invalid username and/or password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect(url_for("index"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/mostrarinfo/<id>", methods=["GET", "POST"])
@login_required
def mostrarinfo(id):

    id_public = db.execute("SELECT id FROM publicaciones WHERE id_api = :id", id=id)[0]

    if request.method == "GET":
        consul = db.execute ("""SELECT username, comentario, fecha FROM comentarios as c
            inner join usuarios as u
            on c.id_usuario = u.id
            WHERE c.id_publicacion = :id_publicacion""", id_publicacion=id_public["id"])

        publi = requests.get(f"https://api.rawg.io/api/games/{id}?key=0650e803ab5149dbb7d94030438d7d7a").json()

        return render_template("mostrarinfo.html", publi=publi, consul=consul)

    if request.method == "POST":

        db.execute("INSERT INTO comentarios (comentario, id_usuario, id_publicacion) VALUES (:comentario, :id_usuario, :id_publicacion)", comentario=request.form.get("comentario"), id_usuario=session["user_id"], id_publicacion=id_public["id"])

        return redirect(id)

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect(url_for("index"))

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        if not request.form.get("username"):
            flash("Usted debe ingresar un usuario")
            return render_template("register.html")

        elif not request.form.get("password"):
            flash("Usted debe ingresar una contrase??a")
            return render_template("register.html")

        elif not request.form.get("confirmation"):
            flash("Debe proporcionar la contrase??a de confirmacion")
            return render_template("register.html")

        if not request.form.get("password") == request.form.get("confirmation"):
            flash("Las contrase??as no son las mismas")
            return render_template("register.html")

        # Consulta en la base de datos para nombre de usuario
        rows = db.execute("SELECT * FROM usuarios WHERE username = :username",
                          username=request.form.get("username"))

        # Confirmar que el usuario no exista
        if len(rows) != 0:
            flash("Usuario Existente")
            return render_template("register.html")

        hash = generate_password_hash(request.form.get("password"))

        new_user_id = db.execute("INSERT INTO usuarios (username, contrase??a) VALUES (:username, :hash)",
                   username=request.form.get("username"), hash=hash)

        session["user_id"] = new_user_id

        flash("Registrado!")

        return redirect(url_for("index"))

    else:
        return render_template("register.html")

@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    """"Cambiar contrase??a"""

    if request.method == "POST":

        if not request.form.get("oldpassword"):
            flash("Ingrese su contrase??a")
            return render_template("change.html")

        if not request.form.get("newpassword"):
            flash("Ingrese una nueva contrase??a")
            return render_template("change.html")

        if not request.form.get("confirmation"):
            flash("Confirme la contrase??a")
            return render_template("change.html")

        if not request.form.get("newpassword") == request.form.get("confirmation"):
            flash("Las contrase??as no coinciden")
            return render_template("change.html")

        userid = session["user_id"]

        rows = db.execute("SELECT * FROM usuarios WHERE id = :id",
                          id=userid)

        if not check_password_hash(rows[0]["contrase??a"], request.form.get("oldpassword")):
            flash("Contrase??a actual incorrecta")
            return render_template("change.html")

        if check_password_hash(rows[0]["contrase??a"], request.form.get("newpassword")):
            flash("La contrase??a nueva no puede ser la misma")
            return render_template("change.html")

        hashpassword = generate_password_hash(request.form.get("newpassword"))

        db.execute("UPDATE usuarios SET contrase??a = :hashpass WHERE id = :id",
                   hashpass=hashpassword, id=userid)

        flash("Contrase??a cambiada")
        return redirect("/")

    else:
        return render_template("change.html")


@app.route("/agregarjuego", methods=["GET", "POST"])
@login_required
def agregarjuego():

    if request.method == "POST":
        nom_juego = request.form.get("juego")
        nom_juego = nom_juego.strip()
        juego = " "

        for letra in nom_juego:
            if letra == " ":
                juego += "-"
            else:
                juego += letra

        juego = juego.strip()

        juegojson = requests.get(f"https://api.rawg.io/api/games/{juego}?key=0650e803ab5149dbb7d94030438d7d7a").json()
        nombre = juegojson.get('name')
        id_api = juegojson.get('id')

        if nombre == None:
            flash(f"No se encontr?? el juego con el nombre: {nom_juego}", "error")
            return render_template("agregarjuego.html")

        else:
            rows = db.execute("SELECT * FROM publicaciones WHERE nombre = :nombre", nombre=nombre)

            # Confirmar que el usuario no exista
            if len(rows) != 0:
                flash("Nombre ya existe", "error")
                return render_template("agregarjuego.html")

            db.execute("INSERT INTO publicaciones (nombre, id_api) VALUES (:nombre, :id_api)", nombre=nombre, id_api=id_api)
            flash("Nombre agregado", "exito")
            return redirect("/")

    else:
        return render_template("agregarjuego.html")



