
### SCRIPT EJEMPLO BACKEND CON SERVIDOR WEBSOCKET
# En este script se implementa un servidor para la comunicación mediante websockets de 
# señales de los equipos de prácticas

# La comunicación entre el dispositivo de prácticas y el backend se realiza mediante websocket
# La comunicación entre el backend y el frontend se realiza mediante socket IO (websockets) 

# Para ejecutar la aplicación: uvicorn main:socket_app --host 0.0.0.0 --port 8002 --workers 1 --loop uvloop


import asyncio
import socketio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.responses import FileResponse
from starlette.requests import Request
import nats
import struct
import json
import time
import subprocess
import base64
from onvif import ONVIFCamera

from starlette.middleware.gzip import GZipMiddleware



NATS_SERVERS = []


#####################################################################################
# Crear servidor Socket.IO
#####################################################################################
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')


#####################################################################################
# Callbacks a los eventos de subcripción NATS
#####################################################################################
async def message_handler(msg):
    subject = msg.subject
    reply = msg.reply
    data =  struct.unpack("<ff",msg.data)
    print("Received a message on '{subject} {reply}': {data}".format(
        subject=subject, reply=reply, data=data))
    await sio.emit("dato_esp32", {"dato": data[0]})



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Nos conectamos al broker NATS
    NATS_SERVERS.append(await nats.connect("nats://demo.nats.io:4222"))
    sub = await NATS_SERVERS[0].subscribe("aeropendulo.esp32.y", cb=message_handler)
    yield 
    # Cuando acaba la aplicación el yield reanuda la ejecución aquí
    # Se desconecta del NATS
    await sub.unsubscribe()
    await NATS_SERVERS[0].drain()


# Crear aplicación FastAPI
app = FastAPI(lifespan=lifespan)

#####################################################################################
# Middleware que comprime las respuestas para que la integración backend-fronted
# sea más fluida
#####################################################################################
app.add_middleware(GZipMiddleware, minimum_size=1000)  # bytes

#####################################################################################
# Conectamos la app con el socketio
#####################################################################################
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


#####################################################################################
# Endpoints
#####################################################################################

@app.get("/", response_class=HTMLResponse, include_in_schema=True)
def root():
    return 'ok'



# #####################################################################################
# # Mensajes recibidos del frontend
# #####################################################################################

# @sio.event
# async def freq_change(sid, data):
#     print(f"[FRONTEND] Mensaje recibido: {data['value']}")
#     val = data['value'] if not isinstance(data['value'],(int,float)) else str(data['value'])
#     freq_event = {"freq":val}
#     conn = [conn for conn in esp32_websockets]
#     await conn[0].send(json.dumps(freq_event))
#     # emviar el dato recibido por websockets al ESP32


# @sio.event
# async def Tm_change(sid, data):
#     print(f"[FRONTEND] Mensaje recibido: {data['value']}")
#     freq_event = {"Tm":data['value']}
#     conn = [conn for conn in esp32_websockets]
#     await conn[0].send(json.dumps(freq_event))
#     # emviar el dato recibido por websockets al ESP32


# #####################################################################################
# ## Gestión de la conexión con el ESP32
# #####################################################################################

# # Guardar el estado del ESP32 (si necesitas enviarle datos)
# esp32_websockets = set()

# # Handler de mensajes WebSocket
# async def ws_esp32_handler(websocket):
#     print("ESP32 conectado")
#     esp32_websockets.add(websocket)
#     try:
#         async for message in websocket:
#             if isinstance(message,bytes):
#                 dataBloc = struct.unpack("<ff",message)
#                 print(f"[ESP32] → {time.time()}:{dataBloc}")
#                 await sio.emit("dato_esp32", {"dato": dataBloc[0]})
#     except websockets.exceptions.ConnectionClosedError:
#         print("ESP32 desconectado")
#     finally:
#         esp32_websockets.remove(websocket)

# # Iniciar WebSocket Server como tarea background
# @app.on_event("startup")
# async def start_ws_server():
#     async def serve_ws():
#         async with websockets.serve(ws_esp32_handler, "0.0.0.0", 8765) as server:
#             print("Servidor WebSocket corriendo en puerto 8765")
#             await server.serve_forever()  # Nunca termina

#     asyncio.create_task(serve_ws())


# # Transmisión de video en tiempo real
# # Lee RTSP y emite frames por socket.io

# IP   = "192.168.1.167"
# USER = "virtyremlab"
# PASS = "cam_aeropendulo"





# # Inicializa la cámara

# mycam = ONVIFCamera(IP, 2020, USER, PASS) # Descomentar para habilitar el control de la cámara.

# @app.get("/ptz")
# async def move_ptz(direction: str):
#     media = mycam.create_media_service()
#     ptz = mycam.create_ptz_service()

#     profile = media.GetProfiles()[0]

#     # Vector de movimiento (Pan, Tilt, Zoom)
#     if direction == "left":
#         velocity = {'x': -0.5, 'y': 0}
#     elif direction == "right":
#         velocity = {'x': 0.5, 'y': 0}
#     elif direction == "up":
#         velocity = {'x': 0, 'y': 0.5}
#     elif direction == "down":
#         velocity = {'x': 0, 'y': -0.5}
#     elif direction =="stop":
#         velocity = {'x': 0, 'y': 0}
#     else:
#         return {"error": "Dirección no soportada"}

#     ptz.Stop({'ProfileToken': profile.token})
#     if direction != "stop":
#         ptz.ContinuousMove({'ProfileToken': profile.token,
#                         'Velocity': {'PanTilt': velocity, 'Zoom': {'x': 0}}})
#     return {"status": f"Moviendo {direction}"}

# ## Conversión del video
# async def ffmpeg_stream():
#     cmd = [
#         "ffmpeg",
#         "-i", f"rtsp://{USER}:{PASS}@{IP}:554/stream1",
#         "-f", "mjpeg",
#         "-"
#     ]
#     process = await asyncio.create_subprocess_exec(
#         *cmd,
#         stdout=subprocess.PIPE
#     )

#     buffer = b""
#     while True:
#         chunk = await process.stdout.read(1024)
#         if not chunk:
#             break
#         buffer += chunk

#         # Busca SOI (Start of Image) y EOI (End of Image) markers
#         while b'\xff\xd8' in buffer and b'\xff\xd9' in buffer:
#             start = buffer.find(b'\xff\xd8')
#             end = buffer.find(b'\xff\xd9') + 2
#             jpg = buffer[start:end]
#             buffer = buffer[end:]
#             # Base64 y enviar
#             jpg_as_text = base64.b64encode(jpg).decode('utf-8')
#             await sio.emit("video_frame", jpg_as_text)

#     await process.wait()


# @app.on_event("startup")
# async def start_stream():
#     asyncio.create_task(ffmpeg_stream())

