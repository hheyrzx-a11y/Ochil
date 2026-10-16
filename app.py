import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from kayro_core import Asistente

app = Flask(__name__)
app.json.ensure_ascii = False
CORS(app)

bot = Asistente(memoria_path="memoria_correcciones.json")


@app.get("/")
def inicio():
    return jsonify({"estado": "ok", "servicio": "KAYRO IA v2"})


@app.route("/chat", methods=["GET", "POST"])
def chat():
    datos = request.get_json(silent=True) or {}
    mensaje = datos.get("mensaje") or datos.get("message") or request.args.get("q", "")
    return jsonify(bot.responder(str(mensaje)[:500]))


@app.route("/aprender", methods=["POST"])
def aprender():
    datos = request.get_json()
    pregunta = datos.get("pregunta")
    respuesta = datos.get("respuesta_correcta")
    if not pregunta or not respuesta:
        return jsonify({"error": "Faltan 'pregunta' o 'respuesta_correcta'"}), 400
    bot.aprender(pregunta, respuesta)
    return jsonify({"estado": "ok", "mensaje": "Corrección guardada."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
