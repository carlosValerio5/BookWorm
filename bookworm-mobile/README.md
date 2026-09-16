# BookWorm 

Aplicación móvil desarrollada con **Expo** para el escaneo inteligente de libros mediante la cámara, comunicándose con un backend local en **FastAPI**.

---

## Requisitos Previos

Asegúrate de tener instalado lo siguiente en tu computadora:
* [Node.js](https://nodejs.org/) (versión LTS recomendada)
* [Python](https://www.python.org/) (versión 3.10 o superior)
* La aplicación **Expo Go** instalada en tu dispositivo móvil (iOS / Android) o un emulador configurado.

---

## Dependencias del Proyecto

### 1. Frontend (Expo / React Native)
Además de las librerías base de Expo Router, este proyecto utiliza los siguientes módulos nativos para el manejo de la cámara, imágenes y sistema de archivos local:
* `expo-camera` (Para el acceso a la cámara y captura de portadas/contraportadas)
* `expo-image` (Para el renderizado optimizado de las portadas de libros)
* `expo-file-system` / `expo-file-system/legacy` (Para la lectura y conversión de las fotos a Base64)

### 2. Backend (Python / FastAPI)
El servidor local requiere las siguientes librerías para procesar las peticiones y gestionar el almacenamiento en el dataset:
* `fastapi` y `uvicorn` (Para levantar la API web y el servidor local)
* `pydantic` (Validación de esquemas JSON)
* `opencv-python` y `numpy` (Procesamiento de imágenes por computadora)
* `structlog` (Sistema estructurado de registros / logging)
* `pillow` (Manipulación de formatos de imagen)

---

## Instalación y Configuración

```bash
### Paso 1: Configurar y ejecutar el Backend
# Abre una terminal en la carpeta raíz del proyecto donde se encuentra el servidor y ejecuta:

# Instalar las dependencias necesarias de Python
pip install fastapi uvicorn pydantic opencv-python structlog numpy pillow

# Iniciar el servidor local de Python con recarga automática
# (Asegúrate de cambiar la IP en api.ts si usas un dispositivo físico en tu red Wi-Fi)
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000

### Paso 2: Configurar y arrancar el Frontend
# Abre otra pestaña o ventana de la terminal en la carpeta de la aplicación móvil y ejecuta:
# 1. Instalar las dependencias de Node.js (incluyendo los módulos de Expo)
npm install

# 2. Iniciar el servidor de desarrollo de Expo
npx expo start