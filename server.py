import os
import json
from pathlib import Path
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from openai import OpenAI


# ============================================================
# CONFIGURACIÓN
# ============================================================

ROOT = Path(__file__).parent

# Cargar base de conocimiento
knowledge_file = ROOT / "knowledge.json"

try:
    KB = json.loads(
        knowledge_file.read_text(encoding="utf-8")
    )
except Exception:
    KB = {}

# API de OpenAI
api_key = os.environ.get("OPENAI_API_KEY")

if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None


# ============================================================
# INSTRUCCIONES DEL ASISTENTE
# ============================================================

SYSTEM = """
Sos el asistente comercial oficial de Sir Fausto LP.

Respondé siempre en español argentino, de manera natural,
amable, breve y clara.

Tu función es ayudar a los clientes a elegir productos de
Sir Fausto LP para barba, cabello, styling, cuidado facial,
piel, afeitado y cuidado personal.

REGLAS IMPORTANTES:

1. Usá exclusivamente la base de conocimiento proporcionada
   para informar sobre los productos.

2. Los precios salen EXCLUSIVAMENTE de la lista de precios
   incluida en la base de conocimiento.

3. Nunca inventes un precio.

4. Nunca confirmes que un producto está en stock.

5. Para disponibilidad utilizá siempre:
   "Consultar disponibilidad".

6. Cuando recomiendes un producto, indicá:
   - Nombre del producto.
   - Para qué sirve.
   - Por qué puede ser adecuado para la necesidad del cliente.
   - Precio, solamente si existe en la base de conocimiento.
   - Fuente/catálogo y página cuando esté disponible.

7. Si el cliente pregunta por varios productos, podés
   compararlos utilizando únicamente la información disponible
   en la base de conocimiento.

8. Si el cliente saluda, respondé cordialmente.

   Ejemplo:
   "¡Hola! 👋 Bienvenido/a a Sir Fausto LP.
   ¿Qué estás buscando? Puedo ayudarte con productos para
   barba, cabello, styling, cuidado facial y más."

9. Si no encontrás información suficiente en la base de
   conocimiento, decilo claramente y no inventes información.

10. No hagas diagnósticos médicos ni afirmaciones médicas.

11. Para pedidos o consultas comerciales, podés indicar:
   Instagram: @SirFausto.lp

12. No utilices el sitio web sirfausto.ar como fuente de precios.

13. No inventes productos que no estén en la base.

14. Si el usuario pregunta por disponibilidad, respondé:
   "Consultar disponibilidad".

15. Mantené un tono comercial pero natural, evitando respuestas
   excesivamente largas.
"""


# ============================================================
# BASE DE CONOCIMIENTO
# ============================================================

def knowledge_text():
    return json.dumps(
        KB,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# SERVIDOR
# ============================================================

class Handler(BaseHTTPRequestHandler):

    # --------------------------------------------------------
    # RESPUESTAS JSON
    # --------------------------------------------------------

    def send_json(self, data, code=200):

        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(code)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(body)

    # --------------------------------------------------------
    # OPTIONS
    # --------------------------------------------------------

    def do_OPTIONS(self):

        self.send_response(200)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def do_GET(self):

        path = urlparse(self.path).path

        # Página principal
        if path in ("/", "/index.html"):

            try:

                html = (
                    ROOT / "index.html"
                ).read_bytes()

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8"
                )

                self.send_header(
                    "Content-Length",
                    str(len(html))
                )

                self.end_headers()

                self.wfile.write(html)

            except Exception as e:

                self.send_json(
                    {
                        "error": "No se pudo cargar index.html",
                        "detail": str(e)
                    },
                    500
                )

            return

        # Health check
        if path == "/health":

            self.send_json(
                {
                    "status": "ok",
                    "service": "Sir Fausto LP"
                }
            )

            return

        # Cualquier otra ruta
        self.send_json(
            {
                "error": "Ruta no encontrada"
            },
            404
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def do_POST(self):

        path = urlparse(self.path).path

        # Endpoint del chatbot
        if path != "/api/chat":

            self.send_json(
                {
                    "error": "Ruta no encontrada"
                },
                404
            )

            return

        # Verificar API key
        if client is None:

            self.send_json(
                {
                    "error": "OPENAI_API_KEY no está configurada en Render."
                },
                500
            )

            return

        try:

            # Cantidad de datos recibidos
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            # Leer datos
            raw_data = self.rfile.read(
                content_length
            )

            # Convertir JSON
            data = json.loads(
                raw_data.decode("utf-8")
            )

            # Mensajes enviados por el navegador
            messages = data.get(
                "messages",
                []
            )

            # Texto de la base de conocimiento
            context = knowledge_text()

            # Construir entrada para OpenAI
            input_messages = [
                {
                    "role": "system",
                    "content": SYSTEM
                },
                {
                    "role": "system",
                    "content":
                        "BASE DE CONOCIMIENTO DE SIR FAUSTO LP:\n\n"
                        + context
                }
            ]

            # Agregar conversación del usuario
            for message in messages:

                role = message.get(
                    "role",
                    "user"
                )

                content = message.get(
                    "content",
                    ""
                )

                if role not in (
                    "user",
                    "assistant"
                ):
                    continue

                input_messages.append(
                    {
                        "role": role,
                        "content": content
                    }
                )

            # Llamar a OpenAI
            response = client.responses.create(
                model="gpt-5.6",
                input=input_messages
            )

            # Obtener respuesta
            reply = response.output_text

            # Enviar respuesta
            self.send_json(
                {
                    "reply": reply
                }
            )

        except Exception as e:

            self.send_json(
                {
                    "error":
                        "No se pudo procesar la consulta.",
                    "detail": str(e)
                },
                500
            )


# ============================================================
# INICIO DEL SERVIDOR
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "8000"
        )
    )

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            port
        ),
        Handler
    )

    print(
        f"Servidor Sir Fausto LP iniciado en el puerto {port}"
    )

    server.serve_forever()
