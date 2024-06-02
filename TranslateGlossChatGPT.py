# %% [markdown]
# # Translate Gloss by ChatGPT

# %%
import getpass, json, re, copy, os, time
from openai import OpenAI
import zipfile
import xml.etree.ElementTree as ET


# %%
def get_input_data_basename( input_data ):
    input_data_basename = os.path.basename( input_data ).replace( ".json", "" ).replace( "_ChatGPT_French", "" )
    return input_data_basename

def get_output_filename( input_data_basename, output_language, output_suffix ):
    output_filename = f"./data/{input_data_basename}_ChatGPT_{output_language}{output_suffix}.json"
    return output_filename

# %%
def get_system_message( output_language ):
    system_message = f"""
    You are a language professor preparing language material.  
    You are translating subsections of Bible verses from Greek and French into {output_language}.
    """.strip()
    return system_message



# %%

def get_bible_usfx( reference_bible_usfx_zip ):
    bible_usfx = None
    if reference_bible_usfx_zip:
        zip_path = reference_bible_usfx_zip.split( ".zip/" )[0] + ".zip"
        xml_path_in_zip = reference_bible_usfx_zip.split( ".zip/" )[1]

        #parse the xml tree in the zip file for usfx.
        with zipfile.ZipFile( zip_path, 'r' ) as zip:
            # #print out all the files in the zip file
            # for filename in zip.namelist():
            #     print( filename )

            with zip.open( xml_path_in_zip ) as f:
                xml_string = f.read().decode('utf-8')
                bible_usfx = ET.fromstring( xml_string )
    return bible_usfx


def get_node_text( node, bcv_code, recording ):
    #iterate inline through the tree and record all text and tail, after recording is true
    #and then stop when we hit a different bcv code.  recording is an array so that it is
    #passed by reference.

    #trim out f nodes.  I think they are foot notes.
    if node.tag == "f":
        return ""

    result = ""

    if "bcv" in node.attrib:
        recording[0] = node.attrib.get( "bcv" ) == bcv_code
    
    if recording[0]:
        if node.text:
            result += node.text

    for child in node:
        result += get_node_text( child, bcv_code, recording )

    if recording[0]:
        if node.tail:
            result += node.tail

    return result


def get_context_verse( cv, bible_usfx, bcv_template ):
    if bible_usfx is None: return None
    chapter, verse = cv.split( ":" )
    bcv_code = bcv_template.format( chapter, verse )
    result = get_node_text(bible_usfx, bcv_code, [False])
    result = result.strip()
    if result: return result
    return None

#     print("hi")


# %%
#go ahead and load the data.
def get_data( input_data ):
    with open( input_data ) as fin:
        data = json.loads( fin.read() )
    return data

def strip_and_tokenize_gloss( gloss ):
    gloss = gloss.replace( '-', ' ' ).replace( '*', ' ' ).strip()

    while '  ' in gloss:
        gloss = gloss.replace( '  ', ' ' )

    tokens_to_nuke = ['.', '?', '!', ',', '"', "'", '(', ')']
    for token in tokens_to_nuke:
        gloss = gloss.replace( token, '' )

    return gloss.split()

# %%
def generate_prompt_string( _data, verse_index, chunk_index, _book_name, bible_usfx, bcv_template, exclude_source_gloss, output_language, extra_ChatGPT_instructions ):
    verse = _data[verse_index]
    chunks = verse['chunks']
    chunk = chunks[chunk_index]
    sources = chunk['source']
    first_piece = sources[0]

    _n = '\n' #f-string objection < python 3.12

    result = f"""
Look at this verse:
```
{_book_name} {first_piece['cv']}: {verse['sourceString']}
```
""".lstrip()
    
    reference_verse = get_context_verse( first_piece['cv'], bible_usfx, bcv_template )
    if reference_verse is not None:
        result += f"""
This is a target translation:
```
{reference_verse}
```
"""

    result += f"""
Focus on these specific words:
```
{' '.join(source['content'] for source in sources)}
```
"""

    if any( ('morph' in source) for source in sources ):
        result += f"""
Morphology information:
```
{_n.join( source['content'] + ': ' + ','.join(source['morph']) for source in sources if 'morph' in source) }
```
"""

    if not exclude_source_gloss and chunk['gloss'] != "<not implemented>":
        result += f"""
The gloss for this in French is:
```
{chunk['gloss']}
```
"""

    result += f"""
What is the gloss for these specific words in {output_language}?  Mark supplemental implicit words with *asterisks* in the gloss. Output the answer in JSON. {extra_ChatGPT_instructions}

Example output:
```json
{{"gloss": "combined-words and *implicit words* example"}}
```
"""
    return result.strip()



