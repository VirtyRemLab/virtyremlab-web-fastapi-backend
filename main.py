
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
ESP_AEROPENDULO_MSG_LENGH_FLOATS = 10




#TODO: Sacar la configuración de la comunicación a un archivo externo que lo compartan
# todas las imágenes de docker
AEROPENDULO_COMS_CONFIG = {
    "lenght":11,
    "model":{ "mode": "estado del sistema [STANDBY, READY,TEST, PID, ALARM]",
             "yk": "salida del sistema",
             "rk": "Referencia",
             "uk": "Acción de control",
             "ek": "Error del sistema",
             "M1": "Vel del motor 1",
             "M2": "Vel del motor 2",
             "vel_man": "Consigna para la velocidad manual",
             "Kp": "Consigna para la ganancia proporcional del regulador PID",
             "Ki": "Consigna para la ganancia integral del regulador PID",
             "Kd": "Consigna para la ganancia diferencial del regulador PID"
    },
    "interface":{"event": "mandar eventos al ESP enum EVENTS {NONE:0,POWERON:1,POWEROFF:2,START_PID:3,START_TEST:4,STOP:4,RESET:5,FAULT:6",
                 "vel_man": "Cambiar la vel manual",
                 "Kp":"Cambiar la Kp del sistema",
                 "Ki":"Cambiar la Ki del sistema",
                 "Kd":"Cambiar la Kd del sistema"}

}

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
    data =  struct.unpack("<f",msg.data)
    # print("Received a message on '{subject} {reply}': {data[0]}".format(
    #     subject=subject, reply=reply, data=data))
    #await sio.emit("dato_esp32", {"dato": data[1]})

async def message_state(msg):
    subject = msg.subject
    reply = msg.reply
    data_tuple =  struct.unpack("<"+"f"*AEROPENDULO_COMS_CONFIG["lenght"],msg.data)
    print("Received a message on '{subject} {reply}': {data}".format(
        subject=subject, reply=reply, data=data_tuple))
    await sio.emit("aeropendulo_state", dict(zip(AEROPENDULO_COMS_CONFIG["model"].keys(),data_tuple)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Nos conectamos al broker NATS
    NATS_SERVERS.append(await nats.connect("nats://localhost:4222"))
    #sub = 
    subs = [await NATS_SERVERS[0].subscribe("aeropendulo.esp32.state", cb=message_state)]
    yield 
    # Cuando acaba la aplicación el yield reanuda la ejecución aquí
    # Se desconecta del NATS
    for sub in subs:
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

@sio.event
async def freq_change(sid, data):
    print(f"[FRONTEND] Mensaje recibido: {data}")
    await NATS_SERVERS[0].publish("aeropendulo.esp32.freq",struct.pack("f",data))
    # val = data['value'] if not isinstance(data['value'],(int,float)) else str(data['value'])
    # freq_event = {"freq":val}
    # conn = [conn for conn in esp32_websockets]
    # await conn[0].send(json.dumps(freq_event))
    # emviar el dato recibido por websockets al ESP32


for event_name, cfg in AEROPENDULO_COMS_CONFIG["interface"].items():
    @sio.on(event_name)
    async def handler(sid, data, cfg=cfg, event_name=event_name):
        print(f"[FRONTEND] {event_name}: {data}")
        packed = struct.pack("f", data)
        await NATS_SERVERS[0].publish(f"aeropendulo.esp32.{event_name}", packed)




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

