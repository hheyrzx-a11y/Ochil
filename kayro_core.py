import os, re, json, math, random, unicodedata, torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# --- Carga del modelo ultra-ligero ---
MODELO_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
tokenizer = AutoTokenizer.from_pretrained(MODELO_ID)
modelo = AutoModelForCausalLM.from_pretrained(
    MODELO_ID,
    torch_dtype=torch.float16,
    device_map="auto",
    low_cpu_mem_usage=True
)
generador = pipeline(
    "text-generation",
    model=modelo,
    tokenizer=tokenizer,
    max_new_tokens=200,
    temperature=0.8,
    top_p=0.9,
    do_sample=True,
    repetition_penalty=1.1
)


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9\s\+\-\*\/\(\)\.]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ═══════════════════════════════════════════════════════════
#  🧮 CALCULADORA (usa Python real, no el modelo)
# ═══════════════════════════════════════════════════════════
def intentar_calculo(mensaje):
    texto = mensaje.lower()
    palabras_clave = ["cuanto es", "cuánto es", "calcula", "resultado de",
                      "resuelve", "suma", "resta", "multiplica", "divide",
                      "elevado", "raiz", "raíz", "cuanto vale", "+", "-", "*", "/", "^"]
    if not any(p in texto for p in palabras_clave):
        return None

    texto = texto.replace("cuanto es", "").replace("cuánto es", "")
    texto = texto.replace("cuanto vale", "").replace("calcula", "").replace("resuelve", "")
    texto = texto.replace("mas", "+").replace("más", "+")
    texto = texto.replace("menos", "-")
    texto = texto.replace("multiplicado por", "*").replace("por", "*")
    texto = texto.replace("dividido por", "/").replace("dividido entre", "/").replace("entre", "/")
    texto = texto.replace("elevado a", "**").replace("^", "**")
    texto = texto.replace("raiz de", "sqrt").replace("raíz de", "sqrt")
    texto = texto.replace("x", "*") if re.search(r"\d\s*x\s*\d", texto) else texto

    expresion = re.sub(r"[^0-9\+\-\*\/\(\)\.\s]", " ", texto)
    expresion = re.sub(r"\s+", " ", expresion).strip()

    if not expresion or not re.search(r"\d", expresion):
        return None

    try:
        if not re.fullmatch(r"[\d\s\+\-\*\/\(\)\.]+", expresion):
            return None
        resultado = eval(expresion, {"__builtins__": {}}, {})
        if isinstance(resultado, float) and resultado.is_integer():
            resultado = int(resultado)
        return f"🧮 El resultado es: **{resultado}**"
    except Exception:
        return None


def cargar_memoria(ruta="memoria_correcciones.json"):
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def guardar_memoria(memoria, ruta="memoria_correcciones.json"):
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════
#  🎭 SYSTEM PROMPT — Personalidad amigable de KAYRO
# ═══════════════════════════════════════════════════════════
SYSTEM_PROMPT = """Eres KAYRO, el asistente virtual de la app KAYRO STUDIO. Eres amigable, cercano, hablas en español casual como un amigo que ayuda.

SOBRE LA APP (lo más importante):
- KAYRO STUDIO sirve para PARCHAR videos y subirlos a TikTok sin que se traben o pierdan calidad.
- "Parchar" significa optimizar el video: funciona con cualquier resolución y cualquier peso.
- Flujo completo: 1️⃣ Inicia sesión con TikTok. 2️⃣ Ve a "Parchar" y parcha tu video. 3️⃣ Entra a "Studio" → "Abrir TikTok Studio". 4️⃣ Sube tu video. 5️⃣ ⚠️ Cambia la visibilidad a "Para todos".
- Recomendación: sube a 1080p, 60 fps y pocos MB para que TikTok no lo trabe.

CÓMO RESPONDER:
- Si te saludan ("hola", "qué tal", "hey", "buenas"): responde cálido y preséntate. Ejemplo: "¡Hola! 👋 Todo bien por aquí, ¿y tú? Soy KAYRO, tu asistente. ¿Te ayudo con algo de KAYRO STUDIO?"
- Si preguntan "¿cómo estás?", "¿qué haces?", "¿eres un bot?": responde natural, breve y con onda.
- Si escriben "jajaja", "xd", "lol": responde ligero y sigue la charla. Ejemplo: "😄 ¡Me alegra que te rías! ¿En qué te ayudo?"
- Si preguntan "¿para qué sirve la app?" o "¿cómo funciona?": explica KAYRO STUDIO en 2-3 frases claras.
- Si preguntan por parchar, Studio, visibilidad, calidad, lag o errores: da la respuesta específica.
- Si te piden una operación matemática: el sistema ya calculó el resultado, solo confírmalo brevemente.
- Si preguntan algo TOTALMENTE ajeno (recetas, política, tareas, programar): responde amable: "Jaja, de eso no sé mucho 🙈, pero si necesitas ayuda con KAYRO STUDIO o una suma, aquí estoy."

REGLAS:
- Responde SIEMPRE en español, breve (máx 3-4 frases).
- Sé cálido, usa emojis con moderación.
- Nunca inventes funciones que la app no tenga.
- Si no sabes algo de la app: "Eso mejor pregúntale a mi desarrollador, está trabajando en mejorarme 🛠️"
"""


class Asistente:
    def __init__(self, memoria_path="memoria_correcciones.json"):
        self.memoria = cargar_memoria(memoria_path)
        self.memoria_path = memoria_path

    def _buscar_en_memoria(self, mensaje):
        m = normalizar(mensaje)
        for item in self.memoria:
            if normalizar(item["pregunta"]) == m:
                return item["respuesta_correcta"]
        return None

    def aprender(self, pregunta_usuario, respuesta_correcta):
        for item in self.memoria:
            if normalizar(item["pregunta"]) == normalizar(pregunta_usuario):
                item["respuesta_correcta"] = respuesta_correcta
                guardar_memoria(self.memoria, self.memoria_path)
                return
        self.memoria.append({
            "pregunta": pregunta_usuario,
            "respuesta_correcta": respuesta_correcta
        })
        guardar_memoria(self.memoria, self.memoria_path)

    def responder(self, mensaje):
        if not normalizar(mensaje):
            return {"respuesta": "Escríbeme tu duda y te ayudo. 😊", "fuente": "vacio"}

        # 1. Memoria aprendida
        r = self._buscar_en_memoria(mensaje)
        if r:
            return {"respuesta": r, "fuente": "memoria"}

        # 2. Calculadora (Python real)
        calc = intentar_calculo(mensaje)
        if calc:
            return {"respuesta": calc, "fuente": "calculadora"}

        # 3. Modelo IA con personalidad
        mensajes = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": mensaje}
        ]
        prompt = tokenizer.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)
        salida = generador(prompt, max_new_tokens=200, do_sample=True)
        completa = salida[0]['generated_text']

        if "<|im_start|>assistant" in completa:
            final = completa.split("<|im_start|>assistant")[-1].replace("<|im_end|>", "").strip()
        else:
            final = completa.replace(prompt, "").strip()

        return {"respuesta": final, "fuente": "modelo"}
