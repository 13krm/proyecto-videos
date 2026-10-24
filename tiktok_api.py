import base64
import hashlib
import os
import secrets
import urllib.parse

import requests

URL_AUTORIZAR = "https://www.tiktok.com/v2/auth/authorize/"
URL_TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"
URL_BORRADOR = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
PERMISOS = "user.info.basic,video.upload"


def crear_url_conexion(client_key, url_vuelta):
    # Código secreto de un solo uso (PKCE). Hay que guardarlo para el siguiente paso.
    verificador = secrets.token_urlsafe(64)
    desafio = base64.urlsafe_b64encode(
        hashlib.sha256(verificador.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    estado = secrets.token_urlsafe(16)

    parametros = {
        "client_key": client_key,
        "scope": PERMISOS,
        "response_type": "code",
        "redirect_uri": url_vuelta,
        "state": estado,
        "code_challenge": desafio,
        "code_challenge_method": "S256",
    }
    url = URL_AUTORIZAR + "?" + urllib.parse.urlencode(parametros)
    return url, estado, verificador


def canjear_codigo(client_key, client_secret, codigo, url_vuelta, verificador):
    datos = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": codigo,
        "grant_type": "authorization_code",
        "redirect_uri": url_vuelta,
        "code_verifier": verificador,
    }
    respuesta = requests.post(URL_TOKEN, data=datos, timeout=30)
    respuesta.raise_for_status()
    resultado = respuesta.json()
    if "access_token" not in resultado:
        raise Exception(f"TikTok no devolvió token: {resultado}")
    return resultado["access_token"]


def subir_video_borrador(token, ruta_video):
    # Envía el vídeo a la bandeja de borradores de la cuenta. Se publica desde la app de TikTok.
    tamano = os.path.getsize(ruta_video)
    tipo_video = "video/quicktime" if ruta_video.lower().endswith(".mov") else "video/mp4"
    cabeceras = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    cuerpo = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": tamano,
            "chunk_size": tamano,
            "total_chunk_count": 1,
        }
    }
    respuesta = requests.post(URL_BORRADOR, headers=cabeceras, json=cuerpo, timeout=60)
    if respuesta.status_code != 200:
        raise Exception(f"{respuesta.status_code}: {respuesta.text}")
    inicio = respuesta.json()
    if inicio.get("error", {}).get("code") != "ok":
        raise Exception(f"TikTok rechazó el borrador: {inicio}")

    datos = inicio["data"]
    with open(ruta_video, "rb") as archivo:
        contenido = archivo.read()

    cabeceras_envio = {
        "Content-Type": tipo_video,
        "Content-Length": str(tamano),
        "Content-Range": f"bytes 0-{tamano - 1}/{tamano}",
    }
    envio = requests.put(datos["upload_url"], headers=cabeceras_envio, data=contenido, timeout=300)
    envio.raise_for_status()
    return datos["publish_id"]