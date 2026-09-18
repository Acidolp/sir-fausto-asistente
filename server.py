import os
import json
from pathlib import Path
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from openai import OpenAI


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

KNOWLEDGE_FILE = BASE_DIR / "knowledge.json"


# ============================================================
# CARGAR BASE DE CONOCIMIENTO
# ============================================================

try:
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        KNOWLEDGE = json.load(f)

    print("Base de conocimiento cargada correctamente.")

except Exception as e:
    print("ERROR CARGANDO knowledge.json:", repr(e))
    KNOWLEDGE = {}


# ============================================================
# OPENAI
# ============================================================

API_KEY = os.environ.get("OPENAI_API_KEY")

if not API_KEY:
    print("ADVERTENCIA: OPENAI_API_KEY no está configurada.")

client = OpenAI(api_key=API_KEY) if API_KEY else None


# ============================================================
# PROMPT DEL ASISTENTE
# ============================================================

SYSTEM_PROMPT = """
Sos el asistente virtual de Sir Fausto LP.

Tu función es ayudar a los clientes a elegir productos Sir Fausto
para barba, cabello, styling, cuidado facial y cuidado personal.

REGLAS IMPORTANTES:

1. Respondé siempre en español argentino, de manera clara,
   amable, natural y comercial.

2. Utilizá principalmente la información contenida en la base
   de conocimiento proporcionada.

3. NO inventes productos, características, tamaños, precios,
   promociones ni beneficios.

4. Los PRECIOS deben salir exclusivamente de la lista de precios
   proporcionada en la base de conocimiento.

5. Si el cliente pregunta si un producto está disponible,
   NO supongas que hay stock.

   Respondé:
   "Consultar disponibilidad."

6. Cuando recomiendes un producto, indicá cuando corresponda:

   - Nombre del producto.
   - Para qué sirve.
   - Por qué puede ser adecuado para lo que busca.
   - Precio.
   - Catálogo y página.

7. Si el precio no está disponible en la base de conocimiento,
   no inventes uno.

8. Si el cliente pregunta por varios productos, podés
   compararlos de manera descriptiva.

9. Si el cliente solamente saluda, respondé cordialmente.

   Ejemplo:

   "¡Hola! 👋 Bienvenido/a a Sir Fausto LP.
   ¿Qué estás buscando?
   Puedo ayudarte con productos para barba,
   cabello, styling o cuidado facial."

10. Si el cliente describe un problema de piel, cabello o barba,
    orientá únicamente según la información disponible en los
    catálogos.

11. No realices diagnósticos médicos ni prometas resultados
    médicos.

12. Si no encontrás la información solicitada en la base de
    conocimiento, decí claramente que no tenés ese dato.

13. Instagram oficial:

    @SirFausto.lp

14. No utilices sirfausto.ar como llamada a la acción.

15. No inventes disponibilidad.

16. Mantené las respuestas relativamente cortas y fáciles
    de leer desde un celular.

17. Cuando sea útil, podés utilizar emojis de forma moderada.

18. El objetivo es ayudar al cliente a encontrar el producto
    adecuado de manera clara y confiable.
"""


# ============================================================
# BASE DE CONOCIMIENTO EN TEXTO
# ============================================================

def get_knowledge_text():

    try:

        return json.dumps(
            KNOWLEDGE,
            ensure_ascii=False,
            indent=2
        )

    except Exception as e:

        print(
            "ERROR CONVIRTIENDO KNOWLEDGE:",
            repr(e)
        )

        return "{}"


# ============================================================
# SERVIDOR
# ============================================================

