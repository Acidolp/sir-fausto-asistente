import os
import json
from pathlib import Path
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


# ============================================================
# SIR FAUSTO LP - ASISTENTE IA
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_FILE = BASE_DIR / "knowledge.json"


# ============================================================
# CONFIGURACIÓN
# ============================================================

PORT = int(
    os.environ.get(
        "PORT",
        "10000"
    )
)

OPENAI_API_KEY = os.environ.get(
    "OPENAI_API_KEY"
)


# ============================================================
# CARGAR KNOWLEDGE
# ============================================================

def load_knowledge():

    try:

        with open(
            KNOWLEDGE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            "ERROR knowledge.json:",
            repr(error),
            flush=True
        )

        return {}


KNOWLEDGE = load_knowledge()


# ============================================================
# PROMPT
# ============================================================

SYSTEM_PROMPT = """
Sos el asistente virtual de Sir Fausto LP.

Ayudás a los clientes a elegir productos Sir Fausto para:

- Barba
- Cabello
- Styling
- Cuidado facial
- Cuidado personal

REGLAS IMPORTANTES:

1. Respondé siempre en español argentino.

2. Sé amable, claro, natural y comercial.

3. Utilizá la BASE DE CONOCIMIENTO proporcionada.

4. NO inventes productos.

5. NO inventes características.

6. NO inventes tamaños.

7. NO inventes precios.

8. Los precios deben salir EXCLUSIVAMENTE de la lista de
   precios incluida en la base de conocimiento.

9. Si un producto no tiene precio registrado,
   no inventes uno.

10. Si el cliente pregunta por stock o disponibilidad,
    respondé:
    "Consultar disponibilidad."

11. Nunca supongas que hay stock.

12. Cuando recomiendes un producto, indicá cuando sea posible:

    - Nombre del producto
    - Para qué sirve
    - Por qué puede servir para lo que busca
    - Precio
    - Catálogo y página

13. Si pregunta por varios productos, podés compararlos
    utilizando solamente la información disponible.

14. Si el cliente solamente saluda, respondé cordialmente.

    Ejemplo:

    "¡Hola! 👋 Bienvenido/a a Sir Fausto LP.
    ¿Qué estás buscando?
    Puedo ayudarte con productos para barba,
    cabello, styling o cuidado facial."

15. Si algo no está en la base de conocimiento,
    decí que no tenés ese dato.

16. No inventes promociones.

17. No inventes descuentos.

18. No inventes disponibilidad.

19. No hagas diagnósticos médicos.

20. No prometas resultados médicos.

21. Si el usuario consulta por piel, cabello o barba,
    orientá únicamente utilizando la información de los
    catálogos.

22. Instagram:
    @SirFausto.lp

23. No utilices sirfausto.ar como llamada a la acción.

24. Mantené las respuestas claras y relativamente cortas.

25. Podés utilizar emojis moderadamente.

26. El objetivo es ayudar al cliente a encontrar el producto
    adecuado de forma clara y confiable.
"""


# ============================================================
# KNOWLEDGE EN TEXTO
# ============================================================

def knowledge_text():

    try:

        return json.dumps(
            KNOWLEDGE,
            ensure_ascii=False,
            indent=2
        )

    except Exception as error:

        print(
            "ERROR convirtiendo knowledge:",
            repr(error),
            flush=True
        )

        return "{}"


# ============================================================
# HTTP HANDLER
# ============================================================

class Handler(BaseHTTPRequestHandler):

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    def send_json(
        self,
        data,
        status=200
    ):

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

        try:

            path = urlparse(
                self.path
            ).path

            # Página principal
            if path in (
                "/",
                "/index.html"
            ):

                index_file = (
                    BASE_DIR / "index.html"
                )

                if not index_file.exists():

                    self.send_json(
                        {
                            "error":
                                "No se encontró index.html"
                        },
                        404
                    )

                    return

                content = (
                    index_file.read_bytes()
                )

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

                self.wfile.write(
                    content
                )

                return

            # Health check
            if path == "/health":

                self.send_json(
                    {
                        "status": "ok",
                        "service":
                            "Sir Fausto LP",
                        "knowledge":
                            bool(KNOWLEDGE),
                        "api_key":
                            bool(OPENAI_API_KEY)
                    }
                )

                return

            # 404
            self.send_json(
                {
                    "error":
                        "Ruta no encontrada."
                },
                404
            )

        except Exception as error:

            print(
                "GET ERROR:",
                repr(error),
                flush=True
            )

            self.send_json(
                {
                    "error":
                        "Error interno."
                },
                500
            )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def do_POST(self):

        path = urlparse(
            self.path
        ).path

        # ----------------------------------------------------
        # API CHAT
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
        # API KEY
        # ----------------------------------------------------

        if not OPENAI_API_KEY:

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
            # IMPORTAR OPENAI SOLO CUANDO SE NECESITA
            # ------------------------------------------------

            from openai import OpenAI

            client = OpenAI(
                api_key=OPENAI_API_KEY
            )

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
                            "Consulta vacía."
                    },
                    400
                )

                return

            data = json.loads(
                body.decode("utf-8")
            )

            messages = data.get(
                "messages",
                []
            )

            if not isinstance(
                messages,
                list
            ):

                messages = []

            # Últimos 20 mensajes
            messages = messages[-20:]

            # ------------------------------------------------
            # CONSTRUIR INPUT
            # ------------------------------------------------

            input_messages = []

            input_messages.append(
                {
                    "role": "system",
                    "content":
                        SYSTEM_PROMPT
                        + "\n\n"
                        + "BASE DE CONOCIMIENTO:\n"
                        + knowledge_text()
                }
            )

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
            # VALIDAR
            # ------------------------------------------------

            if len(input_messages) < 2:

                self.send_json(
                    {
                        "error":
                            "No se recibió ningún mensaje."
                    },
                    400
                )

                return

            print(
                "CHAT: enviando consulta a OpenAI...",
                flush=True
            )

            # ------------------------------------------------
            # OPENAI RESPONSES API
            # ------------------------------------------------

            response = client.responses.create(

                model="gpt-5.6",

                input=input_messages
            )

            answer = response.output_text

            if not answer:

                answer = (
                    "No pude generar una respuesta "
                    "en este momento."
                )

            print(
                "CHAT: respuesta recibida.",
                flush=True
            )

            self.send_json(
                {
                    "answer":
                        answer
                },
                200
            )

        except Exception as error:

            print(
                "CHAT ERROR:",
                repr(error),
                flush=True
            )

            self.send_json(
                {
                    "error":
                        "No se pudo procesar la consulta.",
                    "detail":
                        str(error)
                },
                500
            )


# ============================================================
# ARRANQUE DEL SERVIDOR
# ============================================================

if __name__ == "__main__":

    print(
        "========================================",
        flush=True
    )

    print(
        "SIR FAUSTO LP - ASISTENTE IA",
        flush=True
    )

    print(
        "========================================",
        flush=True
    )

    print(
        f"Puerto Render: {PORT}",
        flush=True
    )

    print(
        f"Knowledge cargado: {bool(KNOWLEDGE)}",
        flush=True
    )

    print(
        f"API Key configurada: {bool(OPENAI_API_KEY)}",
        flush=True
    )

    print(
        "Iniciando servidor...",
        flush=True
    )

    # --------------------------------------------------------
    # ABRIR PUERTO INMEDIATAMENTE
    # --------------------------------------------------------

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            PORT
        ),
        Handler
    )

    print(
        f"Servidor escuchando en 0.0.0.0:{PORT}",
        flush=True
    )

    server.serve_forever()
