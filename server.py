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

with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
    KNOWLEDGE = json.load(f)


API_KEY = os.environ.get("OPENAI_API_KEY")

if not API_KEY:
    print("ADVERTENCIA: No se encontró OPENAI_API_KEY.")

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
   amable, natural y comercial, pero sin ser insistente.

2. Usá principalmente la información contenida en la base de
   conocimiento proporcionada.

3. NO inventes productos, características, tamaños, precios,
   promociones ni beneficios que no estén en la información.

4. Los PRECIOS deben salir exclusivamente de la lista de precios
   proporcionada en la base de conocimiento.

5. Si el cliente pregunta si un producto está disponible,
   NO supongas que hay stock.
   Respondé:
   "Consultar disponibilidad."

6. Cuando recomiendes un producto, indicá:
   - Nombre del producto.
   - Para qué sirve.
   - Por qué puede ser adecuado para lo que busca el cliente.
   - Precio, solamente si está disponible en la lista de precios.
   - Fuente: catálogo y página cuando esté disponible.

7. Si el usuario pregunta por varios productos, podés compararlos
   de manera descriptiva, sin inventar características.

8. Si la consulta no está relacionada con Sir Fausto,
   respondé brevemente y tratá de volver al tema de productos.

9. No hagas diagnósticos médicos ni prometas resultados médicos.

10. Si el cliente describe un problema de piel, cabello o barba,
    podés orientar sobre los productos según la información del
    catálogo, pero aclarando que no reemplaza la consulta con
    un profesional cuando corresponda.

11. Si el cliente solamente saluda, respondé de forma cordial.
    Ejemplo:
    "¡Hola! 👋 Bienvenido/a a Sir Fausto LP.
    ¿Qué estás buscando? Puedo ayudarte con productos para barba,
    cabello, styling o cuidado facial."

12. Instagram oficial para contacto:
    @SirFausto.lp

13. No incluyas enlaces a sirfausto.ar como llamada a la acción.
    Cuando corresponda, invitá a seguir o contactar mediante
    Instagram @SirFausto.lp.

14. No inventes disponibilidad.

15. Si no encontrás la respuesta en la base de conocimiento,
    decí claramente que no tenés ese dato y sugerí consultar
    directamente con Sir Fausto LP.

Tu objetivo es brindar respuestas útiles, concretas y confiables.
"""


# ============================================================
# BASE DE CONOCIMIENTO
# ============================================================

def knowledge_text():
    """
    Convierte knowledge.json en texto para que el modelo
    pueda utilizar la información de los catálogos y precios.
    """

    return json.dumps(
        KNOWLEDGE,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# HANDLER HTTP
# ============================================================

class Handler(BaseHTTPRequestHandler):

    # --------------------------------------------------------
    # RESPUESTAS JSON
    # --------------------------------------------------------

    def send_json(self, data, status=200):

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

    # --------------------------------------------------------
    # OPTIONS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def do_GET(self):

        # Quitamos parámetros como:
        # ?utm_source=chatgpt.com

        path = urlparse(self.path).path

        # Página principal

        if path in ("/", "/index.html"):

            index_file = BASE_DIR / "index.html"

            if not index_file.exists():

                self.send_json(
                    {
                        "error": "No se encontró index.html"
                    },
                    404
                )

                return

            try:

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

            except Exception as e:

                print(
                    "INDEX ERROR:",
                    repr(e)
                )

                self.send_json(
                    {
                        "error": "No se pudo cargar la página."
                    },
                    500
                )

            return

        # ----------------------------------------------------
        # HEALTH CHECK
        # ----------------------------------------------------

        if path == "/health":

            self.send_json(
                {
                    "status": "ok",
                    "service": "Sir Fausto LP"
                }
            )

            return

        # ----------------------------------------------------
        # 404
        # ----------------------------------------------------

        self.send_json(
            {
                "error": "Ruta no encontrada."
            },
            404
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def do_POST(self):

        path = urlparse(self.path).path

        # ----------------------------------------------------
        # API CHAT
        # ----------------------------------------------------

        if path != "/api/chat":

            self.send_json(
                {
                    "error": "Ruta no encontrada."
                },
                404
            )

            return

        # ----------------------------------------------------
        # VERIFICAR API KEY
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
            # LEER BODY
            # ------------------------------------------------

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(
                content_length
            )

            data = json.loads(
                body.decode("utf-8")
            )

            # ------------------------------------------------
            # OBTENER MENSAJES
            # ------------------------------------------------

            messages = data.get(
                "messages",
                []
            )

            # ------------------------------------------------
            # LIMITAR HISTORIAL
            # ------------------------------------------------

            if not isinstance(
                messages,
                list
            ):

                messages = []

            messages = messages[-20:]

            # ------------------------------------------------
            # CONSTRUIR INPUT
            # ------------------------------------------------

            input_messages = []

            # Mensaje del sistema

            input_messages.append(
                {
                    "role": "system",
                    "content":
                        SYSTEM_PROMPT
                        + "\n\nBASE DE CONOCIMIENTO:\n"
                        + knowledge_text()
                }
            )

            # Mensajes del usuario

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

                if not content.strip():
                    continue

                input_messages.append(
                    {
                        "role": role,
                        "content": content
                    }
                )

            # ------------------------------------------------
            # VERIFICAR QUE HAYA CONSULTA
            # ------------------------------------------------

            if len(input_messages) <= 1:

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

            response = client.responses.create(

                model="gpt-5.6",

                input=input_messages
            )

            # ------------------------------------------------
            # OBTENER RESPUESTA
            # ------------------------------------------------

            answer = response.output_text

            if not answer:

                answer = (
                    "No pude generar una respuesta "
                    "en este momento."
                )

            # ------------------------------------------------
            # DEVOLVER RESPUESTA
            # ------------------------------------------------

            self.send_json(
                {
                    "answer": answer
                }
            )

        # ----------------------------------------------------
        # ERROR
        # ----------------------------------------------------

                except Exception as e:

            print("CHAT ERROR:", repr(e))

            self.send_json(
                {
                    "error":
                        "No se pudo procesar la consulta.",
                    "detail": str(e)
                },
                500
            )


# ============================================================
# SERVIDOR
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print(
        f"Sir Fausto LP funcionando en puerto {port}"
    )

    server.serve_forever()
