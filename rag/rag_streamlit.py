import logging
import os
import shutil
import sys
import uuid
from typing import Optional

import streamlit as st
import yaml

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(root_dir)

from typing import Optional

from document_retrieval import DocumentRetrieval
from mixpanel import MixpanelEvents
from env_utils import are_credentials_set, env_input_fields, initialize_env_variables, save_credentials


CONFIG_PATH = os.path.join(current_dir, 'config.yaml')
PERSIST_DIRECTORY = os.path.join(current_dir, f'complete-vector-db')

logging.basicConfig(level=logging.INFO)
logging.info('URL: http://localhost:8501')


logo_image = os.path.join(root_dir,'images/oca_logo1.png')   

def handle_userinput(user_question: str, avatar_img=logo_image) -> None:
    if user_question:
        try:
            with st.spinner('Processing...'):
                response = st.session_state.conversation.invoke({'question': user_question})
            st.session_state.chat_history.append(user_question)
            st.session_state.chat_history.append(response['answer'])

            sources = set([f'{sd.metadata["filename"]}' for sd in response['source_documents']])
            sources_text = ''
            for index, source in enumerate(sources, start=1):
                source_link = source
                sources_text += f'<font size="2" color="grey">{index}. {source_link}</font>  \n'
            st.session_state.sources_history.append(sources_text)
        except Exception as e:
            st.error(f'An error occurred while processing your question: {str(e)}')

    for ques, ans, source in zip(
        st.session_state.chat_history[::2],
        st.session_state.chat_history[1::2],
        st.session_state.sources_history,
    ):
        with st.chat_message('user'):
            st.write(f'{ques}')

        with st.chat_message(
            'ai',
            avatar=avatar_img,
        ):
            st.write(f'{ans}')
            if st.session_state.show_sources:
                with st.expander('Sources'):
                    st.markdown(
                        f'<font size="2" color="grey">{source}</font>',
                        unsafe_allow_html=True,
                    )


def initialize_document_retrieval(prod_mode: bool) -> Optional[DocumentRetrieval]:
    if prod_mode:
        sambanova_api_key = st.session_state.SAMBANOVA_API_KEY
    else:
        if 'SAMBANOVA_API_KEY' in st.session_state:
            sambanova_api_key = os.environ.get('SAMBANOVA_API_KEY') or st.session_state.SAMBANOVA_API_KEY
        else:
            sambanova_api_key = os.environ.get('SAMBANOVA_API_KEY')
    if are_credentials_set():
        try:
            return DocumentRetrieval(sambanova_api_key=sambanova_api_key)
        except Exception as e:
            st.error(f'Failed to initialize DocumentRetrieval: {str(e)}')
            return None
    return None


def main() -> None:
    with open(CONFIG_PATH, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)

    prod_mode = config.get('prod_mode', False)
    conversational = config['retrieval'].get('conversational', False)
    default_collection = 'ekr_default_collection'

    initialize_env_variables(prod_mode)

    st.set_page_config(
        page_title="OCA",
        page_icon=logo_image,
        layout="wide"
    )

    if 'conversation' not in st.session_state:
        st.session_state.conversation = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'show_sources' not in st.session_state:
        st.session_state.show_sources = True
    if 'sources_history' not in st.session_state:
        st.session_state.sources_history = []
    if 'vectorstore' not in st.session_state:
        st.session_state.vectorstore = None
    if 'input_disabled' not in st.session_state:
        st.session_state.input_disabled = True
    if 'document_retrieval' not in st.session_state:
        st.session_state.document_retrieval = None
    if 'st_session_id' not in st.session_state:
        st.session_state.st_session_id = str(uuid.uuid4())
    if 'mp_events' not in st.session_state:
        st.session_state.mp_events = MixpanelEvents(
            os.getenv('MIXPANEL_TOKEN'),
            st_session_id=st.session_state.st_session_id,
            kit_name='enterprise_knowledge_retriever',
            track=prod_mode,
        )
        st.session_state.mp_events.demo_launch()

    st.title(':blue[OCA] Ocorrence Citizen Assistant')

    with st.sidebar:
        st.title('Setup')

        # Callout to get SambaNova API Key
        st.markdown('Get your SambaNova API key [here](https://cloud.sambanova.ai/apis)')

        if not are_credentials_set():
            url, api_key = env_input_fields()
            if st.button('Save Credentials', key='save_credentials_sidebar'):
                message = save_credentials(url, api_key, prod_mode)
                st.session_state.mp_events.api_key_saved()
                st.success(message)
                st.rerun()
        else:
            st.success('Credentials are set')
            if st.button('Clear Credentials', key='clear_credentials'):
                save_credentials('', '', prod_mode)  # type: ignore
                st.rerun()

        if are_credentials_set():
            if st.session_state.document_retrieval is None:
                st.session_state.document_retrieval = initialize_document_retrieval(prod_mode)

        db_path = st.text_input(
            f'Absolute path to your DB folder',
            placeholder='E.g., /Users/<username>/path/to/your/vectordb',
        ).strip()
        st.markdown('**2. Load your datasource and create vectorstore**')
        st.markdown('**Note:** Depending on the size of your vector database, this could take a few seconds')
        if st.button('Load'):
            with st.spinner('Loading vector DB...'):
                if db_path == '':
                    st.error('You must provide a path', icon='🚨')
                else:
                    if os.path.exists(db_path):
                        try:
                            embeddings = st.session_state.document_retrieval.load_embedding_model()
                            collection_name = default_collection if not prod_mode else None
                            vectorstore = st.session_state.document_retrieval.load_vdb(
                                db_path, embeddings, collection_name=collection_name
                            )
                            st.toast(
                                f"""Database loaded{'with collection '
                                    + default_collection if not prod_mode else ''}"""
                            )
                            st.session_state.vectorstore = vectorstore
                            st.session_state.document_retrieval.init_retriever(vectorstore)
                            st.session_state.conversation = (
                                st.session_state.document_retrieval.get_qa_retrieval_chain(
                                    conversational=conversational
                                )
                            )
                            st.session_state.input_disabled = False
                        except Exception as e:
                            st.error(f'An error occurred while loading the database: {str(e)}')
                    else:
                        st.error('Database not present at ' + db_path, icon='🚨')

    user_question = st.chat_input('Ask questions about your data', disabled=st.session_state.input_disabled)
    if user_question is not None:
        st.session_state.mp_events.input_submitted('chat_input')
        handle_userinput(user_question)


main()