# %%
def generate_gloss_for( data, verse_index, chunk_index, book_name, system_message, bible_usfx, model_name, bcv_template, exclude_source_gloss, output_language, extra_ChatGPT_instructions, client_or_pipe, host_local ):
    prompt = generate_prompt_string( data, verse_index, chunk_index, book_name, bible_usfx, bcv_template, exclude_source_gloss, output_language, extra_ChatGPT_instructions )
    messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]


    response = client_or_pipe(messages)
    return response

# %%

def extract_answer_from_response( _response, greek_chunk, output_language ):
    #This checks to see if it is in a MarkDown block.
    extractor_regular_expression = r"```(?:json)?(?P<json_data>.*?)```"
    match = re.search(extractor_regular_expression, _response, re.DOTALL)

    if not match:
        #This one checks for just raw json
        extractor_regular_expression = r"(?P<json_data>\{.*\})"
        match = re.search(extractor_regular_expression, _response, re.DOTALL)

        if not match:
            raise ValueError("Result not in expected format.")

    extracted_data = match.group('json_data')

    #now parse the json.
    response = json.loads(extracted_data)

    #see if we can find a reference to output_language
    for key, value in response.items():
        if output_language.lower() in key.lower():
            return value
        
    #see if the key "gloss" works.
    if 'gloss' in response:

        #make sure none of the greek made it into the output.
        for word in greek_chunk:
            if word in response['gloss']:
                raise ValueError("Greek word found in gloss.")

        return response['gloss']

    raise ValueError("Result not in expected format.")   


# %%
def number_of_verses( _data ):
    return len(_data)
def number_of_chunks( _data, verse_index ):
    return len(_data[verse_index]['chunks'])

def strip_lines( text ):
    return "\n".join( line.strip() for line in text.splitlines() ).strip()


def create_cache_saver( client_or_pipe, cache_saver ):
    """This takes the LLM and wraps it so that if the question is asked again that the same response is returned in the log provided."""

    prompt_key = "Prompt string:"
    answer_key = "Response:"
    answer_end = "Answer:"

    in_prompt = False
    in_answer = False

    collected_prompt = []
    collected_answer = []

    prompts_to_answer = {}



    with open( cache_saver, "r" ) as fin:
        for line in fin:
            if line.strip() == prompt_key:
                in_prompt = True
                in_answer = False
            elif line.strip() == answer_key:
                in_answer = True
                in_prompt = False
            elif line.strip() == answer_end:
                in_prompt = False
                in_answer = False

                if collected_prompt and collected_answer:
                    prompt = "\n".join( collected_prompt ).strip()
                    answer = "\n".join( collected_answer ).strip()
                    prompts_to_answer[prompt] = answer

                collected_prompt = []
                collected_answer = []
            else:
                if in_prompt:
                    collected_prompt.append( line.strip() )
                elif in_answer:
                    collected_answer.append( line.strip() )

    def cache_thing( messages ):
        prompt = strip_lines(messages[-1]['content'].strip())
        if prompt in prompts_to_answer:
            return prompts_to_answer[prompt]
        else:
            return client_or_pipe( messages ) 

    return cache_thing
            

