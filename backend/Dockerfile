# Usar imagen base de Python 3.11
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema si son necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de requisitos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio para la base de datos si no existe
RUN mkdir -p /app/data

# Exponer puerto
EXPOSE 8000

# Variables de entorno por defecto
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV DEBUG=False

# Comando para ejecutar la aplicación
CMD ["python", "main.py"]