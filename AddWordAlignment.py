# %% [markdown]
# # Translate Gloss by ChatGPT

# %%
import getpass, json, re, copy, os, time




# %%


# %%
def get_system_message( output_language ):
    system_message = f"""
    You are a language professor preparing language material.  
    You are translating subsections of Bible verses from Greek and French into {output_language}.
    """.strip()
    return system_message


# %%
def strip_and_tokenize_gloss( gloss ):
    gloss = gloss.replace( '-', ' ' ).replace( '*', ' ' ).strip()

    while '  ' in gloss:
        gloss = gloss.replace( '  ', ' ' )

    tokens_to_nuke = ['.', '?', '!', ',', '"', "'", '(', ')']
    for token in tokens_to_nuke:
        gloss = gloss.replace( token, '' )

    return gloss.split()


def generate_prompt_string( _data, verse_index, chunk_index, gloss_index, _book_name ):
    verse = _data[verse_index]
    chunks = verse['chunks']
    chunk = chunks[chunk_index]
    sources = chunk['source']
    first_piece = sources[0]

    _n = '\n' #f-string objection < python 3.12

    tokenized_gloss = strip_and_tokenize_gloss( chunk['gloss'] )


    morphology_info = ""
    if any( ('morph' in source) for source in sources ):
        morphology_info = f"""
Morphology information:
```
{_n.join( str(index) + ": " + source['content'] + ': ' + ','.join(source['morph']) for index, source in enumerate(sources) ) }
```
"""

    result = f"""
Look at this verse:
```
{_book_name} {first_piece['cv']}: {verse['sourceString']}
```
{morphology_info}
Focus on these specific source words:
```
{ _n.join( str(index) + ": " + source['content'] for index, source in enumerate(sources) ) }
```

This is the output translation of the source words:
```
{_n.join( str(index) + ': ' + token for index, token in enumerate(tokenized_gloss) ) }
```

Which source word, if any, translates to the output word "{gloss_index}: {tokenized_gloss[gloss_index]}"? If no source word translates to "{tokenized_gloss[gloss_index]}," state that it is not mapped.
Don't mention any other source word in your response.
""".strip()
    return result



# %%
def map_gloss_token( data, verse_index, chunk_index, gloss_index, book_name, output_language, host_local, client_or_pipe, model_name ):
    system_message = get_system_message( output_language )

    prompt = generate_prompt_string( data, verse_index, chunk_index, gloss_index, book_name )
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]

    if not host_local:
        response = client_or_pipe.chat.completions.create(
            model=model_name,
            messages=messages
        )
        #return response.choices[0].text,
        return response.choices[0].message.content
    else:
        response = client_or_pipe(messages, max_new_tokens=128)
        return response[0]['generated_text'][-1]['content']

def remove_chars(content, what_to_remove):
    for char in what_to_remove:
        content = content.replace(char, '')
    return content

