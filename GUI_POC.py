import streamlit as st
from pathlib import Path
import os
import librosa
import glob
from app.utils import save_record, read_audio, record
from app.api_calls import transcribe_recording

logo_image = os.getcwd()+'/images/logo-OCA.png'

st.set_page_config(
    page_title="OCA",
    page_icon=logo_image,
    layout="wide"
)

# Cabeçalho
st.image(logo_image, width=100)

st.title('Projeto OCA')


st.markdown('Interação com áudio integrado a chamadas de API :sunglasses:')
st.markdown("**Testes em andamento...**")

st.markdown('---')


st.header("1. Record your own voice")

filename = st.text_input("Choose a filename: ")
duration = st.number_input(
    "Recording duration (seconds)", value=None, placeholder="Type a number..."
)
if st.button(f"Click to Record"):
    if filename == "":
        st.warning("Choose a filename.")
    else:
        record_state = st.text("Recording...")
        #duration = 2  # seconds
        fs = 48000
        myrecording = record(duration, fs)
        record_state.text(f"Saving sample as {filename}.mp3")

        path_myrecording = f"{os.getcwd()}/samples/{filename}.mp3"

        save_record(path_myrecording, myrecording, fs)
        record_state.text(f"Done! Saved sample as {filename}.mp3")

        st.audio(read_audio(path_myrecording))


audio_folder = "samples"
filenames = glob.glob(os.path.join(audio_folder, "*.mp3"))
selected_filename = st.selectbox("Select a file", filenames)

if selected_filename is not None:
    in_fpath = Path(selected_filename.replace('"', "").replace("'", ""))
    fpath = os.path.join(os.getcwd(), in_fpath)
    original_wav, sampling_rate = librosa.load(str(in_fpath))

    st.audio(read_audio(in_fpath))

    if st.checkbox("Do you want to transcribe your recording?"):
        st.success(f"Creating the transcription... file {fpath}")
        transcription = transcribe_recording(fpath)
        
        a = st.text_area("Validate you transcription:", value=str(transcription).replace("\n", ""))

    if "disabled" not in st.session_state:
        st.session_state["disabled"] = False

    def disable():
        st.session_state["disabled"] = True

    st.text_input(
        "Enter some text", 
        disabled=st.session_state.disabled, 
        on_change=disable
    )