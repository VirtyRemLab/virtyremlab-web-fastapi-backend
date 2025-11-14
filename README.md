
# Ejecución en local

```bash
uvicorn main:socket_app --host 0.0.0.0 --port 8002 --workers 1 --loop uvloop
```

# Despliegue
Para el despliegue se empleará un contenedor de docker. La imagen se crear a partir del ```Dockerfile```.

Creación de la imagen:

```bash
docker build -t virtyremlab-backend:v0.1 .
```

Ejecutar el contenedor para la imagen creada:
```bash 
docker run -d -p 8002:8002  --name virtyremlab-backend --network virtyremlab-net virtyremlab-backend:v0.1
```

# NATS
Los mensajes recibidos por websockets del ESP se reenviarán a un servidor NATS. Este servidor es otro contenedor de docker que se ejecutará como:
```bash
docker pull nats:latest
docker run -p 4222:4222 -ti nats:latest
```

# Modelos de los datos [en pruebas] 

El gateway recibe un array de dos valores binarios. El primero de ellos simula el seno y el segundo siempre es 0. Se definen los siguientes tópicos para el servidor NATS:

- aeropendulo.esp32.y
- aeropendulo.esp32.nulo
