import json, zipfile, os

import streamlit as st
import xml.etree.ElementTree as ET
import AddWordAlignment

def main():
    ready = True
    st.title( 'AddWordAlignment' )

    openai_api_key = None
    if os.path.exists("config.json"):
        with open("config.json") as f:
            config = json.load(f)
            if "openai_api_key" in config:
                openai_api_key = config["openai_api_key"]

    if not openai_api_key:
        openai_api_key = st.text_input( 'What is your OpenAI API key?' )
    if not openai_api_key: ready = False

    book_name = st.text_input( "What is the Bible book name the alignment is being added to, (e.g. 1 Peter)?" )
    if not book_name: ready = False

    output_language = st.text_input( f'What is the gloss language being aligned?' )
    if not output_language: ready = False

    streamlit_file = st.file_uploader( f'Please provide the juxtilinear json to be aligned.')
    if not streamlit_file: ready = False

    host_local = st.checkbox( "Do you want to use a local HuggingFace model instead of an OpenAI model?", value=True )

    if not host_local:
        model_name = st.selectbox( 'Which OpenAI model would you like to use?', ('gpt-3.5-turbo', 'gpt-4-1106-preview', 'gpt-4') )
    else:
        model_name = st.selectbox( 'What HuggingFace model would you like to use?', ("teknium/OpenHermes-2.5-Mistral-7B",) )
    if not model_name: ready = False

    if st.button( 'Add Word Alignment', disabled=not ready ):

        data = json.load( streamlit_file )
        input_data = streamlit_file.name

        output_message_pane = st.empty()

        def output_callback( message ):
            #output_message_pane.text( message )
            output_message_pane.empty()
            with output_message_pane:
                st.write( message )


        output_data = AddWordAlignment.get_output_data( host_local, openai_api_key, model_name, data, book_name, output_language, output_callback )
        

        #now need to string output_data to json and then provide it as a download link in streamlit.
        

        output_filename = os.path.basename( input_data ).replace( ".json", f"_matched.json" )
        output_data_json = json.dumps( output_data )
        st.download_button( label="Download modified json", data=output_data_json, file_name=output_filename, mime="application/json" )


        output_callback( 'Done' )


if __name__ == '__main__':
    main()