def extract_answer_from_response( _response, source_words ):
    source_word_list = map( lambda x: x['content'], source_words )

    punctuation = ".,;!?()·"

    #strip punctuation out of source_word_list
    source_word_list = [remove_chars(x, punctuation) for x in source_word_list]
    source_word_list = [remove_chars(x, ":") for x in source_word_list] #we want to keep : in the _response but not in the words.

    #strip punctuation out of _response
    _response = remove_chars(_response, punctuation)

    #see if it is a raw list of numbers.
    try:
        return [int(x) for x in _response.split(',') if int(x) >= 0]
    except ValueError:

        implicit_keys = [
            "is implicit", "is an implicit", "is implied", "is **implicit**", "not directly translated from", "is not explicitly mentioned", "is not mapped", "No source word translates to", "No source word that translates to", "No source word maps to", "None of the source words from the verse translates to", "does not have a corresponding source word", "None of the specified source words translate to", "There is no source word that directly translates",
        ]
        #if the response includes this then it is an implied word    
        for key in implicit_keys:
            if key.lower() in _response.lower():
                return []
        #compile all the quoted text in the response.
        quoted_strings = re.findall(r'"(.*?)"', _response) + re.findall(r"'(.*?)'", _response)

        #also add in the ``` ``` quoted items.`
        quoted_strings += re.findall(r'```(.*?)```', _response, re.DOTALL)

        if quoted_strings:
            quoted_strings = [x.strip().replace('.', '').replace(',', '') for x in quoted_strings]

            #see if any of the source words are exactly in the quoted_strings.
            result = []
            for source_index, source_word in enumerate(source_word_list):
                if source_word in quoted_strings:
                    result.append(source_index)
            if result:
                return result
            
            #Now see if the source words with an index on the front is in the quoted_strings.
            result = []
            for source_index, source_word in enumerate(source_word_list):
                if str(source_index) + ': ' + source_word in quoted_strings:
                    result.append(source_index)
            if result:
                return result

            #see if any of the source words are in any of the quoted_strings.
            result = []
            for source_index, source_word in enumerate(source_word_list):
                for quoted_string in quoted_strings:
                    if source_word in quoted_string:
                        result.append(source_index)
            if result:
                return result
            

            #see if any of the quoted_strings are indexes.
            result = []
            for source_index, source_word in enumerate(source_word_list):
                for quoted_string in quoted_strings:
                    if str(source_index) == quoted_string:
                        result.append(source_index)
            if result:
                return result
            
        #see if the words are in the response loose with an index
        result = []
        for source_index, source_word in enumerate(source_word_list):
            if str(source_index) + ': ' + source_word  in _response:
                result.append(source_index)
        if result:
            return result

        #see if any of the source words are in the response but not quoted.
        result = []
        for source_index, source_word in enumerate(source_word_list):
            if source_word in _response:
                result.append(source_index)
        if result:
            return result

    raise ValueError(f"Result not in expected format: {_response}")



# %%
def number_of_verses( _data ):
    return len(_data)
def number_of_chunks( _data, verse_index ):
    return len(_data[verse_index]['chunks'])

def number_of_gloss_tokens( _data, verse_index, chunk_index ):
    chunk = _data[verse_index]['chunks'][chunk_index]
    return len( strip_and_tokenize_gloss( chunk['gloss'] ) )
# %%
#go ahead and load the data.
def get_data( input_data ):
    with open( input_data, 'r' ) as fin:
        data = json.load( fin )
    return data
# %%

