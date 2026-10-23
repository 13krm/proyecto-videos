# Importamos las librerías necesarias
import streamlit as st
from config import PERFILES

st.title("Mi página de vídeos")

# Botones de enlace directo para el perfil "Youtubers"
st.subheader("Subir a las redes")
for red, enlace in PERFILES["Youtubers"].items():
    st.link_button(f"Subir a {red}", enlace)