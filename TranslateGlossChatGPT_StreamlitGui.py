import json, zipfile, os

import streamlit as st
import xml.etree.ElementTree as ET
import TranslateGlossChatGPT

def main():
    ready = True
    st.title( 'TranslateGlossChatGPT' )

    openai_api_key = None
    if os.path.exists("config.json"):
        with open("config.json") as f:
            config = json.load(f)
            if "openai_api_key" in config:
                openai_api_key = config["openai_api_key"]

    if not openai_api_key:
        openai_api_key = st.text_input( 'What is your OpenAI API key?' )
    if not openai_api_key: ready = False

    book_name = st.text_input( "What is the name of the book of the Bible you wish to translate, (e.g. 1 Peter)?" )
    if not book_name: ready = False

    output_language = st.text_input( f'What target language would you like to translate {book_name + " " if book_name else ""}to?' )
    if not output_language: ready = False

    streamlit_file = st.file_uploader( f'Please provide the juxtilinear json you would like to translate{ " to " + output_language if output_language else ""}.')
    if not streamlit_file: ready = False

    exclude_source_gloss = st.checkbox( f'Do you want to exclude the source gloss from the translation?  Do this if { streamlit_file.name if streamlit_file else "the json you provide" } is already in {output_language if output_language else "the target language"}.' )


    extra_ChatGPT_instructions = st.text_input( 'Enter any additional instructions that you would like to add to the ChatGPT prompt.' )

    streamlit_usfx_zip = st.file_uploader( f"If you would like to provide a { output_language if output_language else 'target language'} USFX zip file, please provide it." )

    #need to now identify the proper xml file in the zip.
    if streamlit_usfx_zip:
        xml_files_in_zip = []
        default_index = 0

        with zipfile.ZipFile( streamlit_usfx_zip, 'r' ) as zip:
            # #print out all the files in the zip file
            # for filename in zip.namelist():
            #     print( filename )

            for index, filename in enumerate( zip.namelist() ):
                if filename.endswith( ".xml" ):
                    xml_files_in_zip.append( filename )

                    if 'usfx' in filename:
                        default_index = index
        if len( xml_files_in_zip ) == 1:
            xml_path_in_zip = xml_files_in_zip[0]
        else:
            xml_path_in_zip = st.selectbox( f"Which xml file in {streamlit_usfx_zip.name} contains the usfx?", xml_files_in_zip, index=default_index )

        if xml_path_in_zip:
            bcv_template = st.text_input( f'What is the template for the bcv code for looking up verses in {xml_path_in_zip}?', 'PHP.{0}.{1}' )
            if not bcv_template: ready = False

    model = st.selectbox( 'Which model would you like to use?', ('gpt-4-1106-preview', 'gpt-3.5-turbo', 'gpt-4') )
    if not model: ready = False

    if st.button( 'Translate', disabled=not ready ):

        data = json.load( streamlit_file )
        input_data = streamlit_file.name

        input_data_basename = TranslateGlossChatGPT.get_input_data_basename( input_data )

        #read the usfx file
        if streamlit_usfx_zip:
            #read the zip from xml_path_in_zip in streamlit_usfx_zip
            with zipfile.ZipFile( streamlit_usfx_zip, 'r' ) as zip:
                with zip.open( xml_path_in_zip ) as f:
                    xml_string = f.read().decode('utf-8')
                    bible_usfx = ET.fromstring( xml_string )
        else:
            bible_usfx = None

        output_message_pane = st.empty()

        def output_callback( message ):
            #output_message_pane.text( message )
            output_message_pane.empty()
            with output_message_pane:
                st.write( message )


        output_data = TranslateGlossChatGPT.get_output_data( data, input_data_basename, book_name, bible_usfx, 
              output_language, bcv_template, exclude_source_gloss, extra_ChatGPT_instructions, model, openai_api_key, output_callback )
        

        #now need to string output_data to json and then provide it as a download link in streamlit.
        output_filename = TranslateGlossChatGPT.get_output_filename( input_data_basename, output_language, '' )
        output_data_json = json.dumps( output_data )
        st.download_button( label="Download the translated json", data=output_data_json, file_name=output_filename, mime="application/json" )

        
        output_callback( 'Done' )


if __name__ == '__main__':
    main()