def get_output_data( host_local, openai_api_key, model_name, data, book_name, output_language, output_callback=None ):


    if output_callback:
        output_callback( "Starting..." )

    if not host_local:
        from openai import OpenAI
        client_or_pipe = OpenAI( api_key = openai_api_key )
    else:
        from transformers import pipeline
        client_or_pipe = pipeline("text-generation", model_name)
    
    output_data = copy.deepcopy(data)

    verse_index = 0
    chunk_index = 0 #TODO: make sure this is zero.
    gloss_index = 0
    # %%

    starting_time = time.time()

    with open( f"match_{book_name}_{output_language}_process.log", "w" ) as process_file_out:
        done = False

        while not done:

            if verse_index >= number_of_verses(data):
                done = True

            if not done:
                process_file_out.write( f"Processing verse {verse_index} chunk {chunk_index} gloss {gloss_index}\n" )
                process_file_out.write( f"Prompt string:\n{generate_prompt_string( data, verse_index, chunk_index, gloss_index, book_name )}\n\n")

                #if we fail to extract an answer from the response we want to loop.
                
                MAX_RETRIES = 7
                try_count = 0
                collected_answers = []
                found_consistency = False
                while not found_consistency and try_count < MAX_RETRIES:
                    try:
                        response = map_gloss_token( data, verse_index, chunk_index, gloss_index, book_name, output_language, host_local, client_or_pipe, model_name )

                        process_file_out.write( f"Response:\n{response}\n\n" )

                        answer = extract_answer_from_response( response, data[verse_index]['chunks'][chunk_index]['source'] )

                        process_file_out.write( f"Answer:\n{answer}\n\n" )
                        process_file_out.flush()

                        answer_string = ",".join([str(x) for x in answer])

                        if answer_string in collected_answers:
                            found_consistency = True

                        collected_answers.append( answer_string )

                    except ValueError as e:
                        process_file_out.write( f"Error: {e}\n" )
                        process_file_out.flush()
                        try_count += 1
                        if output_callback:
                            output_callback( f"Retrying verse {verse_index} chunk {chunk_index} because of {e} retry {try_count}" )
                        print( f"Retrying verse {verse_index} chunk {chunk_index} because of {e} retry {try_count}" )
                        time.sleep(10)

                if not found_consistency:
                    if collected_answers:
                        answer = collected_answers[0]
                    else:
                        answer = []
                    response = "No consistent answer found after " + str(MAX_RETRIES) + " retries."
                    

                if 'gloss_mapping' not in output_data[verse_index]['chunks'][chunk_index]:
                    output_data[verse_index]['chunks'][chunk_index]['gloss_mapping'] = {}

                gloss_tokenized = strip_and_tokenize_gloss( output_data[verse_index]['chunks'][chunk_index]['gloss'] )
                source_words = output_data[verse_index]['chunks'][chunk_index]['source']
                output_data[verse_index]['chunks'][chunk_index]['gloss_mapping'][ f"{gloss_index}: {gloss_tokenized[gloss_index]}" ] = [f"{index}: {source_words[index]['content']}" for index in answer]

                process_file_out.write( "gloss_mapping:\n" )
                process_file_out.write( json.dumps( output_data[verse_index]['chunks'][chunk_index]['gloss_mapping'], indent=4, ensure_ascii=False ) )
                process_file_out.write( "\n\n" )
                process_file_out.flush()

                if 'gloss_debug' not in output_data[verse_index]['chunks'][chunk_index]:
                    output_data[verse_index]['chunks'][chunk_index]['gloss_debug'] = {}
                output_data[verse_index]['chunks'][chunk_index]['gloss_debug'][f"{gloss_index}: {gloss_tokenized[gloss_index]}"] = response

                #update the indexes
                gloss_index += 1

                if output_callback:
                    output_callback( f"Verse {verse_index} chunk {chunk_index} gloss {gloss_index}" )

                if gloss_index >= number_of_gloss_tokens(data, verse_index, chunk_index):
                    chunk_index += 1
                    gloss_index = 0

                if chunk_index >= number_of_chunks(data, verse_index):
                    verse_index += 1
                    chunk_index = 0

                    now = time.time()
                    end_estimation_time = now + (now - starting_time) * (number_of_verses(data) - verse_index) / (verse_index)
                    print( f"Estimated end time: {time.strftime('%Y-%m-%d %I:%M:%S %p', time.localtime(end_estimation_time))}  Arrange count: {verse_index}/{number_of_verses(data)}" )

                    if output_callback:
                        output_callback( f"Estimated end time: {time.strftime('%Y-%m-%d %I:%M:%S %p', time.localtime(end_estimation_time))}  Arrange count: {verse_index}/{number_of_verses(data)}" )

    return output_data

# %%
def write_output_data( output_data, output_filename ):
    with open( output_filename, 'w' ) as file_out:
        file_out.write( json.dumps( output_data, indent=4, ensure_ascii=False  ) )

# %%

def main():

    _host_local = False
    _output_language = "English"


    _input_data = f"./data/php_ChatGPT_{_output_language}.json"
    _output_filename = f"./data/php_ChatGPT_{_output_language}_matched.json"
    _book_name = "Philippians"

    if not _host_local:
        _model = "gpt-3.5-turbo"
        #_model = "gpt-4"
        #_model = "gpt-4-1106-preview"
    else:
        _hugging_face_model = "teknium/OpenHermes-2.5-Mistral-7B"

    if not _host_local:
        # see if we can get an openai api key out of a config.json file
        _openai_api_key = None
        if os.path.exists("config.json"):
            with open("config.json") as f:
                config = json.load(f)
                if "openai_api_key" in config:
                    _openai_api_key = config["openai_api_key"]
        if not _openai_api_key:
            _openai_api_key = getpass.getpass("OpenAI api key?")

    _data = get_data( _input_data )

    output_data = get_output_data( _host_local, _openai_api_key, _model if not _host_local else _hugging_face_model, 
            _data, _book_name, _output_language )

    write_output_data( output_data, _output_filename )

if __name__ == "__main__":
    main()