# %%
def get_output_data( data, input_data_basename, book_name, bible_usfx, output_language, bcv_template, exclude_source_gloss, extra_ChatGPT_instructions, model_name, openai_api_key, host_local, output_callback=None, gloss_output_callback=None, cache_saver=None ):

    if output_callback:
        output_callback( "Starting..." )

    if not host_local:
        from openai import OpenAI
        open_ai = OpenAI( api_key = openai_api_key )
        def client_or_pipe( messages ):
            while True:
                try:
                    response = open_ai.chat.completions.create(
                        model=model_name,
                        messages=messages
                    )
                    #return response.choices[0].text,
                    return response.choices[0].message.content
                except Exception as e:
                    print( e )
                    time.sleep( 10 )
    else:
        from transformers import pipeline
        local_pipeline = pipeline("text-generation", model_name)
        def client_or_pipe( messages ):
            response = local_pipeline(messages, max_new_tokens=128, do_sample=True)
            return response[0]['generated_text'][-1]['content']

    if cache_saver:
        client_or_pipe = create_cache_saver( client_or_pipe, cache_saver )
    
    system_message = get_system_message( output_language )

    output_data = copy.deepcopy(data)

    verse_index = 0
    chunk_index = 0


    starting_time = time.time()

    if gloss_output_callback:
        gloss_output_log = []

    #append to process.log
    with open( f"{input_data_basename}_{output_language}_process.log", "w" ) as process_out:
        done = False

        while not done:

            if verse_index >= number_of_verses(data):
                done = True

            if not done:
                try:
                    process_out.write( f"Processing verse {verse_index} chunk {chunk_index}\n" )
                    process_out.write( f"Prompt string:\n{generate_prompt_string( data, verse_index, chunk_index, book_name, bible_usfx, bcv_template, exclude_source_gloss, output_language, extra_ChatGPT_instructions )}\n\n")

                    response = generate_gloss_for( data, verse_index, chunk_index, book_name, system_message, bible_usfx, model_name, bcv_template, exclude_source_gloss, output_language, extra_ChatGPT_instructions, client_or_pipe, host_local )

                    process_out.write( f"Response:\n{response}\n\n" )


                
                    sources = data[verse_index]['chunks'][chunk_index]['source']
                    greek_chunk = ' '.join(source['content'] for source in sources).replace( ",", "").replace( '.', '' ).replace( "?", "" ).replace( "!", "" )
                    greek_chunk = strip_and_tokenize_gloss( greek_chunk )

                    answer = extract_answer_from_response( response, greek_chunk, output_language )

                    process_out.write( f"Answer:\n{answer}\n\n" )
                    process_out.flush()

                    output_data[verse_index]['chunks'][chunk_index]['gloss'] = answer

                    if gloss_output_callback:
                        gloss_output_log.append( {"greek": ' '.join(source['content'] for source in sources), "translation": answer, "cv": data[verse_index]['chunks'][chunk_index]['source'][0]['cv']} )
                        gloss_output_callback( gloss_output_log )

                    chunk_index += 1
                    if chunk_index >= number_of_chunks(data, verse_index):
                        verse_index += 1
                        chunk_index = 0

                        now = time.time()
                        end_estimation_time = now + (now - starting_time) * (number_of_verses(data) - verse_index) / (verse_index)
                        print( f"Estimated end time: {time.strftime('%Y-%m-%d %I:%M:%S %p', time.localtime(end_estimation_time))}  Arrange count: {verse_index}/{number_of_verses(data)}" )

                        if output_callback:
                            output_callback( f"Estimated end time: {time.strftime('%Y-%m-%d %I:%M:%S %p', time.localtime(end_estimation_time))}  Arrange count: {verse_index}/{number_of_verses(data)}" )

                #catch ValueError
                except ValueError as e:
                    process_out.write( f"Error processing verse {verse_index} chunk {chunk_index}: {e}\n" )
                    process_out.flush()
                    if output_callback:
                        output_callback( f"Error processing verse {verse_index} chunk {chunk_index}: {e}" )
                    time.sleep(10)
    return output_data

# %%
def write_output_data( output_data, output_filename ):
    with open( output_filename, 'w' ) as result_file_out:
        result_file_out.write( json.dumps( output_data, indent=4, ensure_ascii=False  ) )

# %%

def do_it( input_data, book_name, output_language, output_suffix, reference_bible_usfx_zip, bcv_template, exclude_source_gloss, extra_ChatGPT_instructions, model_name, openai_api_key, host_local, cache_saver ):
    data = get_data( input_data )
    input_data_basename = get_input_data_basename( input_data )
    bible_usfx = get_bible_usfx( reference_bible_usfx_zip )
    output_data = get_output_data( data, input_data_basename, book_name, bible_usfx, output_language, bcv_template, exclude_source_gloss, extra_ChatGPT_instructions, model_name, openai_api_key, host_local, cache_saver=cache_saver )
    output_filename = get_output_filename( input_data_basename, output_language, output_suffix )
    write_output_data( output_data, output_filename )

