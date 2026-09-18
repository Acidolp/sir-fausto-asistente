import os, json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from openai import OpenAI

ROOT = Path(__file__).parent
KB = json.loads((ROOT / "knowledge.json").read_text(encoding="utf-8"))
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM = """Sos el asistente comercial de Sir Fausto LP.
Respondé en español argentino, de forma natural, breve y útil.
Usá exclusivamente la base de conocimiento proporcionada para productos, características, páginas y precios.
REGLAS IMPORTANTES:
- Los precios salen exclusivamente de la lista de precios incluida en la base.
- Nunca inventes ni confirmes stock. Siempre indicá 'Disponibilidad: consultar'.
- Si el cliente pregunta por un producto, incluí nombre, precio si está disponible, disponibilidad y catálogo/página cuando sea útil.
- Si falta un precio en la base, no lo inventes: indicá 'Precio: consultar'.
- Si el cliente saluda, respondé cordialmente y preguntá qué busca.
- Podés recomendar productos comparando lo que dice el catálogo, sin inventar propiedades.
- No diagnostiques enfermedades ni hagas afirmaciones médicas.
- Para pedidos, indicá que puede contactarse por Instagram @SirFausto.lp.
"""

def kb_text():
    return json.dumps(KB, ensure_ascii=False)

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json({}, 200)

    def do_POST(self):
        if urlparse(self.path).path != "/api/chat":
            self.send_json({"error":"Ruta no encontrada"}, 404); return
        try:
            n = int(self.headers.get("Content-Length","0"))
            data = json.loads(self.rfile.read(n))
            messages = data.get("messages", [])
            context = SYSTEM + "\n\nBASE DE CONOCIMIENTO:\n" + kb_text()
            msgs = [{"role":"system","content":context}] + messages[-12:]
            response = client.responses.create(model="gpt-5.6", input=msgs)
            self.send_json({"reply": response.output_text})
        except Exception as e:
            self.send_json({"error":"No se pudo procesar la consulta.","detail":str(e)}, 500)

    def do_GET(self):
        if urlparse(self.path).path in ("/", "/index.html"):
            html = (ROOT/"index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
        else:
            self.send_response(404)
            self.end_headers()