class Handler(BaseHTTPRequestHandler):

    # ========================================================
    # RESPUESTA JSON
    # ========================================================

    def send_json(self, data, status=200):

        try:

            body = json.dumps(
                data,
                ensure_ascii=False
            ).encode("utf-8")

            self.send_response(status)

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(body))
            )

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type"
            )

            self.send_header(
                "Access-Control-Allow-Methods",
                "GET, POST, OPTIONS"
            )

            self.end_headers()

            self.wfile.write(body)

        except Exception as e:

            print(
                "ERROR EN send_json:",
                repr(e)
            )

    # ========================================================
    # OPTIONS
    # ========================================================

    def do_OPTIONS(self):

        self.send_response(204)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.end_headers()

    # ========================================================
    # GET
    # ========================================================

    def do_GET(self):

        try:

            path = urlparse(self.path).path

            # ------------------------------------------------
            # PÁGINA PRINCIPAL
            # ------------------------------------------------

            if path in ("/", "/index.html"):

                index_file = BASE_DIR / "index.html"

                if not index_file.exists():

                    self.send_json(
                        {
                            "error":
                                "No se encontró index.html"
                        },
                        404
                    )

                    return

                content = index_file.read_bytes()

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8"
                )

                self.send_header(
                    "Content-Length",
                    str(len(content))
                )

                self.end_headers()

                self.wfile.write(content)

                return

            # ------------------------------------------------
            # HEALTH CHECK
            # ------------------------------------------------

            if path == "/health":

                self.send_json(
                    {
                        "status": "ok",
                        "service": "Sir Fausto LP",
                        "openai_configured":
                            bool(client)
                    }
                )

                return

            # ------------------------------------------------
            # 404
            # ------------------------------------------------

            self.send_json(
                {
                    "error": "Ruta no encontrada."
                },
                404
            )

        except Exception as e:

            print(
                "GET ERROR:",
                repr(e)
            )

            self.send_json(
                {
                    "error":
                        "Error interno del servidor.",
                    "detail":
                        str(e)
                },
                500
            )

    # ========================================================
    # POST
    # ========================================================

    def do_POST(self):

        path = urlparse(self.path).path

        # ----------------------------------------------------
        # VERIFICAR RUTA
        # ----------------------------------------------------

        if path != "/api/chat":

            self.send_json(
                {
                    "error":
                        "Ruta no encontrada."
                },
                404
            )

            return

        # ----------------------------------------------------
        # VERIFICAR OPENAI
        # ----------------------------------------------------

        if not client:

            self.send_json(
                {
                    "error":
                        "OPENAI_API_KEY no está configurada."
                },
                500
            )

            return

        try:

            # ------------------------------------------------
            # LEER REQUEST
            # ------------------------------------------------

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            body = self.rfile.read(
                content_length
            )

            if not body:

                self.send_json(
                    {
                        "error":
                            "La consulta está vacía."
                    },
                    400
                )

                return

            data = json.loads(
                body.decode("utf-8")
            )

            # ------------------------------------------------
            # MENSAJES
            # ------------------------------------------------

            messages = data.get(
                "messages",
                []
            )

            if not isinstance(
                messages,
                list
            ):

                messages = []

            # Nos quedamos con los últimos 20 mensajes.

            messages = messages[-20:]

            # ------------------------------------------------
            # CREAR INPUT
            # ------------------------------------------------

            input_messages = []

            knowledge = get_knowledge_text()

            system_content = (
                SYSTEM_PROMPT
                + "\n\n"
                + "BASE DE CONOCIMIENTO:\n"
                + knowledge
            )

            input_messages.append(
                {
                    "role": "system",
                    "content": system_content
                }
            )

            # ------------------------------------------------
            # AGREGAR HISTORIAL
            # ------------------------------------------------

            for message in messages:

                if not isinstance(
                    message,
                    dict
                ):
                    continue

                role = message.get(
                    "role"
                )

                content = message.get(
                    "content"
                )

                if role not in (
                    "user",
                    "assistant"
                ):
                    continue

                if not isinstance(
                    content,
                    str
                ):
                    continue

                content = content.strip()

                if not content:
                    continue

                input_messages.append(
                    {
                        "role": role,
                        "content": content
                    }
                )

            # ------------------------------------------------
            # VERIFICAR CONSULTA
            # ------------------------------------------------

            if len(input_messages) < 2:

                self.send_json(
                    {
                        "error":
                            "No se recibió ninguna consulta."
                    },
                    400
                )

                return

            # ------------------------------------------------
            # LLAMADA A OPENAI
            # ------------------------------------------------

            print(
                "Enviando consulta a OpenAI..."
            )

            response = client.responses.create(

                model="gpt-5.6",

                input=input_messages
            )

            # ------------------------------------------------
            # RESPUESTA
            # ------------------------------------------------

            answer = response.output_text

            if not answer:

                answer = (
                    "No pude generar una respuesta "
                    "en este momento."
                )

            print(
                "Respuesta de OpenAI recibida correctamente."
            )

            # ------------------------------------------------
            # DEVOLVER AL FRONTEND
            # ------------------------------------------------

            self.send_json(
                {
                    "answer": answer
                },
                200
            )

        # ----------------------------------------------------
        # ERROR
        # ----------------------------------------------------

        except Exception as e:

            print(
                "CHAT ERROR:",
                repr(e)
            )

            self.send_json(
                {
                    "error":
                        "No se pudo procesar la consulta.",
                    "detail":
                        str(e)
                },
                500
            )


# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    print(
        "========================================"
    )

    print(
        "   SIR FAUSTO LP - ASISTENTE IA"
    )

    print(
        "========================================"
    )

    print(
        f"Puerto: {port}"
    )

    print(
        f"OpenAI configurado: {bool(client)}"
    )

    print(
        f"Knowledge cargado: {bool(KNOWLEDGE)}"
    )

    print(
        "========================================"
    )

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print(
        "Servidor iniciado correctamente."
    )

    server.serve_forever()
