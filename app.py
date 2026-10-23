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
    # "estados": estado -> (código secreto, perfil que se está conectando)
    # "credenciales": perfil -> permiso de YouTube de ese perfil
    return {"estados": {}, "credenciales": {}}


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

# Si Google nos devuelve aquí, comprobamos el estado y guardamos el permiso del perfil
if "code" in st.query_params:
    estado = st.query_params.get("state", "")
    if estado in db["estados"]:
        verificador, perfil_conectado = db["estados"].pop(estado)
        flow = crear_flow(state=estado)
        flow.code_verifier = verificador
        flow.fetch_token(code=st.query_params["code"])
        db["credenciales"][perfil_conectado] = flow.credentials
        st.query_params.clear()
        # Recordamos el perfil para que siga seleccionado al volver
        st.query_params["perfil"] = perfil_conectado
    else:
        st.query_params.clear()
    st.rerun()

# Selector de perfil (Youtubers / Podcast)
perfiles = list(PERFILES)
perfil_url = st.query_params.get("perfil", perfiles[0])
indice = perfiles.index(perfil_url) if perfil_url in perfiles else 0
perfil = st.radio("Perfil", perfiles, index=indice, horizontal=True)

pestana_enlaces, pestana_api = st.tabs(["Enlaces directos", "Con API (automático)"])

# --- Pestaña 1: enlaces directos, sin API ---
with pestana_enlaces:
    st.write("Abre la página de subida de cada red. Se usa la cuenta que tengas abierta en el navegador.")
    for red, enlace in PERFILES[perfil].items():
        st.link_button(f"Subir a {red}", enlace)

# --- Pestaña 2: subida automática con API ---
with pestana_api:
    st.subheader("YouTube")
    credenciales = db["credenciales"].get(perfil)

    if credenciales is None:
        # Todavía no hay canal conectado para este perfil
        flow = crear_flow()
        url, estado = flow.authorization_url(
            access_type="offline", prompt="consent select_account"
        )
        db["estados"][estado] = (flow.code_verifier, perfil)
        st.write(f"Conecta el canal de YouTube de {perfil}.")
        st.link_button("Conectar con YouTube", url)
    else:
        if st.button("Desconectar YouTube", key=f"desconectar_{perfil}"):
            db["credenciales"].pop(perfil, None)
            st.rerun()

        video = st.file_uploader(
            "Elige un vídeo", type=["mp4", "mov", "avi", "mkv"], key=f"video_{perfil}"
        )
        titulo = st.text_input("Título", value="Mi vídeo", key=f"titulo_{perfil}")

        if video is not None and st.button("Subir a YouTube", key=f"subir_{perfil}"):
            try:
                with st.spinner("Subiendo el vídeo..."):
                    # Guardamos el vídeo en un archivo temporal para enviarlo a YouTube
                    extension = os.path.splitext(video.name)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
                        tmp.write(video.getbuffer())
                        ruta = tmp.name

                    youtube = build("youtube", "v3", credentials=credenciales)
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
                st.success(f"Vídeo subido como privado. ID: {respuesta['id']}")
            except Exception as error:
                st.error(f"No se pudo subir el vídeo: {error}")

    st.subheader("TikTok")
    st.info("Pendiente: necesita que TikTok apruebe la app (auditoría).")
    st.subheader("Instagram")
    st.info("Pendiente: necesita cuenta profesional y configuración de Meta.")