#Adding a main break so I can call this script from a web gui wrapper.
if __name__ == "__main__":
    #I added _ prefix to everything so that I could tell when functions were taking the values from the global scope.

    
    # see if we can get an openai api key out of a config.json file
    _openai_api_key = None
    if os.path.exists("config.json"):
        with open("config.json") as f:
            config = json.load(f)
            if "openai_api_key" in config:
                _openai_api_key = config["openai_api_key"]

    
    if not _openai_api_key:
        _openai_api_key = getpass.getpass("OpenAI api key?")


    _host_local = False

    if not _host_local:
        #_model_name = "gpt-3.5-turbo"
        #_model_name = "gpt-4"
        #_model_name = "gpt-4-1106-preview"
        _model_name = "gpt-4o"
    else:
        _model_name = "teknium/OpenHermes-2.5-Mistral-7B"


    #client = OpenAI( api_key = _openai_api_key )

    # some defaults.
    _exclude_source_gloss = False
    _extra_ChatGPT_instructions = ""
    _reference_bible_usfx_zip = ""
    _output_suffix = ""
    _bcv_template = None


    # output_language = "Farsi"
    # input_data = "./data/php_21.01.2024.json"
    # output_filename = f"./data/php_ChatGPT_{output_language}.json"
    # book_name = "Philippians"

    # output_language = "English"
    # input_data = "./data/tite21_21.01.2024.json"
    # book_name = "Titus"

    # output_language = "French"
    # input_data = "./data/php_21.01.2024.json"
    # book_name = "Philippians"
    # exclude_source_gloss = True #Don't include the french when producing French.

    # output_language = "Farsi"
    # input_data = "./data/php_21.01.2024.json"
    # book_name = "Philippians"
    # extra_ChatGPT_instructions = "\n\nUse Christian words such as in Persion Old Version. Do not use Muslim words or Arabic words."
    # reference_bible_usfx_zip = "./data/Farsi_pesOPV_usfx.zip/pesOPV_usfx.xml"
    # bcv_template = "PHP.{0}.{1}"

    # _output_language = "Arabic"
    # _input_data = "./data/php_21.01.2024.json"
    # _book_name = "Philippians"
    # _extra_ChatGPT_instructions = "\n\nUse Christian words such as in the provided Arabic version."
    # _reference_bible_usfx_zip = "./data/arb-vd_usfx.zip/arb-vd_usfx.xml"
    # _bcv_template = "PHP.{0}.{1}"


    # output_language = "French"
    # input_data = "./data/auto_11-philippians.json"
    # book_name = "Philippians"
    # exclude_source_gloss = True #Don't include the french when producing French.

    # output_language = "French"
    # input_data = "./data/auto_21-1peter.json"
    # book_name = "1 Peter"
    # exclude_source_gloss = True #Don't include the french when producing French.

    # output_language = "English"
    # input_data = "./data/auto_21-1peter_ChatGPT_French.json"
    # book_name = "1 Peter"

    # _output_language = "French"
    # _input_data = "./data/auto_11-philippians.json"
    # _book_name = "Philippians"
    # _exclude_source_gloss = True #Don't include the french when producing French.
    # _reference_bible_usfx_zip = "./data/French_frasbl_usfx.zip/frasbl_usfx.xml"
    # _bcv_template = "PHP.{0}.{1}"
    # _output_suffix = "_frasbl"
    # _extra_ChatGPT_instructions = "\n\nStick as close to the Greek as possible with a hyper literal translation."

    # _output_language = "English"
    # _input_data = "./data/auto_01-matthew.json"
    # _book_name = "Matthew"

    _output_language = "English"
    _input_data = "./data/auto_02-mark.json"
    _book_name = "Mark"

    _cache_saver = "ChatGPT_cache.txt"

    do_it( input_data=_input_data, book_name=_book_name, output_language=_output_language, output_suffix=_output_suffix,
        reference_bible_usfx_zip=_reference_bible_usfx_zip, bcv_template=_bcv_template, exclude_source_gloss=_exclude_source_gloss,
        extra_ChatGPT_instructions=_extra_ChatGPT_instructions, model_name=_model_name, openai_api_key=_openai_api_key, host_local=_host_local,
        cache_saver=_cache_saver )


    print( "Done." )