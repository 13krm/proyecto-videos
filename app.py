import os
import tempfile
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import PERFILES

# Dirección exacta de la web publicada (debe coincidir con la de Google)
URL_APP = "https://proyectosubirvideos.streamlit.app/"
PERMISOS = ["https://www.googleapis.com/auth/youtube.upload"]


@st.cache_resource
def almacen():
    # Memoria del servidor: sobrevive a la vuelta de Google.
    # "estados" guarda las comprobaciones pendientes; "credenciales" guarda el permiso.
    return {"estados": set(), "credenciales": None}


def crear_flow(state=None):
    # Construye la conexión con Google usando los datos de secrets
    cfg = st.secrets["google"]
    config_google = {"web": {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }}
    return Flow.from_client_config(
        config_google, scopes=PERMISOS, redirect_uri=URL_APP, state=state
    )


db = almacen()
st.title("Mi página de vídeos")

# Si Google nos devuelve aquí, comprobamos el estado y cambiamos el código por el permiso
if "code" in st.query_params and db["credenciales"] is None:
    estado = st.query_params.get("state", "")
    if estado in db["estados"]:
        db["estados"].discard(estado)
        flow = crear_flow(state=estado)
        flow.fetch_token(code=st.query_params["code"])
        db["credenciales"] = flow.credentials
    st.query_params.clear()
    st.rerun()

# Si todavía no hay permiso, mostramos el botón para conectar
if db["credenciales"] is None:
    flow = crear_flow()
    url, estado = flow.authorization_url(access_type="offline", prompt="consent")
    db["estados"].add(estado)
    st.write("Conecta tu canal de YouTube para subir vídeos.")
    st.link_button("Conectar con YouTube", url)
    st.stop()

# Botón para desconectar la cuenta
if st.button("Desconectar cuenta"):
    db["credenciales"] = None
    st.rerun()

# Subida de vídeo a YouTube
st.subheader("Subir vídeo a YouTube")
video = st.file_uploader("Elige un vídeo", type=["mp4", "mov", "avi", "mkv"])
titulo = st.text_input("Título", value="Mi vídeo")

if video is not None and st.button("Subir a YouTube"):
    with st.spinner("Subiendo el vídeo..."):
        # Guardamos el vídeo en un archivo temporal para enviarlo a YouTube
        extension = os.path.splitext(video.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
            tmp.write(video.getbuffer())
            ruta = tmp.name

        youtube = build("youtube", "v3", credentials=db["credenciales"])
        cuerpo = {
            "snippet": {"title": titulo, "categoryId": "22"},
            # Privado hasta que el proyecto pase la auditoría de Google
            "status": {"privacyStatus": "private"},
        }
        peticion = youtube.videos().insert(
            part="snippet,status",
            body=cuerpo,
            media_body=MediaFileUpload(ruta, resumable=True),
        )
        respuesta = peticion.execute()
        os.remove(ruta)
    st.success(f"Vídeo subido a tu canal como privado. ID: {respuesta['id']}")

# Botones de enlace directo para las redes
st.subheader("Subir a las redes")
for red, enlace in PERFILES["Youtubers"].items():
    st.link_button(f"Subir a {red}", enlace)
