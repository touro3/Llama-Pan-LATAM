import streamlit as st
import pyaudio
import speech_recognition as sr
import tempfile
import os


# Função para listar dispositivos de entrada de áudio disponíveis
def listar_dispositivos_audio():
    """Lista dispositivos de entrada de áudio disponíveis."""
    audio = pyaudio.PyAudio()
    dispositivos = {}
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:  # Apenas dispositivos de entrada
            dispositivos[i] = info["name"]
    audio.terminate()
    return dispositivos


# Função para gravar áudio usando o microfone
def gravar_audio(device_index):
    """Grava áudio usando o dispositivo especificado."""
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone(device_index=device_index) as source:
            st.info("Ajustando ruído ambiente... Aguarde.")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            st.info("Gravando... Fale claramente.")
            audio = recognizer.listen(source, timeout=4)
            st.success("Gravação concluída!")
        st.info("Transcrevendo o áudio...")
        texto = recognizer.recognize_google(audio, language="pt-BR")
        return texto
    except sr.UnknownValueError:
        st.error("Não foi possível entender o áudio.")
    except sr.RequestError as e:
        st.error(f"Erro no serviço de reconhecimento: {e}")
    except Exception as ex:
        st.error(f"Erro ao capturar áudio: {ex}")
    return None


# Função para transcrever áudio de arquivo
def transcrever_audio(arquivo_audio):
    recognizer = sr.Recognizer()
    with sr.AudioFile(arquivo_audio) as source:
        audio = recognizer.record(source)
    try:
        texto_transcrito = recognizer.recognize_google(audio, language="pt-BR")
        return texto_transcrito
    except sr.UnknownValueError:
        return "Não foi possível entender o áudio."
    except sr.RequestError:
        return "Erro no serviço de transcrição."
    except Exception as e:
        return f"Erro ao processar o áudio: {e}"


logo_image = os.getcwd()+'/images/logo-OCA.png'

st.set_page_config(
    page_title="OCA",
    page_icon=logo_image,
    layout="wide"
)

# Cabeçalho
st.image(logo_image, width=100)

st.title('Projeto OCA')

st.markdown(
    """
    Este aplicativo foi projetado para oferecer uma visão geral criada por IA e ajudar 
    pessoas em situações de urgência. Insira sua localização e seu problema abaixo.
    """
)

# Formulário para localização
st.subheader("1. Informe sua localização")
localidade = st.text_input("Digite sua cidade e estado (ex: Porto Velho, Rondônia)", placeholder="Sua localização")

# Entrada de texto ou áudio
st.subheader("2. Descreva sua situação")
input_mode = st.radio("Escolha o tipo de entrada:", ("Texto", "Áudio"))

descricao = st.session_state.get("descricao", "")  # Variável inicial para descrição

if input_mode == "Texto":
    descricao = st.text_area("Digite a descrição do problema:", placeholder="Exemplo: Preciso de ajuda médica.")
    st.session_state["descricao"] = descricao
else:
    # Opções de envio de áudio
    audio_source = st.radio("Escolha o modo de envio de áudio:", ("Gravação pelo microfone", "Upload de arquivo"))

    if audio_source == "Gravação pelo microfone":
        # Listar dispositivos de áudio
        dispositivos_audio = listar_dispositivos_audio()
        if not dispositivos_audio:
            st.error("Nenhum dispositivo de entrada de áudio disponível.")
        else:
            dispositivo_selecionado = st.selectbox("Selecione o dispositivo de áudio:", dispositivos_audio.values())
            dispositivo_index = list(dispositivos_audio.keys())[list(dispositivos_audio.values()).index(dispositivo_selecionado)]

            if st.button("Gravar Áudio"):
                descricao_gravada = gravar_audio(device_index=dispositivo_index)
                if descricao_gravada:
                    descricao = descricao_gravada
                    st.session_state["descricao"] = descricao
                    st.write("**Transcrição do Áudio:**", descricao)

    elif audio_source == "Upload de arquivo":
        audio_file = st.file_uploader("Faça upload de um arquivo de áudio:", type=["wav", "mp3"])
        if audio_file:
            with tempfile.NamedTemporaryFile(delete=False) as temp_audio:
                temp_audio.write(audio_file.read())
                transcricao = transcrever_audio(temp_audio.name)
                descricao = transcricao
                st.session_state["descricao"] = descricao
            os.unlink(temp_audio.name)
            st.write("**Transcrição do Áudio:**", descricao)
        else:
            st.warning("Por favor, envie um arquivo de áudio válido.")

# Botão para enviar
if st.button("Enviar"):
    if not localidade:
        st.error("Por favor, insira sua localização.")
    elif not descricao:
        st.error("Por favor, descreva sua situação ou forneça um áudio válido.")
    else:
        st.success("Informações enviadas com sucesso!")
        st.markdown(
            f"""
            **Detalhes enviados:**
            - Localização: {localidade}
            - Situação: {descricao}
            """
        )
        st.info("A IA irá processar esses dados para fornecer ajuda personalizada.")
